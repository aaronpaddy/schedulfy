"""
Schedulfy 2.0 - AI-Powered Course Scheduler
Enhanced Flask backend with GPT-4 recommendations, workload prediction, and chat interface
"""

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from datetime import datetime, timedelta
import base64
import io
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import models
from models import db, User, Course, Schedule, ScheduleCourses, ChatHistory, CurriculumEntry

# Import AI services
from ai_service import ai_recommender, workload_predictor, course_intelligence, curriculum_extractor
from course_utils import (
    canonical_code,
    serialize_tags,
    serialize_time_slots,
    normalize_days,
    parse_prerequisites,
    serialize_prerequisites,
    unmet_prerequisites,
)

# Initialize Flask app
app = Flask(__name__)

IS_PRODUCTION = os.getenv('FLASK_ENV', 'development') == 'production'


def get_database_uri():
    """Resolve the database URI, normalizing Postgres URLs for SQLAlchemy 2.x.

    Managed Postgres providers hand out 'postgres://' URLs, a scheme SQLAlchemy
    dropped support for, so rewrite it. Remote databases also get sslmode=require;
    local ones are left alone because a stock local Postgres has no TLS and would
    refuse the connection outright.
    """
    from urllib.parse import urlsplit

    uri = os.getenv('DATABASE_URL', 'sqlite:///courses.db')

    if uri.startswith('postgres://'):
        uri = uri.replace('postgres://', 'postgresql://', 1)

    if uri.startswith('postgresql://') and 'sslmode=' not in uri:
        host = urlsplit(uri).hostname or ''
        if host not in ('localhost', '127.0.0.1', '::1', ''):
            uri += ('&' if '?' in uri else '?') + 'sslmode=require'

    return uri


# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Recycle connections before managed Postgres closes them out from under us
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql://'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }

if IS_PRODUCTION and app.config['SECRET_KEY'] == 'dev-secret-key-change-in-production':
    raise RuntimeError(
        'SECRET_KEY must be set in production. Without it, every restart '
        'invalidates all user sessions.'
    )

# Session configuration
# 'None' is the safe production default: it works whether the frontend calls the
# API same-origin (through a proxy) or cross-domain. Cross-domain browsers only
# send the cookie when SameSite=None AND Secure. Once the API is confirmed
# same-origin, set SESSION_COOKIE_SAMESITE=Lax for CSRF protection.
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv(
    'SESSION_COOKIE_SAMESITE', 'None' if IS_PRODUCTION else 'Lax'
)
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_NAME'] = 'schedulfy_session'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# CORS
# Credentialed requests cannot use a wildcard origin, so list frontend origins
# explicitly via CORS_ORIGINS (comma-separated).
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    if origin.strip()
]
CORS(app, supports_credentials=True, origins=CORS_ORIGINS)

# Initialize database
db.init_app(app)


# ==================== Helper Functions ====================

def login_required(f):
    """Decorator to require login for routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def as_int(value, default=None):
    """Coerce a form value to int, treating blank input as 'not provided'.

    HTML forms submit unfilled fields as '', which SQLite silently accepted into
    an INTEGER column but Postgres rejects with InvalidTextRepresentation.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def as_float(value, default=None):
    """Coerce a form value to float, treating blank input as 'not provided'."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def admin_required(f):
    """Restrict a route to catalog administrators.

    The course catalog is shared by every user, so a single student must not be
    able to import over it or wipe it for everyone.
    """
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        user = db.session.get(User, session['user_id'])
        if user is None or not user.is_admin:
            return jsonify({
                'error': 'Administrator access required to modify the course catalog'
            }), 403
        return f(*args, **kwargs)

    return decorated_function


def error_response(e, status=500, message=None, **extra):
    """Log the real exception; return something safe to show a browser.

    Returning str(e) put SQLAlchemy statements - including a freshly created
    password hash - straight onto the page. The detail belongs in the logs.
    """
    app.logger.exception('Request failed: %s', e)
    payload = dict(extra)
    payload['error'] = (
        str(e) if not IS_PRODUCTION
        else (message or 'Something went wrong. Please try again.')
    )
    return jsonify(payload), status


def curriculum_progress(user):
    """Degree progress, or None when the student has no curriculum yet."""
    entries = CurriculumEntry.query.filter_by(user_id=user.id).all()
    if not entries:
        return None

    done = [e for e in entries if e.is_satisfied()]
    credits_total = sum(e.credits or 0 for e in entries)
    credits_done = sum(e.credits or 0 for e in done)
    return {
        'total_courses': len(entries),
        'completed_courses': len(done),
        'remaining_courses': len(entries) - len(done),
        'credits_total': credits_total,
        'credits_completed': credits_done,
        'credits_remaining': max(credits_total - credits_done, 0),
        'remaining_codes': [e.course_code for e in entries if not e.is_satisfied()],
    }


def scope_to_curriculum(user, courses):
    """Narrow a catalog list to what this student still needs.

    Every AI surface has to agree on the candidate pool, otherwise the builder
    recommends courses the degree plan never asked for.
    """
    required = curriculum_required_codes(user)
    if required is None:
        return courses
    return [c for c in courses if canonical_code(c.code) in required]


def completed_course_codes(user):
    """Course codes the student has satisfied.

    The curriculum is the source of truth once uploaded; the preferences list
    remains the fallback for accounts that predate it.
    """
    from_curriculum = _curriculum_completed_codes(user.id)
    if from_curriculum:
        return from_curriculum
    preferences = json.loads(user.preferences) if user.preferences else {}
    return preferences.get('completed_courses', [])


def curriculum_required_codes(user):
    """Codes the student still needs, or None when no curriculum exists."""
    rows = CurriculumEntry.query.filter(
        CurriculumEntry.user_id == user.id,
        ~CurriculumEntry.status.in_(CurriculumEntry.SATISFIED),
    ).all()
    if not rows:
        return None
    return {canonical_code(r.course_code) for r in rows}


def get_current_user():
    """Get the current logged-in user"""
    if 'user_id' in session:
        return db.session.get(User, session['user_id'])
    return None


def has_time_conflict(course1, course2):
    """Check if two courses have overlapping time slots"""
    try:
        slots1 = json.loads(course1.time_slots) if course1.time_slots else []
        slots2 = json.loads(course2.time_slots) if course2.time_slots else []
        
        # If either course has no time slots, assume no conflict (course times not specified)
        if not slots1 or not slots2:
            return False
        
        for slot1 in slots1:
            for slot2 in slots2:
                # Check if they're on the same day
                day1 = slot1.get('day', '')
                day2 = slot2.get('day', '')
                
                # Skip if either slot doesn't have a day specified
                if not day1 or not day2:
                    continue
                
                # Expand to canonical weekday names so 'MWF', 'Mon,Wed,Fri'
                # and 'monday' all compare equal.
                common_days = normalize_days(day1) & normalize_days(day2)
                if not common_days:
                    continue
                
                # Get time slots
                start1 = slot1.get('start_time')
                end1 = slot1.get('end_time')
                start2 = slot2.get('start_time')
                end2 = slot2.get('end_time')
                
                # Skip if times are not specified for either slot
                if not start1 or not end1 or not start2 or not end2:
                    continue
                
                # Normalize times to comparable format (handle both 12hr and 24hr)
                def normalize_time(time_str):
                    """Convert time to 24-hour format for comparison"""
                    time_str = time_str.strip().upper()
                    
                    # Handle 12-hour format
                    if 'AM' in time_str or 'PM' in time_str:
                        is_pm = 'PM' in time_str
                        time_str = time_str.replace('AM', '').replace('PM', '').strip()
                        
                        parts = time_str.split(':')
                        hours = int(parts[0])
                        minutes = int(parts[1]) if len(parts) > 1 else 0
                        
                        # Convert to 24-hour
                        if is_pm and hours != 12:
                            hours += 12
                        elif not is_pm and hours == 12:
                            hours = 0
                        
                        return f"{hours:02d}:{minutes:02d}"
                    
                    # Already in 24-hour format, just ensure proper format
                    parts = time_str.split(':')
                    if len(parts) >= 2:
                        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
                    return "00:00"
                
                try:
                    start1_norm = normalize_time(start1)
                    end1_norm = normalize_time(end1)
                    start2_norm = normalize_time(start2)
                    end2_norm = normalize_time(end2)
                    
                    # Check for time overlap: two time ranges overlap if start1 < end2 AND start2 < end1
                    if start1_norm < end2_norm and start2_norm < end1_norm:
                        return True
                except (ValueError, IndexError):
                    # If time parsing fails, skip this comparison
                    continue
        
        return False
    except Exception as e:
        print(f"Error checking time conflict: {e}")
        return False


# ==================== Curriculum ====================

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.gif')


def _pdf_to_text(data):
    """Extract embedded text from a PDF, or '' when it is a scan."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return '\n'.join((page.extract_text() or '') for page in reader.pages).strip()
    except Exception as e:
        print(f'PDF text extraction failed: {e}')
        return ''


