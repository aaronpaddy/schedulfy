"""
Schedulfy 2.0 - AI-Powered Course Scheduler
Enhanced Flask backend with GPT-4 recommendations, workload prediction, and chat interface
"""

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import models
from models import db, User, Course, Schedule, ScheduleCourses, ChatHistory

# Import AI services
from ai_service import ai_recommender, workload_predictor, course_intelligence

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
# The frontend is served from a different domain than the API, so the session
# cookie is cross-site: browsers only send it when SameSite=None AND Secure.
app.config['SESSION_COOKIE_SAMESITE'] = 'None' if IS_PRODUCTION else 'Lax'
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
                
                # Handle comma-separated days
                days1 = [d.strip() for d in day1.split(',')] if day1 else []
                days2 = [d.strip() for d in day2.split(',')] if day2 else []
                
                # Check if any days overlap
                common_days = set(days1) & set(days2)
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
        return jsonify({'error': str(e)}), 400


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
        return jsonify({'error': str(e)}), 400


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
        completed_courses = preferences.get('completed_courses', [])
        
        student_profile = {
            'major': user.major,
            'year': user.current_year or 'Freshman',
            'gpa': user.gpa or 3.0,
            'completed_courses': completed_courses,
            'career_goal': user.career_goal or 'Not specified',
            'learning_preferences': user.learning_preferences,
            'target_credits': data.get('target_credits', 15),
            'focus_area': data.get('focus_area', '')
        }
        
        # Get available courses
        semester = data.get('semester', 'Fall')
        year = data.get('year', 2025)
        
        available_courses = Course.query.filter(
            (Course.semester == semester) | (Course.semester == 'Both')
        ).all()
        
        # Convert to dicts
        courses_data = [course.to_dict() for course in available_courses]
        
        # Get AI recommendations
        ai_response = ai_recommender.get_course_recommendations(
            student_profile,
            courses_data,
            num_recommendations=data.get('num_recommendations', 8)
        )
        
        # Return the AI response directly (it already has success and recommendations fields)
        return jsonify(ai_response), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
            'completed_courses': preferences.get('completed_courses', []),
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
        
        # Get available courses
        available_courses = Course.query.all()
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        completed_courses = preferences.get('completed_courses', [])
        
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
        
        # Get all available courses
        available_courses = Course.query.filter(
            (Course.semester == schedule.semester) | (Course.semester == 'Both')
        ).all()
        
        # Filter out courses already in schedule and completed courses
        eligible_courses = [
            c for c in available_courses 
            if c.code not in current_course_codes 
            and c.code not in completed_courses
            and c.credits <= remaining_credits  # Only courses that fit
        ]
        
        # Build student profile with current schedule context
        student_profile = {
            'major': user.major,
            'year': user.current_year,
            'gpa': user.gpa or 3.0,
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


@app.route('/api/courses/import', methods=['POST'])
@login_required
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
                        prereqs = course_data['prerequisites']
                        existing_course.prerequisites = json.dumps(prereqs if isinstance(prereqs, list) else [prereqs])
                    
                    if 'time_slots' in course_data:
                        slots = course_data['time_slots']
                        existing_course.time_slots = json.dumps(slots if isinstance(slots, list) else [])
                    
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
                        prerequisites=json.dumps(course_data.get('prerequisites', [])) if isinstance(course_data.get('prerequisites'), list) else '[]',
                        time_slots=json.dumps(course_data.get('time_slots', [])) if isinstance(course_data.get('time_slots'), list) else '[]',
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
        return jsonify({'error': str(e)}), 500


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
            'max_capacity', 'current_enrollment'
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
                course.prerequisites or '[]',
                course.time_slots or '[]',
                course.max_capacity or '',
                course.current_enrollment or ''
            ])
        
        output.seek(0)
        
        return output.getvalue(), 200, {
            'Content-Type': 'text/csv',
            'Content-Disposition': 'attachment; filename=courses_export.csv'
        }
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/courses/clear', methods=['DELETE'])
@login_required
def clear_courses():
    """Delete all courses from the database"""
    try:
        # Only allow admins or for development
        deleted = Course.query.delete()
        db.session.commit()
        
        return jsonify({
            'message': f'Successfully deleted {deleted} courses',
            'deleted_count': deleted
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/courses/scrape', methods=['POST'])
@login_required
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
        completed_courses = preferences.get('completed_courses', [])
        
        # Filter out completed courses
        eligible_courses = [
            c for c in available_courses 
            if c.code not in completed_courses and c.credits >= 1
        ]
        
        # Use AI recommendations if enabled
        if use_ai and os.getenv('OPENAI_API_KEY'):
            student_profile = {
                'major': user.major,
                'year': user.current_year,
                'gpa': user.gpa or 3.0,
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
        
        return jsonify(response_data), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


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
        if 'gpa' in data:
            current_user.gpa = as_float(data['gpa'])
        if 'career_goal' in data:
            current_user.career_goal = data['career_goal']
        if 'learning_preferences' in data:
            current_user.learning_preferences = json.dumps(data['learning_preferences']) if isinstance(data['learning_preferences'], dict) else data['learning_preferences']
        if 'preferences' in data:
            current_user.preferences = json.dumps(data['preferences']) if isinstance(data['preferences'], dict) else data['preferences']
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
        return jsonify({'error': str(e)}), 500


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
            current_user.preferences = json.dumps(data['preferences']) if isinstance(data['preferences'], dict) else data['preferences']
            db.session.commit()
            
            return jsonify({
                'message': 'Preferences updated successfully',
                'preferences': json.loads(current_user.preferences) if current_user.preferences else {}
            }), 200
        
        return jsonify({'error': 'No preferences provided'}), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


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
        return jsonify({'error': str(e)}), 500


# ==================== Initialize Database ====================

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

