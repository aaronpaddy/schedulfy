"""
Enhanced Database Models for Schedulfy 2.0
AI-ready models with workload, difficulty, and career relevance fields
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()


class User(db.Model):
    """Enhanced User model with AI-ready fields"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile information
    major = db.Column(db.String(100))
    graduation_year = db.Column(db.Integer)
    current_year = db.Column(db.String(20))  # Freshman, Sophomore, etc.
    gpa = db.Column(db.Float)
    
    # Career and preferences
    career_goal = db.Column(db.Text)
    learning_preferences = db.Column(db.Text)  # JSON string
    preferences = db.Column(db.Text)  # JSON string (time preferences, etc.)
    
    # AI personalization
    workload_capacity = db.Column(db.Integer, default=25)  # Hours per week
    risk_tolerance = db.Column(db.String(20), default='moderate')  # low, moderate, high
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    schedules = db.relationship('Schedule', backref='user', lazy=True)
    
    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches the hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'major': self.major,
            'graduation_year': self.graduation_year,
            'current_year': self.current_year,
            'gpa': self.gpa,
            'career_goal': self.career_goal,
            'learning_preferences': json.loads(self.learning_preferences) if self.learning_preferences else {},
            'preferences': json.loads(self.preferences) if self.preferences else {},
            'workload_capacity': self.workload_capacity,
            'risk_tolerance': self.risk_tolerance,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Course(db.Model):
    """Enhanced Course model with AI fields"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    department = db.Column(db.String(100), index=True)
    description = db.Column(db.Text)
    
    # Schedule information
    semester = db.Column(db.String(20))  # Fall, Spring, Both
    year = db.Column(db.Integer)
    time_slots = db.Column(db.Text)  # JSON string
    
    # Enrollment
    max_capacity = db.Column(db.Integer)
    current_enrollment = db.Column(db.Integer, default=0)
    
    # Prerequisites and requirements
    prerequisites = db.Column(db.Text)  # JSON string of required courses
    corequisites = db.Column(db.Text)  # JSON string
    
    # AI-ready fields
    difficulty = db.Column(db.Float, default=3.0)  # 1.0-5.0 scale
    workload_hours = db.Column(db.Float)  # Average hours per week
    career_tags = db.Column(db.Text)  # JSON array: ["machine-learning", "web-dev"]
    skills_taught = db.Column(db.Text)  # JSON array of skills
    
    # Analytics
    average_grade = db.Column(db.Float)  # GPA of students who took this
    completion_rate = db.Column(db.Float)  # % who complete vs drop
    student_rating = db.Column(db.Float)  # 1-5 stars
    
    # Professor information
    professor = db.Column(db.String(100))
    professor_rating = db.Column(db.Float)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert course to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'credits': self.credits,
            'department': self.department,
            'description': self.description,
            'semester': self.semester,
            'year': self.year,
            'time_slots': json.loads(self.time_slots) if self.time_slots else [],
            'max_capacity': self.max_capacity,
            'current_enrollment': self.current_enrollment,
            'prerequisites': json.loads(self.prerequisites) if self.prerequisites else [],
            'corequisites': json.loads(self.corequisites) if self.corequisites else [],
            'difficulty': self.difficulty,
            'workload_hours': self.workload_hours,
            'career_tags': json.loads(self.career_tags) if self.career_tags else [],
            'skills_taught': json.loads(self.skills_taught) if self.skills_taught else [],
            'average_grade': self.average_grade,
            'completion_rate': self.completion_rate,
            'student_rating': self.student_rating,
            'professor': self.professor,
            'professor_rating': self.professor_rating,
            'enrollment_percentage': (self.current_enrollment / self.max_capacity * 100) if self.max_capacity > 0 else 0
        }


class Schedule(db.Model):
    """Enhanced Schedule model"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100))  # Optional name like "Fall 2025 - Heavy Load"
    semester = db.Column(db.String(20), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    total_credits = db.Column(db.Integer, default=0)
    
    # AI predictions
    predicted_gpa = db.Column(db.Float)
    predicted_workload = db.Column(db.Float)  # Hours per week
    quality_score = db.Column(db.Float)  # AI-generated quality score
    risk_level = db.Column(db.String(20))  # low, moderate, high, very_high
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_enrolled = db.Column(db.Boolean, default=False)  # Actually enrolled in courses
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    courses = db.relationship('Course', secondary='schedule_courses', backref='schedules')
    
    def to_dict(self, include_courses=True):
        """Convert schedule to dictionary"""
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'semester': self.semester,
            'year': self.year,
            'total_credits': self.total_credits,
            'predicted_gpa': self.predicted_gpa,
            'predicted_workload': self.predicted_workload,
            'quality_score': self.quality_score,
            'risk_level': self.risk_level,
            'is_active': self.is_active,
            'is_enrolled': self.is_enrolled,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_courses:
            result['courses'] = [course.to_dict() for course in self.courses]
        
        return result


class ScheduleCourses(db.Model):
    """Association table for schedules and courses"""
    __tablename__ = 'schedule_courses'
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChatHistory(db.Model):
    """Store chat conversations for context"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    context = db.Column(db.Text)  # JSON with additional context
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'role': self.role,
            'content': self.message,
            'timestamp': self.created_at.isoformat() if self.created_at else None
        }