def _curriculum_completed_codes(user_id):
    """Course codes this student has satisfied, for prerequisite checks."""
    rows = CurriculumEntry.query.filter(
        CurriculumEntry.user_id == user_id,
        CurriculumEntry.status.in_(CurriculumEntry.SATISFIED),
    ).all()
    return [r.course_code for r in rows]


@app.route('/api/curriculum/extract', methods=['POST'])
@login_required
def extract_curriculum():
    """Parse uploaded degree-plan documents into DRAFT rows.

    Nothing is saved here. The student confirms and corrects the result before
    it becomes their curriculum.
    """
    try:
        text_parts = []
        images = []

        for upload in request.files.getlist('files'):
            if not upload.filename:
                continue
            data = upload.read()
            if len(data) > MAX_UPLOAD_BYTES:
                return jsonify({
                    'success': False,
                    'error': f'{upload.filename} is larger than 8MB'
                }), 400

            name = upload.filename.lower()
            if name.endswith('.pdf'):
                extracted = _pdf_to_text(data)
                if extracted:
                    text_parts.append(extracted)
                else:
                    # A scanned PDF has no text layer, and rasterizing it needs
                    # poppler, which is not available here. Ask for an image.
                    return jsonify({
                        'success': False,
                        'error': f'{upload.filename} has no readable text. '
                                 'It looks like a scan - please upload a screenshot instead.'
                    }), 400
            elif name.endswith(IMAGE_EXTENSIONS):
                mime = 'image/png' if name.endswith('.png') else 'image/jpeg'
                encoded = base64.b64encode(data).decode('ascii')
                images.append(f'data:{mime};base64,{encoded}')
            elif name.endswith(('.txt', '.csv')):
                text_parts.append(data.decode('utf-8', errors='replace'))
            else:
                return jsonify({
                    'success': False,
                    'error': f'Unsupported file type: {upload.filename}'
                }), 400

        pasted = (request.form.get('text') or '').strip()
        if pasted:
            text_parts.append(pasted)

        if not text_parts and not images:
            return jsonify({'success': False, 'error': 'No curriculum provided'}), 400

        result = curriculum_extractor.extract(
            text='\n\n'.join(text_parts) if text_parts else None,
            images=images,
        )
        if not result.get('success'):
            return jsonify(result), 502

        # Flag codes the student already has, so confirming cannot silently
        # overwrite work they have recorded.
        existing = {
            canonical_code(r.course_code)
            for r in CurriculumEntry.query.filter_by(user_id=session['user_id']).all()
        }
        for course in result['courses']:
            course['already_in_plan'] = canonical_code(course.get('course_code')) in existing

        result['draft'] = True
        return jsonify(result), 200

    except Exception as e:
        return error_response(e, 500, success=False)


@app.route('/api/curriculum', methods=['GET'])
@login_required
def get_curriculum():
    """The student's curriculum, with derived progress."""
    try:
        user = get_current_user()
        entries = CurriculumEntry.query.filter_by(user_id=user.id).order_by(
            CurriculumEntry.suggested_year.nulls_last()
            if hasattr(CurriculumEntry.suggested_year, 'nulls_last')
            else CurriculumEntry.suggested_year,
            CurriculumEntry.course_code,
        ).all()

        completed = [e for e in entries if e.is_satisfied()]
        credits_done = sum(e.credits or 0 for e in completed)
        credits_total = sum(e.credits or 0 for e in entries)

        return jsonify({
            'curriculum': [e.to_dict() for e in entries],
            'progress': {
                'total_courses': len(entries),
                'completed_courses': len(completed),
                'remaining_courses': len(entries) - len(completed),
                'credits_completed': credits_done,
                'credits_total': credits_total,
                'credits_remaining': max(credits_total - credits_done, 0),
            },
        }), 200
    except Exception as e:
        return error_response(e, 500)


@app.route('/api/curriculum', methods=['POST'])
@login_required
def save_curriculum():
    """Save confirmed curriculum rows.

    Upserts on course code so re-uploading a corrected sheet updates rows in
    place instead of duplicating them, and never resets a recorded status.
    """
    try:
        user = get_current_user()
        data = request.get_json() or {}
        rows = data.get('curriculum', [])
        if not isinstance(rows, list):
            return jsonify({'error': 'curriculum must be a list'}), 400

        if data.get('replace'):
            CurriculumEntry.query.filter_by(user_id=user.id).delete()
            db.session.flush()

        existing = {
            canonical_code(e.course_code): e
            for e in CurriculumEntry.query.filter_by(user_id=user.id).all()
        }

        created = updated = 0
        for row in rows:
            code = (row.get('course_code') or '').strip()
            if not code:
                continue

            entry = existing.get(canonical_code(code))
            if entry is None:
                entry = CurriculumEntry(user_id=user.id, course_code=code)
                db.session.add(entry)
                existing[canonical_code(code)] = entry
                created += 1
            else:
                updated += 1

            entry.course_code = code
            entry.title = row.get('title') or entry.title
            entry.credits = as_float(row.get('credits'), entry.credits if entry.credits else 3.0)
            entry.category = row.get('category') or entry.category
            entry.suggested_year = as_int(row.get('suggested_year'), entry.suggested_year)
            entry.suggested_term = row.get('suggested_term') or entry.suggested_term
            entry.notes = row.get('notes') if row.get('notes') is not None else entry.notes
            entry.source = row.get('source') or entry.source or 'upload'

            terms = row.get('offered_terms')
            if isinstance(terms, list):
                entry.offered_terms = json.dumps(terms)

            if 'prerequisites' in row:
                entry.prerequisites = serialize_prerequisites(row.get('prerequisites'))

            status = row.get('status')
            if status in CurriculumEntry.STATUSES:
                entry.status = status
            elif not entry.status:
                entry.status = CurriculumEntry.STATUS_NEEDED

        db.session.commit()
        return jsonify({
            'message': f'Saved {created + updated} curriculum entries',
            'created': created,
            'updated': updated,
        }), 200
    except Exception as e:
        db.session.rollback()
        return error_response(e, 500)


