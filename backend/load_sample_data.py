"""
Load enhanced sample course data with AI-ready fields
"""

import json
from models import Course

def load_enhanced_courses(db):
    """Load sample courses with workload, difficulty, career tags"""
    
    sample_courses = [
        # Computer Science Courses
        {
            'code': 'CS101', 
            'name': 'Introduction to Computer Science', 
            'credits': 3,
            'department': 'Computer Science',
            'description': 'Introduction to computer science concepts, programming fundamentals, and computational thinking.',
            'semester': 'Both',
            'year': 2025,
            'time_slots': json.dumps([{
                'day': 'Monday,Wednesday,Friday',
                'start_time': '09:00 AM',
                'end_time': '10:30 AM',
                'room': 'CS 101'
            }]),
            'max_capacity': 150,
            'current_enrollment': 120,
            'difficulty': 2.5,
            'workload_hours': 8,
            'career_tags': json.dumps(['software-engineering', 'programming', 'foundations']),
            'skills_taught': json.dumps(['Python', 'Problem Solving', 'Algorithms']),
            'average_grade': 3.2,
            'completion_rate': 0.92,
            'student_rating': 4.2,
            'professor': 'Dr. Sarah Johnson',
            'professor_rating': 4.5
        },
        {
            'code': 'CS225',
            'name': 'Data Structures and Algorithms',
            'credits': 4,
            'department': 'Computer Science',
            'description': 'Fundamental data structures and algorithms. Topics include arrays, linked lists, stacks, queues, trees, graphs, sorting, and searching.',
            'semester': 'Both',
            'year': 2025,
            'time_slots': json.dumps([{
                'day': 'Tuesday,Thursday',
                'start_time': '11:00 AM',
                'end_time': '12:30 PM',
                'room': 'CS 225'
            }]),
            'max_capacity': 100,
            'current_enrollment': 85,
            'prerequisites': json.dumps(['CS101']),
            'difficulty': 4.2,
            'workload_hours': 14,
            'career_tags': json.dumps(['software-engineering', 'algorithms', 'data-structures']),
            'skills_taught': json.dumps(['C++', 'Data Structures', 'Algorithm Design', 'Complexity Analysis']),
            'average_grade': 2.9,
            'completion_rate': 0.85,
            'student_rating': 4.0,
            'professor': 'Dr. Michael Chen',
            'professor_rating': 4.3
        },
        {
            'code': 'CS341',
            'name': 'Machine Learning',
            'credits': 4,
            'department': 'Computer Science',
            'description': 'Introduction to machine learning, including supervised and unsupervised learning, neural networks, and deep learning.',
            'semester': 'Fall',
            'year': 2025,
            'time_slots': json.dumps([{
                'day': 'Monday,Wednesday',
                'start_time': '02:00 PM',
                'end_time': '03:30 PM',
                'room': 'CS 341'
            }]),
            'max_capacity': 80,
            'current_enrollment': 75,
            'prerequisites': json.dumps(['CS225', 'MATH231']),
            'difficulty': 4.5,
            'workload_hours': 16,
            'career_tags': json.dumps(['machine-learning', 'ai', 'data-science']),
            'skills_taught': json.dumps(['Python', 'TensorFlow', 'Neural Networks', 'ML Algorithms']),
            'average_grade': 3.1,
            'completion_rate': 0.88,
            'student_rating': 4.6,
            'professor': 'Dr. Emily Zhang',
            'professor_rating': 4.8
        },
        {
            'code': 'CS242',
            'name': 'Web Development',
            'credits': 3,
            'department': 'Computer Science',
            'description': 'Modern web development with React, Node.js, databases, and cloud deployment.',
            'semester': 'Both',
            'year': 2025,
            'time_slots': json.dumps([{
                'day': 'Tuesday,Thursday',
                'start_time': '09:30 AM',
                'end_time': '11:00 AM',
                'room': 'CS 242'
            }]),
            'max_capacity': 60,
            'current_enrollment': 55,
            'prerequisites': json.dumps(['CS101']),
            'difficulty': 3.5,
            'workload_hours': 12,
            'career_tags': json.dumps(['web-development', 'full-stack', 'javascript']),
            'skills_taught': json.dumps(['React', 'Node.js', 'REST APIs', 'MongoDB']),
            'average_grade': 3.4,
            'completion_rate': 0.93,
            'student_rating': 4.5,
            'professor': 'Prof. Alex Martinez',
            'professor_rating': 4.6
        },
        {
            'code': 'CS374',
            'name': 'Database Systems',
            'credits': 3,
            'department': 'Computer Science',
            'description': 'Database design, SQL, NoSQL databases, transactions, and query optimization.',
            'semester': 'Spring',
            'year': 2025,
            'time_slots': json.dumps([{
                'day': 'Monday,Wednesday,Friday',
                'start_time': '01:00 PM',
                'end_time': '02:00 PM',
                'room': 'CS 374'
            }]),
            'max_capacity': 70,
            'current_enrollment': 60,
            'prerequisites': json.dumps(['CS225']),
            'difficulty': 3.8,
            'workload_hours': 11,
            'career_tags': json.dumps(['database', 'backend', 'data-engineering']),
            'skills_taught': json.dumps(['SQL', 'PostgreSQL', 'MongoDB', 'Database Design']),
            'average_grade': 3.3,
            'completion_rate': 0.90,
            'student_rating': 4.2,
            'professor': 'Dr. James Wilson',
            'professor_rating': 4.4
        },
        
        # Mathematics Courses
        {
            'code': 'MATH220',
            'name': 'Calculus I',
            'credits': 4,
            'department': 'Mathematics',
            'description': 'Limits, derivatives, integrals, and applications of calculus.',
            'semester': 'Both',
            'year': 2025,
            'time_slots': json.dumps([{
                'day': 'Monday,Wednesday,Friday',
                'start_time': '08:00 AM',
                'end_time': '09:00 AM',
                'room': 'MATH 220'
            }]),
            'max_capacity': 200,
            'current_enrollment': 180,
            'difficulty': 3.5,
            'workload_hours': 12,
            'career_tags': json.dumps(['mathematics', 'engineering', 'sciences']),
            'skills_taught': json.dumps(['Calculus', 'Problem Solving', 'Mathematical Reasoning']),
            'average_grade': 2.8,
            'completion_rate': 0.82,
            'student_rating': 3.8,
            'professor': 'Dr. Robert Lee',
            'professor_rating': 4.0
        },
        {
            'code': 'MATH231',
            'name': 'Calculus II',
            'credits': 4,
            'department': 'Mathematics',
            'description': 'Techniques of integration, sequences and series, and applications.',
            'semester': 'Both',
            'year': 2025,
            'time_slots': json.dumps([{
                'day': 'Tuesday,Thursday',
                'start_time': '08:00 AM',
                'end_time': '09:30 AM',
                'room': 'MATH 231'
            }]),
            'max_capacity': 150,
            'current_enrollment': 130,
            'prerequisites': json.dumps(['MATH220']),
            'difficulty': 4.0,
            'workload_hours': 13,
            'career_tags': json.dumps(['mathematics', 'engineering', 'physics']),
            'skills_taught': json.dumps(['Integration', 'Series', 'Differential Equations']),
            'average_grade': 2.7,
            'completion_rate': 0.80,
            'student_rating': 3.7,
            'professor': 'Dr. Lisa Anderson',
            'professor_rating': 3.9
        },
        {
            'code': 'MATH415',
            'name': 'Linear Algebra',
            'credits': 3,
            'department': 'Mathematics',
            'description': 'Vector spaces, matrices, eigenvalues, and applications to computer science and data science.',
            'semester': 'Both',
            'year': 2025,
            'time_slots': json.dumps([{
                'day': 'Monday,Wednesday,Friday',
                'start_time': '11:00 AM',
                'end_time': '12:00 PM',
                'room': 'MATH 415'
            }]),
            'max_capacity': 100,
            'current_enrollment': 90,
            'prerequisites': json.dumps(['MATH220']),
            'difficulty': 4.0,
            'workload_hours': 11,
            'career_tags': json.dumps(['machine-learning', 'data-science', 'mathematics']),
            'skills_taught': json.dumps(['Linear Algebra', 'Matrix Operations', 'Vector Spaces']),
            'average_grade': 3.0,
            'completion_rate': 0.87,
            'student_rating': 4.1,
            'professor': 'Dr. Kevin Park',
            'professor_rating': 4.3
        },
        
        # Science Courses
        {
            'code': 'PHYS211',
            'name': 'University Physics I',
            'credits': 4,
            'department': 'Physics',
            'description': 'Mechanics, waves, and thermodynamics with calculus.',
            'semester': 'Both',
            'year': 2025,
            'time_slots': json.dumps([{
                'day': 'Tuesday,Thursday',
                'start_time': '02:00 PM',
                'end_time': '03:30 PM',
                'room': 'PHYS 211'
            }]),
            'max_capacity': 120,
            'current_enrollment': 100,
            'prerequisites': json.dumps(['MATH220']),
            'difficulty': 3.8,
            'workload_hours': 14,
            'career_tags': json.dumps(['physics', 'engineering', 'sciences']),
            'skills_taught': json.dumps(['Classical Mechanics', 'Problem Solving', 'Lab Techniques']),
            'average_grade': 2.9,
            'completion_rate': 0.84,
            'student_rating': 3.9,
            'professor': 'Dr. Patricia Brown',
            'professor_rating': 4.1
        },
        {
            'code': 'CHEM102',
            'name': 'General Chemistry',
            'credits': 4,
            'department': 'Chemistry',
            'description': 'Fundamental principles of chemistry including atomic structure, bonding, and reactions.',
            'semester': 'Both',
            'year': 2025,
            'time_slots': json.dumps([{
                'day': 'Monday,Wednesday',
                'start_time': '10:00 AM',
                'end_time': '11:30 AM',
                'room': 'CHEM 102'
            }]),
            'max_capacity': 100,
            'current_enrollment': 85,
            'difficulty': 3.5,
            'workload_hours': 12,
            'career_tags': json.dumps(['chemistry', 'sciences', 'pre-med']),
            'skills_taught': json.dumps(['Chemistry', 'Lab Skills', 'Scientific Method']),
            'average_grade': 3.0,
            'completion_rate': 0.86,
            'student_rating': 4.0,
            'professor': 'Dr. Daniel Kim',
            'professor_rating': 4.2
        },
        
        # General Education
        {
            'code': 'ENG101',
            'name': 'English Composition',
            'credits': 3,
            'department': 'English',
            'description': 'Academic writing, research, and critical thinking skills.',
            'semester': 'Both',
            'year': 2025,
            'time_slots': json.dumps([{
                'day': 'Monday,Wednesday,Friday',
                'start_time': '10:00 AM',
                'end_time': '11:00 AM',
                'room': 'ENG 101'
            }]),
            'max_capacity': 25,
            'current_enrollment': 22,
            'difficulty': 2.5,
            'workload_hours': 9,
            'career_tags': json.dumps(['communication', 'writing', 'general-ed']),
            'skills_taught': json.dumps(['Writing', 'Research', 'Critical Thinking']),
            'average_grade': 3.4,
            'completion_rate': 0.95,
            'student_rating': 4.3,
            'professor': 'Prof. Jennifer Taylor',
            'professor_rating': 4.5
        },
        {
            'code': 'HIST101',
            'name': 'World History',
            'credits': 3,
            'department': 'History',
            'description': 'Survey of world history from ancient civilizations to modern times.',
            'semester': 'Both',
            'year': 2025,
            'time_slots': json.dumps([{
                'day': 'Tuesday,Thursday',
                'start_time': '03:00 PM',
                'end_time': '04:30 PM',
                'room': 'HIST 101'
            }]),
            'max_capacity': 50,
            'current_enrollment': 45,
            'difficulty': 2.0,
            'workload_hours': 7,
            'career_tags': json.dumps(['humanities', 'general-ed', 'social-sciences']),
            'skills_taught': json.dumps(['Historical Analysis', 'Writing', 'Critical Thinking']),
            'average_grade': 3.5,
            'completion_rate': 0.96,
            'student_rating': 4.4,
            'professor': 'Dr. William Davis',
            'professor_rating': 4.6
        },
        {
            'code': 'PSYCH101',
            'name': 'Introduction to Psychology',
            'credits': 3,
            'department': 'Psychology',
            'description': 'Introduction to psychological science, including cognition, development, and social psychology.',
            'semester': 'Both',
            'year': 2025,
            'time_slots': json.dumps([{
                'day': 'Monday,Wednesday',
                'start_time': '01:00 PM',
                'end_time': '02:30 PM',
                'room': 'PSYCH 101'
            }]),
            'max_capacity': 80,
            'current_enrollment': 75,
            'difficulty': 2.3,
            'workload_hours': 8,
            'career_tags': json.dumps(['psychology', 'social-sciences', 'general-ed']),
            'skills_taught': json.dumps(['Psychology', 'Research Methods', 'Critical Thinking']),
            'average_grade': 3.3,
            'completion_rate': 0.94,
            'student_rating': 4.5,
            'professor': 'Dr. Maria Rodriguez',
            'professor_rating': 4.7
        },
        {
            'code': 'BIO101',
            'name': 'Introduction to Biology',
            'credits': 4,
            'department': 'Biology',
            'description': 'Fundamental concepts of biology including cell structure, genetics, and evolution.',
            'semester': 'Both',
            'year': 2025,
            'time_slots': json.dumps([{
                'day': 'Tuesday,Thursday',
                'start_time': '11:00 AM',
                'end_time': '12:30 PM',
                'room': 'BIO 101'
            }]),
            'max_capacity': 100,
            'current_enrollment': 90,
            'difficulty': 3.2,
            'workload_hours': 11,
            'career_tags': json.dumps(['biology', 'sciences', 'pre-med']),
            'skills_taught': json.dumps(['Biology', 'Lab Techniques', 'Scientific Method']),
            'average_grade': 3.1,
            'completion_rate': 0.89,
            'student_rating': 4.2,
            'professor': 'Dr. Christopher Moore',
            'professor_rating': 4.3
        },
        {
            'code': 'ECON101',
            'name': 'Principles of Microeconomics',
            'credits': 3,
            'department': 'Economics',
            'description': 'Supply and demand, market structures, and microeconomic policy.',
            'semester': 'Both',
            'year': 2025,
            'time_slots': json.dumps([{
                'day': 'Monday,Wednesday,Friday',
                'start_time': '09:00 AM',
                'end_time': '10:00 AM',
                'room': 'ECON 101'
            }]),
            'max_capacity': 100,
            'current_enrollment': 85,
            'difficulty': 3.0,
            'workload_hours': 9,
            'career_tags': json.dumps(['economics', 'business', 'social-sciences']),
            'skills_taught': json.dumps(['Economics', 'Analytical Thinking', 'Data Analysis']),
            'average_grade': 3.2,
            'completion_rate': 0.91,
            'student_rating': 4.1,
            'professor': 'Prof. Susan Wright',
            'professor_rating': 4.4
        }
    ]
    
    # Add courses to database
    for course_data in sample_courses:
        course = Course(**course_data)
        db.session.add(course)
    
    db.session.commit()
    print(f"Loaded {len(sample_courses)} enhanced courses with AI-ready data")