@app.route('/api/curriculum/<int:entry_id>', methods=['PUT', 'DELETE'])
@login_required
def modify_curriculum_entry(entry_id):
    """Update one requirement - ticking it off, or correcting a field."""
    try:
        user = get_current_user()
        entry = db.session.get(CurriculumEntry, entry_id)
        if entry is None or entry.user_id != user.id:
            return jsonify({'error': 'Curriculum entry not found'}), 404

        if request.method == 'DELETE':
            db.session.delete(entry)
            db.session.commit()
            return jsonify({'message': 'Entry removed'}), 200

        data = request.get_json() or {}
        if 'status' in data:
            if data['status'] not in CurriculumEntry.STATUSES:
                return jsonify({
                    'error': f"status must be one of {', '.join(CurriculumEntry.STATUSES)}"
                }), 400
            entry.status = data['status']

        for field in ('title', 'category', 'suggested_term', 'notes'):
            if field in data:
                setattr(entry, field, data[field])
        if 'course_code' in data and data['course_code']:
            entry.course_code = data['course_code'].strip()
        if 'credits' in data:
            entry.credits = as_float(data['credits'], entry.credits)
        if 'suggested_year' in data:
            entry.suggested_year = as_int(data['suggested_year'], entry.suggested_year)
        if isinstance(data.get('offered_terms'), list):
            entry.offered_terms = json.dumps(data['offered_terms'])
        if 'prerequisites' in data:
            entry.prerequisites = serialize_prerequisites(data['prerequisites'])

        db.session.commit()
        return jsonify({'message': 'Entry updated', 'entry': entry.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return error_response(e, 500)


# ==================== Health Check ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'message': 'Schedulfy 2.0 AI API is running',
        'status': 'healthy',
        'version': '2.0.0',
        'ai_enabled': bool(os.getenv('OPENAI_API_KEY')),
        'timestamp': datetime.utcnow().isoformat()
    })


# ==================== Authentication Routes ====================

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """Register a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if username already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # Validate password length
        if len(data['password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
        # Create new user
        new_user = User(
            username=data['username'],
            email=data['email'],
            major=data.get('major', ''),
            graduation_year=as_int(data.get('graduation_year')),
            current_year=data.get('current_year', 'Freshman'),
            gpa=as_float(data.get('gpa')),
            career_goal=data.get('career_goal', ''),
            preferences=json.dumps(data.get('preferences', {})),
            learning_preferences=json.dumps(data.get('learning_preferences', {}))
        )
        new_user.set_password(data['password'])
        
        db.session.add(new_user)
        db.session.commit()
        
        # Log the user in
        session.permanent = True
        session['user_id'] = new_user.id
        session['username'] = new_user.username
        
        return jsonify({
            'message': 'User created successfully',
            'user': new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return error_response(e, 400)


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        
        if not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Username and password are required'}), 400
        
        # Find user
        user = User.query.filter(
            (User.username == data['username']) | (User.email == data['username'])
        ).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid username or password'}), 401
        
        # Create session
        session.permanent = True
        session['user_id'] = user.id
        session['username'] = user.username
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return error_response(e, 400)


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200


@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user_info():
    """Get current logged-in user information"""
    user = get_current_user()
    return jsonify({
        'user': user.to_dict(),
        'authenticated': True
    }), 200


# ==================== AI-Powered Routes ====================

@app.route('/api/ai/recommendations', methods=['POST'])
@login_required
def get_ai_recommendations():
    """
    Get AI-powered course recommendations
    POST /api/ai/recommendations
    Body: {
        "target_credits": 15,
        "semester": "Fall",
        "year": 2025,
        "focus_area": "machine learning" (optional)
    }
    """
    try:
        user = get_current_user()
        data = request.get_json() or {}
        
        # Build student profile
        preferences = json.loads(user.preferences) if user.preferences else {}
        completed_courses = completed_course_codes(user)
        
        student_profile = {
            'major': user.major,
            'year': user.current_year or 'Freshman',
            'gpa': user.gpa if user.gpa is not None else 'Not provided',
            'completed_courses': completed_courses,
            'career_goal': user.career_goal or 'Not specified',
            'learning_preferences': user.learning_preferences,
            'target_credits': data.get('target_credits', 15),
            'focus_area': data.get('focus_area', ''),
            'degree_progress': curriculum_progress(user),
        }
        
        # Get available courses
        semester = data.get('semester', 'Fall')
        year = data.get('year', 2025)
        
        available_courses = scope_to_curriculum(user, Course.query.filter(
            (Course.semester == semester) | (Course.semester == 'Both')
        ).all())
        
        # Convert to dicts
        courses_data = [course.to_dict() for course in available_courses]
        
        # Get AI recommendations
        ai_response = ai_recommender.get_course_recommendations(
            student_profile,
            courses_data,
            num_recommendations=data.get('num_recommendations', 8)
        )
        
        # The model is asked for prerequisites_met, but a language model is not
        # the right authority on it. Recompute from the catalog so the badge the
        # UI shows is backed by data rather than inference.
        by_code = {canonical_code(c.code): c for c in available_courses}
        for rec in ai_response.get('recommendations', []) or []:
            course = by_code.get(canonical_code(rec.get('course_code')))
            if course is None:
                continue
            missing = unmet_prerequisites(course.prerequisites, completed_courses)
            rec['prerequisites_met'] = not missing
            rec['missing_prerequisites'] = missing

        return jsonify(ai_response), 200
        
    except Exception as e:
        return error_response(e, 500, success=False)


@app.route('/api/ai/chat', methods=['POST'])
@login_required
def chat_with_ai():
    """
    Natural language chat interface for schedule building
    POST /api/ai/chat
    Body: {
        "message": "I need 15 credits, no Friday classes",
        "include_history": true
    }
    """
    try:
        user = get_current_user()
        data = request.get_json()
        
        user_message = data.get('message', '')
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Get conversation history if requested
        conversation_history = []
        if data.get('include_history', False):
            history = ChatHistory.query.filter_by(user_id=user.id).order_by(
                ChatHistory.created_at.desc()
            ).limit(10).all()
            conversation_history = [h.to_dict() for h in reversed(history)]
        
        # Build student context
        preferences = json.loads(user.preferences) if user.preferences else {}
        student_context = {
            'name': user.username,
            'major': user.major,
            'year': user.current_year,
            'completed_courses': completed_course_codes(user),
            'career_goal': user.career_goal
        }
        
        # Add current schedule context if provided
        current_schedule = data.get('current_schedule', [])
        schedule_context = data.get('schedule_context', {})
        
        if current_schedule:
            student_context['current_schedule'] = current_schedule
            student_context['current_credits'] = sum(c.get('credits', 0) for c in current_schedule)
            student_context['current_courses'] = [c.get('code') for c in current_schedule]
        
        if schedule_context:
            student_context['schedule_name'] = schedule_context.get('scheduleName')
            student_context['max_credits'] = schedule_context.get('maxCredits', 18)
            student_context['remaining_credits'] = schedule_context.get('remainingCredits', 18)
        
        # Get available courses, narrowed to the degree plan when there is one
        available_courses = scope_to_curriculum(user, Course.query.all())
        student_context['degree_progress'] = curriculum_progress(user)
        courses_data = [course.to_dict() for course in available_courses]
        
        # Get AI response
        response = ai_recommender.chat_schedule_assistant(
            user_message,
            conversation_history,
            student_context,
            courses_data
        )
        
        # Save chat history
        if response['success']:
            # Save user message
            user_chat = ChatHistory(
                user_id=user.id,
                message=user_message,
                role='user'
            )
            db.session.add(user_chat)
            
            # Save AI response
            ai_chat = ChatHistory(
                user_id=user.id,
                message=response['message'],
                role='assistant',
                context=json.dumps({'suggested_courses': response.get('suggested_courses', [])})
            )
            db.session.add(ai_chat)
            db.session.commit()
        
        return jsonify(response), 200
        
    except Exception as e:
        return error_response(e, 500, success=False)


@app.route('/api/ai/workload-prediction', methods=['POST'])
@login_required
def predict_workload():
    """
    Predict workload for a set of courses
    POST /api/ai/workload-prediction
    Body: {
        "course_ids": [1, 2, 3, 4]
    }
    """
    try:
        data = request.get_json()
        course_ids = data.get('course_ids', [])
        
        if not course_ids:
            return jsonify({'error': 'course_ids required'}), 400
        
        # Get courses
        courses = Course.query.filter(Course.id.in_(course_ids)).all()
        courses_data = [course.to_dict() for course in courses]
        
        # Predict workload
        prediction = workload_predictor.predict_schedule_workload(courses_data)
        
        return jsonify({
            'success': True,
            'prediction': prediction
        }), 200
        
    except Exception as e:
        return error_response(e, 500, success=False)


@app.route('/api/ai/analyze-schedule/<int:schedule_id>', methods=['GET'])
@login_required
def analyze_schedule(schedule_id):
    """AI analysis of schedule quality"""
    try:
        user = get_current_user()
        schedule = db.session.get(Schedule, schedule_id)
        
        if not schedule or schedule.user_id != user.id:
            return jsonify({'error': 'Schedule not found'}), 404
        
        courses_data = [course.to_dict() for course in schedule.courses]
        
        student_profile = {
            'major': user.major,
            'year': user.current_year,
            'career_goal': user.career_goal
        }
        
        analysis = ai_recommender.analyze_schedule_quality(courses_data, student_profile)
        
        return jsonify(analysis), 200
        
    except Exception as e:
        return error_response(e, 500, success=False)


@app.route('/api/ai/suggest-for-schedule/<int:schedule_id>', methods=['POST'])
@login_required
def suggest_for_existing_schedule(schedule_id):
    """
    Get AI suggestions for courses to add to an existing schedule
    POST /api/ai/suggest-for-schedule/<schedule_id>
    Body: {
        "num_suggestions": 5
    }
    """
    try:
        user = get_current_user()
        schedule = db.session.get(Schedule, schedule_id)
        
        if not schedule or schedule.user_id != user.id:
            return jsonify({'error': 'Schedule not found'}), 404
        
        data = request.get_json() or {}
        num_suggestions = data.get('num_suggestions', 5)
        
        # Get current courses in schedule
        current_courses = schedule.courses
        current_course_codes = [c.code for c in current_courses]
        current_credits = schedule.total_credits
        
        # Get user preferences and max credits
        preferences = json.loads(user.preferences) if user.preferences else {}
        max_credits = preferences.get('max_credits_per_semester', 18)
        completed_courses = completed_course_codes(user)
        
        # Calculate remaining credits
        remaining_credits = max_credits - current_credits
        
        if remaining_credits <= 0:
            return jsonify({
                'success': True,
                'message': f'Your schedule is at the {max_credits}-credit limit. Remove courses to add more.',
                'recommendations': [],
                'current_credits': current_credits,
                'max_credits': max_credits
            }), 200
        
        # Get all available courses, narrowed to the degree plan when present
        available_courses = scope_to_curriculum(user, Course.query.filter(
            (Course.semester == schedule.semester) | (Course.semester == 'Both')
        ).all())
        
        # Filter out courses already in schedule and completed courses
        # Courses already taken count toward prerequisites, as do the ones
        # already on this schedule.
        satisfied = list(completed_courses) + list(current_course_codes)
        eligible_courses = [
            c for c in available_courses 
            if c.code not in current_course_codes 
            and c.code not in completed_courses
            and c.credits <= remaining_credits  # Only courses that fit
            and not unmet_prerequisites(c.prerequisites, satisfied)
        ]
        
        # Build student profile with current schedule context
        student_profile = {
            'major': user.major,
            'year': user.current_year,
            'gpa': user.gpa if user.gpa is not None else 'Not provided',
            'completed_courses': completed_courses + current_course_codes,  # Treat current schedule as "completed"
            'career_goal': user.career_goal,
            'target_credits': remaining_credits,
            'current_schedule': [c.to_dict() for c in current_courses]
        }
        
        # Get AI recommendations
        courses_data = [c.to_dict() for c in eligible_courses]
        ai_result = ai_recommender.get_course_recommendations(
            student_profile,
            courses_data,
            num_recommendations=num_suggestions
        )
        
        if not ai_result['success']:
            return jsonify(ai_result), 500
        
        # Filter recommendations to avoid time conflicts
        filtered_recommendations = []
        for recommendation in ai_result['recommendations']:
            course_code = recommendation['course_code']
            course = next((c for c in eligible_courses if c.code == course_code), None)
            
            if not course:
                continue
            
            # Check for time conflicts with current schedule
            has_conflict = False
            for current_course in current_courses:
                if has_time_conflict(course, current_course):
                    has_conflict = True
                    recommendation['conflict_warning'] = f"Time conflict with {current_course.code}"
                    break
            
            # Add conflict status
            recommendation['has_conflict'] = has_conflict
            filtered_recommendations.append(recommendation)
        
        return jsonify({
            'success': True,
            'recommendations': filtered_recommendations,
            'current_credits': current_credits,
            'max_credits': max_credits,
            'remaining_credits': remaining_credits,
            'schedule_name': schedule.name,
            'context': f'Suggestions complement your current {len(current_courses)}-course schedule'
        }), 200
        
    except Exception as e:
        return error_response(e, 500, success=False)


# ==================== Course Routes ====================

@app.route('/api/courses', methods=['GET'])
def get_courses():
    """Get all available courses with optional filters"""
    try:
        # Query parameters
        department = request.args.get('department')
        semester = request.args.get('semester')
        min_credits = request.args.get('min_credits', type=int)
        max_credits = request.args.get('max_credits', type=int)
        
        # Build query
        query = Course.query
        
        if department:
            query = query.filter_by(department=department)
        if semester:
            query = query.filter((Course.semester == semester) | (Course.semester == 'Both'))
        if min_credits:
            query = query.filter(Course.credits >= min_credits)
        if max_credits:
            query = query.filter(Course.credits <= max_credits)
        
        courses = query.all()
        
        return jsonify({
            'courses': [course.to_dict() for course in courses],
            'total': len(courses)
        }), 200
        
    except Exception as e:
        return error_response(e, 500)


@app.route('/api/courses/<int:course_id>', methods=['GET'])
def get_course_detail(course_id):
    """Get detailed information about a specific course"""
    try:
        course = db.session.get(Course, course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
        
        # Get similar courses
        similar_courses = course_intelligence.find_similar_courses(course_id)
        
        # Predict workload if not set
        if not course.workload_hours:
            workload_pred = workload_predictor.predict_course_workload(course.to_dict())
            course.workload_hours = workload_pred['hours_per_week']
        
        result = course.to_dict()
        result['similar_courses'] = similar_courses
        
        return jsonify(result), 200
        
    except Exception as e:
        return error_response(e, 500)


@app.route('/api/courses/import', methods=['POST'])
@admin_required
def import_courses():
    """Import courses from CSV or JSON file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read file content
        content = file.read().decode('utf-8')
        
        imported = 0
        updated = 0
        errors = []
        
        # Parse based on file type
        if file.filename.endswith('.json'):
            try:
                courses_data = json.loads(content)
                if not isinstance(courses_data, list):
                    return jsonify({'error': 'JSON must be an array of course objects'}), 400
            except json.JSONDecodeError as e:
                return jsonify({'error': f'Invalid JSON format: {str(e)}'}), 400
        
        elif file.filename.endswith('.csv'):
            import csv
            import io
            
            reader = csv.DictReader(io.StringIO(content))
            courses_data = list(reader)
        else:
            return jsonify({'error': 'Unsupported file format. Use CSV or JSON'}), 400
        
        # Import each course
        for course_data in courses_data:
            try:
                # Map field names (handle both formats)
                code = course_data.get('course_code') or course_data.get('code')
                name = course_data.get('course_name') or course_data.get('name')
                credits = course_data.get('credits', 3)
                
                if not code or not name:
                    errors.append(f"Missing required fields for course: {course_data}")
                    continue
                
                # Check if course exists
                existing_course = Course.query.filter_by(code=code).first()
                
                if existing_course:
                    # Update existing course
                    existing_course.name = name
                    existing_course.credits = int(credits)
                    existing_course.description = course_data.get('description', '')
                    existing_course.department = course_data.get('department', '')
                    existing_course.semester = course_data.get('semester', 'Fall')
                    existing_course.year = int(course_data.get('year', 2025))
                    
                    # Handle JSON fields
                    if 'prerequisites' in course_data:
                        # serialize_prerequisites unwraps values that are
                        # already JSON, so re-importing an export no longer
                        # nests the list inside itself.
                        existing_course.prerequisites = serialize_prerequisites(
                            course_data['prerequisites']
                        )
                    
                    # A CSV cell is always a string, so the previous
                    # isinstance(list) check silently discarded every
                    # meeting time and left schedules unable to detect
                    # conflicts.
                    if 'time_slots' in course_data:
                        existing_course.time_slots = serialize_time_slots(
                            course_data['time_slots']
                        )

                    # Fields the AI reads. Without these an imported catalog
                    # forces the model to guess difficulty and workload.
                    if 'difficulty' in course_data:
                        existing_course.difficulty = as_float(
                            course_data['difficulty'], existing_course.difficulty
                        )
                    if 'workload_hours' in course_data:
                        existing_course.workload_hours = as_float(
                            course_data['workload_hours'], existing_course.workload_hours
                        )
                    if 'career_tags' in course_data:
                        existing_course.career_tags = serialize_tags(course_data['career_tags'])
                    
                    updated += 1
                else:
                    # Create new course
                    new_course = Course(
                        code=code,
                        name=name,
                        credits=int(credits),
                        description=course_data.get('description', ''),
                        department=course_data.get('department', ''),
                        semester=course_data.get('semester', 'Fall'),
                        year=int(course_data.get('year', 2025)),
                        prerequisites=serialize_prerequisites(course_data.get('prerequisites')),
                        time_slots=serialize_time_slots(course_data.get('time_slots')),
                        difficulty=as_float(course_data.get('difficulty'), 3.0),
                        workload_hours=as_float(course_data.get('workload_hours')),
                        career_tags=serialize_tags(course_data.get('career_tags')),
                        max_capacity=int(course_data.get('max_capacity', 0)) if course_data.get('max_capacity') else None,
                        current_enrollment=int(course_data.get('current_enrollment', 0)) if course_data.get('current_enrollment') else None
                    )
                    db.session.add(new_course)
                    imported += 1
                
            except Exception as e:
                errors.append(f"Error importing {course_data.get('code', 'unknown')}: {str(e)}")
        
        db.session.commit()
        
        return jsonify({
            'message': 'Import completed',
            'imported': imported,
            'updated': updated,
            'errors': errors
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return error_response(e, 500)


@app.route('/api/courses/export', methods=['GET'])
@login_required
def export_courses():
    """Export all courses to CSV"""
    try:
        import csv
        import io
        
        courses = Course.query.all()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'code', 'name', 'description', 'credits', 'department', 
            'semester', 'year', 'prerequisites', 'time_slots', 
            'max_capacity', 'current_enrollment',
            'difficulty', 'workload_hours', 'career_tags'
        ])
        
        # Write course data
        for course in courses:
            writer.writerow([
                course.code,
                course.name,
                course.description or '',
                course.credits,
                course.department or '',
                course.semester or '',
                course.year or '',
                serialize_prerequisites(course.prerequisites),
                serialize_time_slots(course.time_slots),
                course.max_capacity or '',
                course.current_enrollment or '',
                course.difficulty if course.difficulty is not None else '',
                course.workload_hours if course.workload_hours is not None else '',
                serialize_tags(course.career_tags)
            ])
        
        output.seek(0)
        
        return output.getvalue(), 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=courses_export.csv'
        }
        
    except Exception as e:
        return error_response(e, 500)


@app.route('/api/courses/clear', methods=['DELETE'])
@admin_required
def clear_courses():
    """Delete all courses from the database"""
    try:
        # Saved schedules reference courses, and Postgres enforces that foreign
        # key even though SQLite did not. Detach the schedule entries first,
        # otherwise the delete aborts.
        detached = ScheduleCourses.query.delete()

        # Every course is going, so no schedule has any credits left.
        Schedule.query.update({Schedule.total_credits: 0})

        deleted = Course.query.delete()
        db.session.commit()
        
        return jsonify({
            'message': f'Successfully deleted {deleted} courses',
            'deleted_count': deleted,
            'schedule_entries_removed': detached
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return error_response(e, 500)


@app.route('/api/courses/scrape', methods=['POST'])
@admin_required
def scrape_courses():
    """Scrape courses from a university website URL using BeautifulSoup4"""
    try:
        from bs4 import BeautifulSoup
        import requests
        import re
        
        data = request.get_json()
        url = data.get('url')
        enhanced = data.get('enhanced', False)
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        # Fetch the webpage
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            return jsonify({'error': f'Failed to fetch URL: {str(e)}'}), 400
        
        soup = BeautifulSoup(response.content, 'html.parser')
        courses = []
        
        # Common patterns for course codes (e.g., CS101, MATH 220, BIO-301)
        course_code_pattern = re.compile(r'\b([A-Z]{2,4}[\s-]?\d{3,4}[A-Z]?)\b')
        
        # Common patterns for credits (e.g., 3 credits, (4), 3-4 credits)
        credits_pattern = re.compile(r'(\d)\s*(?:credits?|credit hours?|cr\.?|units?)?', re.IGNORECASE)
        
        # Try different common HTML structures for course listings
        
        # Strategy 1: Look for course listings in divs/sections with class containing "course"
        course_elements = (
            soup.find_all(['div', 'section', 'article', 'li'], class_=re.compile(r'course', re.IGNORECASE)) or
            soup.find_all(['div', 'section', 'article', 'li'], attrs={'data-course': True}) or
            soup.find_all(['tr']) # Table rows as fallback
        )
        
        seen_codes = set()
        
        for element in course_elements:
            try:
                text = element.get_text(' ', strip=True)
                
                # Find course code
                code_match = course_code_pattern.search(text)
                if not code_match:
                    continue
                
                course_code = code_match.group(1).replace(' ', '').replace('-', '')
                
                # Skip duplicates
                if course_code in seen_codes:
                    continue
                seen_codes.add(course_code)
                
                # Extract course name (usually comes after the code)
                # Try to find the course name by looking for text after the code
                text_after_code = text[code_match.end():].strip()
                
                # Course name is usually the first substantial text after the code
                # Stop at common delimiters
                name_parts = []
                for word in text_after_code.split():
                    if word.lower() in ['prerequisite', 'prereq', 'credit', 'credits', 'hours', 'description', 'semester', 'fall', 'spring', 'summer']:
                        break
                    if re.match(r'^\(?\d', word):  # Stop at numbers (likely credits)
                        break
                    name_parts.append(word)
                    if len(' '.join(name_parts)) > 80:  # Reasonable name length
                        break
                
                course_name = ' '.join(name_parts[:15]).strip('.,;:')  # Limit to first 15 words
                
                if not course_name or len(course_name) < 3:
                    continue
                
                # Extract credits
                credits_match = credits_pattern.search(text)
                credits = int(credits_match.group(1)) if credits_match else 3
                
                # Extract department from course code
                dept_match = re.match(r'([A-Z]{2,4})', course_code)
                department = dept_match.group(1) if dept_match else 'General'
                
                # Try to find description
                description = ''
                # Look for description in siblings or children
                desc_element = element.find(['p', 'div'], class_=re.compile(r'desc|description', re.IGNORECASE))
                if desc_element:
                    description = desc_element.get_text(' ', strip=True)[:500]  # Limit length
                elif len(text_after_code) > len(course_name) + 50:
                    # Use remaining text as description
                    description = text_after_code[len(course_name):].strip()[:500]
                
                # Enhanced scraping: try to find time slots
                time_slots = []
                if enhanced:
                    # Look for time patterns (e.g., MWF 9:00-10:30, M/W/F 9:00 AM - 10:30 AM)
                    time_pattern = re.compile(r'([MTWRFSU]+|(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[,\s/]*)+\s+(\d{1,2}:\d{2})\s*(?:AM|PM|am|pm)?\s*[-–]\s*(\d{1,2}:\d{2})\s*(?:AM|PM|am|pm)?', re.IGNORECASE)
                    time_match = time_pattern.search(text)
                    
                    if time_match:
                        days_str = time_match.group(1)
                        start_time = time_match.group(2)
                        end_time = time_match.group(3)
                        
                        # Convert day codes to full names
                        day_map = {
                            'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday',
                            'R': 'Thursday', 'F': 'Friday', 'S': 'Saturday', 'U': 'Sunday',
                            'Mon': 'Monday', 'Tue': 'Tuesday', 'Wed': 'Wednesday',
                            'Thu': 'Thursday', 'Fri': 'Friday', 'Sat': 'Saturday', 'Sun': 'Sunday'
                        }
                        
                        days = []
                        for key, value in day_map.items():
                            if key in days_str:
                                if value not in days:
                                    days.append(value)
                        
                        if days:
                            time_slots.append({
                                'day': ','.join(days),
                                'start_time': start_time,
                                'end_time': end_time,
                                'room': 'TBD'
                            })
                
                course_data = {
                    'code': course_code,
                    'name': course_name,
                    'credits': credits,
                    'department': department,
                    'description': description,
                    'semester': 'Fall',
                    'year': 2025
                }
                
                if time_slots:
                    course_data['time_slots'] = time_slots
                
                courses.append(course_data)
                
            except Exception as e:
                # Skip problematic entries
                continue
        
        if not courses:
            return jsonify({
                'error': 'No courses found on this page',
                'message': 'The page structure may not be compatible, or there are no course listings. Try a different URL or use manual import.',
                'suggestions': [
                    'Make sure the URL points to a page with course listings',
                    'Try the department course catalog page',
                    'Some pages may be protected or require authentication'
                ]
            }), 404
        
        return jsonify({
            'message': f'Successfully scraped {len(courses)} courses',
            'url': url,
            'total_found': len(courses),
            'courses': courses,
            'enhanced': enhanced
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Web scraping failed: {str(e)}'}), 500


# ==================== Schedule Routes ====================

@app.route('/api/schedule/generate', methods=['POST'])
@login_required
def generate_schedule():
    """Generate an AI-optimized schedule"""
    try:
        user = get_current_user()
        data = request.get_json() or {}
        
        semester = data.get('semester', 'Fall')
        year = data.get('year', 2025)
        max_credits = data.get('max_credits', 18)
        use_ai = data.get('use_ai', True)
        
        # Check for existing schedule
        existing_schedule = Schedule.query.filter_by(
            user_id=user.id,
            semester=semester,
            year=year
        ).first()
        
        if existing_schedule:
            existing_schedule.courses = []
            existing_schedule.total_credits = 0
            db.session.commit()
            schedule = existing_schedule
        else:
            schedule = Schedule(
                user_id=user.id,
                semester=semester,
                year=year,
                name=f"{semester} {year}"
            )
            db.session.add(schedule)
            db.session.commit()
        
        # Get available courses
        available_courses = Course.query.filter(
            (Course.semester == semester) | (Course.semester == 'Both')
        ).all()
        
        # Get user preferences
        preferences = json.loads(user.preferences) if user.preferences else {}
        completed_courses = completed_course_codes(user)
        
        # When the student has uploaded a curriculum, it decides what counts as
        # a candidate; the catalog only supplies the sections and meeting times
        # for those courses. Without one, fall back to the whole catalog.
        required_codes = curriculum_required_codes(user)
        if required_codes is not None:
            available_courses = [
                c for c in available_courses
                if canonical_code(c.code) in required_codes
            ]

        # Filter out completed courses and anything the student is not yet
        # eligible for. Without the prerequisite check a first-year student
        # was being scheduled straight into upper-level courses.
        eligible_courses = [
            c for c in available_courses 
            if c.code not in completed_courses and c.credits >= 1
            and not unmet_prerequisites(c.prerequisites, completed_courses)
        ]

        # Requirements with no catalog entry cannot be timetabled, but the
        # student still needs to know they are outstanding.
        unscheduled_requirements = []
        if required_codes is not None:
            in_catalog = {canonical_code(c.code) for c in available_courses}
            unscheduled_requirements = [
                {
                    'code': r.course_code,
                    'title': r.title,
                    'credits': r.credits,
                    'reason': 'No section information in the course catalog',
                }
                for r in CurriculumEntry.query.filter(
                    CurriculumEntry.user_id == user.id,
                    ~CurriculumEntry.status.in_(CurriculumEntry.SATISFIED),
                ).all()
                if canonical_code(r.course_code) not in in_catalog
            ]
        blocked_by_prereqs = [
            {
                'code': c.code,
                'name': c.name,
                'missing_prerequisites': unmet_prerequisites(c.prerequisites, completed_courses),
            }
            for c in available_courses
            if c.code not in completed_courses
            and unmet_prerequisites(c.prerequisites, completed_courses)
        ]
        
        # Use AI recommendations if enabled
        if use_ai and os.getenv('OPENAI_API_KEY'):
            student_profile = {
                'major': user.major,
                'year': user.current_year,
                'gpa': user.gpa if user.gpa is not None else 'Not provided',
                'completed_courses': completed_courses,
                'career_goal': user.career_goal,
                'target_credits': max_credits
            }
            
            courses_data = [c.to_dict() for c in eligible_courses]
            ai_result = ai_recommender.get_course_recommendations(
                student_profile,
                courses_data,
                num_recommendations=6
            )
            
            if ai_result['success']:
                # Add recommended courses to schedule (with conflict checking)
                recommended_codes = [r['course_code'] for r in ai_result['recommendations']]
                selected_courses = [c for c in eligible_courses if c.code in recommended_codes]
                
                total_credits = 0
                added_courses = []
                conflicts_avoided = []
                
                for course in selected_courses:
                    # Check credit limit
                    if total_credits + course.credits > max_credits:
                        continue
                    
                    # Check for time conflicts with already added courses
                    has_conflict = False
                    conflicting_course = None
                    
                    for added_course in added_courses:
                        if has_time_conflict(course, added_course):
                            has_conflict = True
                            conflicting_course = added_course
                            break
                    
                    if has_conflict:
                        conflicts_avoided.append({
                            'course': course.code,
                            'conflicts_with': conflicting_course.code if conflicting_course else 'Unknown'
                        })
                        continue
                    
                    # No conflicts, add the course
                    schedule.courses.append(course)
                    added_courses.append(course)
                    total_credits += course.credits
                
                schedule.total_credits = total_credits
                
                # Predict workload and quality
                courses_for_pred = [c.to_dict() for c in schedule.courses]
                workload_pred = workload_predictor.predict_schedule_workload(courses_for_pred)
                
                schedule.predicted_workload = workload_pred['total_hours_per_week']
                schedule.risk_level = workload_pred['risk_level']
                
                db.session.commit()
                
                response_data = {
                    'message': 'AI-optimized schedule generated successfully',
                    'schedule': schedule.to_dict(),
                    'workload_prediction': workload_pred,
                    'ai_recommendations': ai_result['recommendations']
                }
                
                # Add conflict info if any were avoided
                if conflicts_avoided:
                    response_data['conflicts_avoided'] = conflicts_avoided
                    response_data['message'] = f'AI-optimized schedule generated successfully. {len(conflicts_avoided)} time conflict(s) avoided.'
                
                # Tell the student which courses were withheld and why.
                if blocked_by_prereqs:
                    response_data['blocked_by_prerequisites'] = blocked_by_prereqs
                
                return jsonify(response_data), 200
        
        # Fallback to basic algorithm (with conflict checking)
        selected_courses = []
        total_credits = 0
        conflicts_avoided = []
        
        for course in eligible_courses[:20]:  # Check more courses to account for conflicts
            # Check credit limit
            if total_credits + course.credits > max_credits:
                continue
            
            # Check for time conflicts
            has_conflict = False
            conflicting_course = None
            
            for added_course in selected_courses:
                if has_time_conflict(course, added_course):
                    has_conflict = True
                    conflicting_course = added_course
                    break
            
            if has_conflict:
                conflicts_avoided.append({
                    'course': course.code,
                    'conflicts_with': conflicting_course.code if conflicting_course else 'Unknown'
                })
                continue
            
            # No conflicts, add the course
            selected_courses.append(course)
            total_credits += course.credits
        
        for course in selected_courses:
            schedule.courses.append(course)
        
        schedule.total_credits = total_credits
        db.session.commit()
        
        response_data = {
            'message': 'Schedule generated successfully',
            'schedule': schedule.to_dict()
        }
        
        # Add conflict info if any were avoided
        if conflicts_avoided:
            response_data['conflicts_avoided'] = conflicts_avoided
            response_data['message'] = f'Schedule generated successfully. {len(conflicts_avoided)} time conflict(s) avoided.'
        
        # Tell the student which courses were withheld and why.
        if blocked_by_prereqs:
            response_data['blocked_by_prerequisites'] = blocked_by_prereqs
        if unscheduled_requirements:
            response_data['unscheduled_requirements'] = unscheduled_requirements
        
        return jsonify(response_data), 200
        
    except Exception as e:
        db.session.rollback()
        return error_response(e, 500)


# ==================== User Profile Routes ====================

@app.route('/api/users/<int:user_id>', methods=['GET', 'PUT'])
@login_required
def manage_user(user_id):
    """Get or update user profile"""
    try:
        current_user = get_current_user()
        
        # Users can only access their own profile
        if current_user.id != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        if request.method == 'GET':
            return jsonify(current_user.to_dict()), 200
        
        # PUT method - update profile
        data = request.get_json()
        
        # Update allowed fields
        if 'username' in data:
            # Check if username is taken by another user
            existing = User.query.filter_by(username=data['username']).first()
            if existing and existing.id != user_id:
                return jsonify({'error': 'Username already taken'}), 400
            current_user.username = data['username']
        
        if 'email' in data:
            # Check if email is taken by another user
            existing = User.query.filter_by(email=data['email']).first()
            if existing and existing.id != user_id:
                return jsonify({'error': 'Email already taken'}), 400
            current_user.email = data['email']
        
        if 'major' in data:
            current_user.major = data['major']
        if 'graduation_year' in data:
            current_user.graduation_year = as_int(data['graduation_year'])
        if 'current_year' in data:
            current_user.current_year = data['current_year']
        # Degree sequencing. The term matters as much as the year, and catalog
        # year decides which edition of the requirements applies.
        if 'graduation_term' in data:
            current_user.graduation_term = data['graduation_term'] or None
        if 'catalog_year' in data:
            current_user.catalog_year = as_int(data['catalog_year'])
        if 'takes_summer' in data:
            current_user.takes_summer = bool(data['takes_summer'])
        if 'minor' in data:
            current_user.minor = data['minor'] or None
        if 'gpa' in data:
            current_user.gpa = as_float(data['gpa'])
        if 'career_goal' in data:
            current_user.career_goal = data['career_goal']
        if 'learning_preferences' in data:
            current_user.learning_preferences = json.dumps(data['learning_preferences']) if isinstance(data['learning_preferences'], dict) else data['learning_preferences']
        if 'preferences' in data:
            if isinstance(data['preferences'], dict):
                merged = json.loads(current_user.preferences) if current_user.preferences else {}
                merged.update(data['preferences'])
                current_user.preferences = json.dumps(merged)
            else:
                current_user.preferences = data['preferences']
        if 'workload_capacity' in data:
            current_user.workload_capacity = as_int(data['workload_capacity'], 25)
        if 'risk_tolerance' in data:
            current_user.risk_tolerance = data['risk_tolerance']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': current_user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return error_response(e, 500)


@app.route('/api/users/<int:user_id>/preferences', methods=['GET', 'PUT'])
@login_required
def manage_user_preferences(user_id):
    """Get or update user preferences"""
    try:
        current_user = get_current_user()
        
        # Users can only access their own preferences
        if current_user.id != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        if request.method == 'GET':
            preferences = json.loads(current_user.preferences) if current_user.preferences else {}
            return jsonify({
                'user_id': user_id,
                'preferences': preferences,
                'major': current_user.major,
                'graduation_year': current_user.graduation_year
            }), 200
        
        # PUT method - update preferences
        data = request.get_json()
        
        if 'preferences' in data:
            incoming = data['preferences']
            if isinstance(incoming, str):
                incoming = json.loads(incoming)

            if isinstance(incoming, dict):
                # Merge rather than replace. The profile form only knows about
                # a handful of keys, and replacing wiped everything else it had
                # never heard of - completed_courses among them.
                existing = json.loads(current_user.preferences) if current_user.preferences else {}
                existing.update(incoming)
                current_user.preferences = json.dumps(existing)
            else:
                current_user.preferences = json.dumps(incoming)

            db.session.commit()
            
            return jsonify({
                'message': 'Preferences updated successfully',
                'preferences': json.loads(current_user.preferences) if current_user.preferences else {}
            }), 200
        
        return jsonify({'error': 'No preferences provided'}), 400
        
    except Exception as e:
        db.session.rollback()
        return error_response(e, 500)


@app.route('/api/schedules', methods=['GET'])
@login_required
def get_user_schedules():
    """Get all schedules for current user"""
    try:
        user = get_current_user()
        schedules = Schedule.query.filter_by(user_id=user.id).order_by(
            Schedule.created_at.desc()
        ).all()
        
        return jsonify({
            'schedules': [s.to_dict() for s in schedules]
        }), 200
        
    except Exception as e:
        return error_response(e, 500)


@app.route('/api/schedule', methods=['POST'])
@login_required
def create_schedule():
    """Create a new schedule"""
    try:
        user = get_current_user()
        data = request.get_json()
        
        name = data.get('name', 'New Schedule')
        semester = data.get('semester', 'Fall')
        year = data.get('year', 2025)
        course_ids = data.get('course_ids', [])
        max_credits = data.get('max_credits', 18)
        
        # Get the courses
        courses = Course.query.filter(Course.id.in_(course_ids)).all()
        
        # Calculate total credits
        total_credits = sum(c.credits for c in courses)
        
        # Get user's max credits preference
        preferences = json.loads(user.preferences) if user.preferences else {}
        user_max_credits = preferences.get('max_credits_per_semester', 18)
        
        # Check credit limit
        if total_credits > user_max_credits:
            return jsonify({
                'error': f'Total credits ({total_credits}) exceeds your maximum ({user_max_credits} credits)',
                'total_credits': total_credits,
                'max_credits': user_max_credits,
                'can_force': True
            }), 400
        
        # Check for time conflicts
        conflicts = []
        for i, course1 in enumerate(courses):
            for course2 in courses[i+1:]:
                if has_time_conflict(course1, course2):
                    conflicts.append({
                        'course1': f"{course1.code} {course1.name}",
                        'course2': f"{course2.code} {course2.name}"
                    })
        
        if conflicts:
            return jsonify({
                'error': 'Schedule has time conflicts',
                'conflicts': conflicts
            }), 400
        
        # Create the schedule
        schedule = Schedule(
            user_id=user.id,
            name=name,
            semester=semester,
            year=year,
            total_credits=total_credits
        )
        
        # Add courses to schedule
        for course in courses:
            schedule.courses.append(course)
        
        db.session.add(schedule)
        db.session.commit()
        
        return jsonify({
            'message': 'Schedule created successfully',
            'schedule': schedule.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return error_response(e, 500)


@app.route('/api/schedule/<int:schedule_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_schedule(schedule_id):
    """Get, update, or delete a specific schedule"""
    try:
        user = get_current_user()
        schedule = db.session.get(Schedule, schedule_id)
        
        if not schedule or schedule.user_id != user.id:
            return jsonify({'error': 'Schedule not found'}), 404
        
        if request.method == 'DELETE':
            schedule.courses = []
            db.session.delete(schedule)
            db.session.commit()
            return jsonify({'message': 'Schedule deleted successfully'}), 200
        
        if request.method == 'PUT':
            # Update schedule with new courses
            data = request.get_json()
            course_ids = data.get('course_ids', [])
            force_update = data.get('force_update', False)
            
            # Get the courses
            courses = Course.query.filter(Course.id.in_(course_ids)).all()
            
            # Calculate total credits
            total_credits = sum(c.credits for c in courses)
            old_credits = schedule.total_credits
            
            # Get user's max credits preference
            preferences = json.loads(user.preferences) if user.preferences else {}
            max_credits = preferences.get('max_credits_per_semester', 18)
            
            if not force_update:
                # Check credit limit - allow if reducing credits (even if still over limit)
                is_reducing = total_credits < old_credits
                
                if total_credits > max_credits and not is_reducing:
                    return jsonify({
                        'error': f'Total credits ({total_credits}) exceeds your maximum ({max_credits} credits)',
                        'total_credits': total_credits,
                        'max_credits': max_credits,
                        'can_force': True
                    }), 400
                
                # Check for time conflicts
                conflicts = []
                for i, course1 in enumerate(courses):
                    for course2 in courses[i+1:]:
                        if has_time_conflict(course1, course2):
                            conflicts.append({
                                'course1': f"{course1.code} {course1.name}",
                                'course2': f"{course2.code} {course2.name}"
                            })
                
                if conflicts:
                    return jsonify({
                        'error': 'Schedule has time conflicts',
                        'conflicts': conflicts
                    }), 400
            
            # Update the schedule
            schedule.courses = courses
            schedule.total_credits = total_credits
            
            db.session.commit()
            
            return jsonify({
                'message': 'Schedule updated successfully',
                'schedule': schedule.to_dict()
            }), 200
        
        # GET method
        return jsonify(schedule.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return error_response(e, 500)


@app.route('/api/schedule/<int:schedule_id>/weekly', methods=['GET'])
@login_required
def get_weekly_schedule(schedule_id):
    """Get weekly view of a schedule"""
    try:
        user = get_current_user()
        schedule = db.session.get(Schedule, schedule_id)
        
        if not schedule or schedule.user_id != user.id:
            return jsonify({'error': 'Schedule not found'}), 404
        
        weekly_schedule = {
            'Monday': [],
            'Tuesday': [],
            'Wednesday': [],
            'Thursday': [],
            'Friday': []
        }
        
        for course in schedule.courses:
            if course.time_slots:
                time_slots = json.loads(course.time_slots)
                for slot in time_slots:
                    days_str = slot.get('day', 'Monday')
                    
                    # Handle comma-separated days (e.g., "Monday,Wednesday,Friday")
                    if ',' in days_str:
                        days = [day.strip() for day in days_str.split(',')]
                    else:
                        days = [days_str.strip()]
                    
                    # Add course to each day it meets
                    for day in days:
                        if day in weekly_schedule:
                            start_time = slot.get('start_time', '09:00')
                            end_time = slot.get('end_time', '10:30')
                            weekly_schedule[day].append({
                                'course_code': course.code,
                                'course_name': course.name,
                                'time': f"{start_time} - {end_time}",
                                'start_time': start_time,  # For sorting
                                'room': slot.get('room', 'TBD'),
                                'credits': course.credits
                            })
        
        # Sort courses by start time within each day (properly as time, not string)
        def time_to_minutes(time_str):
            """Convert time string to minutes since midnight for proper sorting"""
            try:
                # Handle both 24-hour (14:00) and 12-hour (02:00 PM) formats
                time_str = time_str.strip()
                
                # Check if it's 12-hour format (contains AM/PM)
                if 'AM' in time_str.upper() or 'PM' in time_str.upper():
                    # Parse 12-hour format
                    time_str = time_str.upper().replace(' ', '')
                    is_pm = 'PM' in time_str
                    time_str = time_str.replace('AM', '').replace('PM', '')
                    
                    parts = time_str.split(':')
                    hours = int(parts[0])
                    minutes = int(parts[1]) if len(parts) > 1 else 0
                    
                    # Convert to 24-hour
                    if is_pm and hours != 12:
                        hours += 12
                    elif not is_pm and hours == 12:
                        hours = 0
                    
                    return hours * 60 + minutes
                else:
                    # Parse 24-hour format
                    parts = time_str.split(':')
                    hours = int(parts[0])
                    minutes = int(parts[1]) if len(parts) > 1 else 0
                    return hours * 60 + minutes
            except:
                return 0  # Default to midnight if parsing fails
        
        for day in weekly_schedule:
            weekly_schedule[day].sort(key=lambda x: time_to_minutes(x['start_time']))
        
        return jsonify(weekly_schedule), 200
        
    except Exception as e:
        return error_response(e, 500)


# ==================== Initialize Database ====================

# Columns added after the first release, with the SQL type used when a
# database predates them. db.create_all() creates missing tables but never
# alters existing ones, and this project has no migration tool.
_ADDED_USER_COLUMNS = {
    'is_admin': 'BOOLEAN NOT NULL DEFAULT {false}',
    'graduation_term': 'VARCHAR(20)',
    'catalog_year': 'INTEGER',
    'takes_summer': 'BOOLEAN NOT NULL DEFAULT {false}',
    'minor': 'VARCHAR(200)',
}


def ensure_user_schema():
    """Add user columns introduced after a database was first created."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if 'user' not in inspector.get_table_names():
        return []

    existing = {c['name'] for c in inspector.get_columns('user')}
    false_literal = '0' if db.engine.dialect.name == 'sqlite' else 'FALSE'

    added = []
    for column, ddl in _ADDED_USER_COLUMNS.items():
        if column in existing:
            continue
        # "user" is a reserved word in Postgres, so it stays quoted.
        db.session.execute(text(
            f'ALTER TABLE "user" ADD COLUMN {column} {ddl.format(false=false_literal)}'
        ))
        added.append(column)

    if added:
        db.session.commit()
        print(f"Added user column(s): {', '.join(added)}")
    return added


def ensure_admins():
    """Make sure at least one account can administer the catalog.

    Accounts listed in ADMIN_EMAILS are promoted. If that leaves nobody, the
    earliest account is promoted so the catalog tools are never locked away
    from everyone.
    """
    emails = {
        e.strip().lower()
        for e in os.getenv('ADMIN_EMAILS', '').split(',')
        if e.strip()
    }

    promoted = []
    if emails:
        for user in User.query.all():
            if user.email and user.email.lower() in emails and not user.is_admin:
                user.is_admin = True
                promoted.append(user.username)

    if not User.query.filter_by(is_admin=True).first():
        first = User.query.order_by(User.id).first()
        if first is not None:
            first.is_admin = True
            promoted.append(first.username)

    if promoted:
        db.session.commit()
        print(f"Granted catalog admin to: {', '.join(promoted)}")
    return promoted


def repair_prerequisite_encoding():
    """Rewrite prerequisite columns that were stored as nested JSON.

    An export/import round-trip used to wrap the JSON list inside another list,
    producing values like '["[\\"CS101\\"]"]'. Re-serializing flattens them
    back to '["CS101"]'. Idempotent: rows already clean are left untouched.
    """
    repaired = 0
    for course in Course.query.all():
        cleaned = serialize_prerequisites(course.prerequisites)
        if cleaned != (course.prerequisites or '[]'):
            course.prerequisites = cleaned
            repaired += 1

    if repaired:
        db.session.commit()
        print(f"Repaired prerequisite encoding on {repaired} course(s)")
    return repaired


def init_db():
    """Initialize database with sample data"""
    with app.app_context():
        db.create_all()
        
        # Check if we need sample data
        if Course.query.count() == 0:
            print("Loading sample courses with AI-ready data...")
            # Import sample data loader
            from load_sample_data import load_enhanced_courses
            load_enhanced_courses(db)
        
        # Bring an existing database up to the current schema
        ensure_user_schema()

        # Normalize any prerequisite values left nested by older imports
        repair_prerequisite_encoding()

        # Ensure the catalog always has an administrator
        ensure_admins()

        # Build course intelligence index
        courses = Course.query.all()
        course_intelligence.build_course_index([c.to_dict() for c in courses])
        
        print("Database initialized successfully!")


# ==================== Run Application ====================

if __name__ == '__main__':
    init_db()
    app.run(
        debug=os.getenv('FLASK_DEBUG', 'True') == 'True',
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5003))
    )

