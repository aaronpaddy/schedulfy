"""
AI Service Layer for Schedulfy
Handles all AI/ML operations including recommendations, chat, and predictions
"""

import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
from course_utils import parse_prerequisites

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY', ''))


class AIRecommendationEngine:
    """
    AI-powered course recommendation engine using GPT-4
    """
    
    def __init__(self):
        self.model = "gpt-4"
        self.max_tokens = 2000
    
    def get_course_recommendations(
        self, 
        student_profile: Dict[str, Any], 
        available_courses: List[Dict[str, Any]],
        num_recommendations: int = 8
    ) -> Dict[str, Any]:
        """
        Generate personalized course recommendations using AI
        
        Args:
            student_profile: Student information (major, year, completed courses, goals)
            available_courses: List of available courses
            num_recommendations: Number of courses to recommend
        
        Returns:
            Dictionary with recommended courses and explanations
        """
        try:
            # Format courses for prompt
            courses_text = self._format_courses_for_prompt(available_courses)
            
            # Build the prompt
            prompt = f"""You are an expert academic advisor for university students. Analyze the student profile and recommend the most suitable courses for next semester.

Student Profile:
- Major: {student_profile.get('major', 'Undeclared')}
- Current Year: {student_profile.get('year', 'Freshman')}
- GPA: {student_profile.get('gpa', 'N/A')}
- Completed Courses: {', '.join(student_profile.get('completed_courses', []))}
- Career Goal: {student_profile.get('career_goal', 'Not specified')}
- Learning Preferences: {student_profile.get('learning_preferences', 'Not specified')}
- Target Credits: {student_profile.get('target_credits', 15)}

Available Courses (top 50):
{courses_text}

Task: Recommend {num_recommendations} courses that:
1. Align with the student's major requirements and career goals
2. Build upon completed coursework
3. Provide appropriate academic challenge
4. Balance workload effectively
5. Support long-term career objectives

Only recommend courses whose prerequisites the student has already completed,
based on the prerequisite list shown for each course and the student's completed
courses above. If a strong match is blocked by a missing prerequisite, recommend
the prerequisite instead.

For each recommended course, provide:
- Course code and name
- Reasoning (2-3 sentences explaining why this course is ideal)
- Career relevance (how it helps achieve their career goal)
- Difficulty level (1-5 scale) - copy the value given for the course; only
  estimate it when the course list shows none
- Estimated workload (hours per week - copy the value given for the course;
  only estimate it when the course list shows none. Not the same as credits)
- Prerequisites status (met/not met), derived from the data above

Format your response as a JSON array of objects with these fields:
[
  {{
    "course_code": "CS225",
    "course_name": "Data Structures",
    "reasoning": "Foundational course that builds on CS125...",
    "career_relevance": "Essential for software engineering roles...",
    "difficulty": 4,
    "estimated_workload": 12,
    "prerequisites_met": true,
    "priority": "high"
  }},
  ...
]
"""
            
            # Call OpenAI API
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert academic advisor who provides personalized, thoughtful course recommendations. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=self.max_tokens
            )
            
            # Parse response
            ai_response = response.choices[0].message.content
            
            # Extract JSON from response
            recommendations = self._parse_json_response(ai_response)
            
            return {
                'success': True,
                'recommendations': recommendations,
                'explanation': f"Generated {len(recommendations)} personalized recommendations based on your profile",
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"Error in AI recommendations: {e}")
            return {
                'success': False,
                'error': str(e),
                'recommendations': [],
                'fallback': True
            }
    
    def chat_schedule_assistant(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        student_context: Dict[str, Any],
        available_courses: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Natural language chat interface for schedule building
        
        Args:
            user_message: User's message
            conversation_history: Previous messages
            student_context: Student profile and preferences
            available_courses: Available courses
        
        Returns:
            AI response with suggested courses
        """
        try:
            # Format context
            courses_summary = self._format_courses_summary(available_courses)
            
            # Build current schedule info if available
            current_schedule_info = ""
            if student_context.get('current_schedule'):
                schedule_courses = student_context['current_schedule']
                course_list = [f"{c.get('code')} - {c.get('name')} ({c.get('credits')}cr)" for c in schedule_courses]
                current_credits = student_context.get('current_credits', 0)
                max_credits = student_context.get('max_credits', 18)
                remaining_credits = student_context.get('remaining_credits', 18)
                
                current_schedule_info = f"""
CURRENT SCHEDULE (IMPORTANT - You CAN see this!):
- Schedule: {student_context.get('schedule_name', 'Current Schedule')}
- Courses Currently Selected: {len(schedule_courses)}
  {chr(10).join(f'  • {course}' for course in course_list)}
- Total Credits: {current_credits} / {max_credits}
- Credits Available: {remaining_credits}

Your task: Suggest courses that COMPLEMENT the above schedule, avoid time conflicts, and fit within the remaining {remaining_credits} credits.
"""
            
            system_prompt = f"""You are Schedulfy AI, an intelligent academic advisor chatbot. Help students build their perfect schedule through natural conversation.

Student Context:
- Name: {student_context.get('name', 'Student')}
- Major: {student_context.get('major', 'Undeclared')}
- Year: {student_context.get('year', 'Freshman')}
- Completed Courses: {', '.join(student_context.get('completed_courses', []))}
- Career Goal: {student_context.get('career_goal', 'Not specified')}
{current_schedule_info}
Available Courses Summary:
{courses_summary}

Guidelines:
1. Be conversational, friendly, and supportive
2. YOU CAN SEE their current schedule above - use it to make smart suggestions
3. Suggest courses that complement what they already have
4. Warn about time conflicts if you notice them
5. Consider remaining credit availability
6. Explain why each course is a good fit
7. Keep responses concise (2-3 paragraphs max)

When suggesting courses, format them clearly:
📚 **CS225 - Data Structures** (4 credits)
   ✅ Why: Builds on CS125, essential for software development
   ⏰ Workload: ~12 hrs/week
"""
            
            # Build messages
            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Add conversation history
            messages.extend(conversation_history[-10:])  # Last 10 messages
            
            # Add current message
            messages.append({"role": "user", "content": user_message})
            
            # Call OpenAI
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,
                max_tokens=800
            )
            
            ai_message = response.choices[0].message.content
            
            # Extract course codes mentioned
            suggested_courses = self._extract_course_codes(ai_message, available_courses)
            
            return {
                'success': True,
                'message': ai_message,
                'suggested_courses': suggested_courses,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            print(f"Error in chat assistant: {e}")
            return {
                'success': False,
                'message': "I'm having trouble connecting right now. Please try again in a moment.",
                'error': str(e)
            }
    
    def analyze_schedule_quality(
        self,
        schedule: List[Dict[str, Any]],
        student_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        AI analysis of schedule quality with suggestions for improvement
        """
        try:
            schedule_text = "\n".join([
                f"- {c['code']}: {c['name']} ({c['credits']} credits)"
                for c in schedule
            ])
            
            prompt = f"""Analyze this student's proposed schedule and provide detailed feedback.

Student Profile:
- Major: {student_profile.get('major')}
- Year: {student_profile.get('year')}
- Career Goal: {student_profile.get('career_goal')}

Proposed Schedule:
{schedule_text}

Total Credits: {sum(c['credits'] for c in schedule)}

Provide a comprehensive analysis including:
1. Overall quality score (1-10)
2. Strengths (what's good about this schedule)
3. Potential concerns (workload, prerequisites, balance)
4. Suggestions for improvement
5. Career alignment assessment

Format as JSON:
{{
  "quality_score": 8,
  "grade": "B+",
  "strengths": ["Good balance of theory and practice", "..."],
  "concerns": ["Heavy workload in weeks 8-10", "..."],
  "suggestions": ["Consider swapping X for Y", "..."],
  "career_alignment": "Strong alignment with software engineering goals",
  "predicted_gpa": 3.6,
  "predicted_workload": 18,
  "risk_level": "moderate"
}}
"""
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an academic advisor analyzing course schedules. Respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=1000
            )
            
            analysis = self._parse_json_response(response.choices[0].message.content)
            
            return {
                'success': True,
                'analysis': analysis
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _format_courses_for_prompt(self, courses: List[Dict], limit: int = 50) -> str:
        """Format courses for AI prompt.

        Includes the prerequisite, difficulty and workload values held in the
        database. Without them the model invented all three from the course
        code alone.
        """
        formatted = []
        for i, course in enumerate(courses[:limit]):
            line = (
                f"{i+1}. {course['code']} - {course['name']} "
                f"({course['credits']} cr) - {course.get('department', 'N/A')}"
            )

            prereqs = parse_prerequisites(course.get('prerequisites'))
            line += f" | prerequisites: {', '.join(prereqs) if prereqs else 'none'}"

            if course.get('difficulty') is not None:
                line += f" | difficulty: {course['difficulty']}/5"
            if course.get('workload_hours') is not None:
                line += f" | workload: {course['workload_hours']} hrs/wk"

            tags = course.get('career_tags')
            if isinstance(tags, list) and tags:
                line += f" | career tags: {', '.join(tags)}"

            formatted.append(line)
        return "\n".join(formatted)
    
    def _format_courses_summary(self, courses: List[Dict], limit: int = 30) -> str:
        """Concise course summary for chat context"""
        departments = {}
        for course in courses[:limit]:
            dept = course.get('department', 'Other')
            if dept not in departments:
                departments[dept] = []
            departments[dept].append(f"{course['code']} - {course['name']}")
        
        summary = []
        for dept, course_list in departments.items():
            summary.append(f"{dept}: {', '.join(course_list[:5])}")
        
        return "\n".join(summary)
    
    def _parse_json_response(self, response: str) -> Any:
        """Extract and parse JSON from AI response"""
        try:
            # Try direct parse
            return json.loads(response)
        except json.JSONDecodeError:
            # Try to find JSON in response
            import re
            json_match = re.search(r'\[.*\]|\{.*\}', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
            return []
    
    def _extract_course_codes(self, text: str, available_courses: List[Dict]) -> List[str]:
        """Extract course codes mentioned in text"""
        import re
        codes = []
        
        # Extract potential course codes
        pattern = r'\b([A-Z]{2,4}\s?\d{3,4})\b'
        matches = re.findall(pattern, text)
        
        # Verify against available courses
        available_codes = {c['code'] for c in available_courses}
        
        for match in matches:
            normalized = match.replace(' ', '')
            if normalized in available_codes:
                codes.append(normalized)
        
        return list(set(codes))


class WorkloadPredictor:
    """
    ML-based workload prediction system
    """
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=100)
        self.model = None
        self._load_or_train_model()
    
    def _load_or_train_model(self):
        """Load existing model or train new one"""
        try:
            import joblib
            self.model = joblib.load('workload_model.pkl')
        except:
            # Train a simple model with default data
            self._train_default_model()
    
    def _train_default_model(self):
        """Train a basic model with synthetic data"""
        from sklearn.ensemble import RandomForestRegressor
        
        # Synthetic training data based on common patterns
        # Features: [credits, level (100-400), is_cs, is_math, is_lab]
        X_train = np.array([
            [3, 100, 1, 0, 0],  # CS intro course
            [4, 200, 1, 0, 0],  # CS intermediate
            [3, 300, 1, 0, 0],  # CS advanced
            [4, 100, 0, 1, 0],  # Math intro
            [4, 200, 0, 1, 0],  # Math intermediate
            [3, 100, 0, 0, 0],  # General ed
            [4, 200, 1, 0, 1],  # CS with lab
            [3, 300, 0, 0, 0],  # Upper level elective
        ])
        
        # Target: hours per week
        y_train = np.array([8, 12, 14, 10, 13, 6, 15, 9])
        
        self.model = RandomForestRegressor(n_estimators=10, random_state=42)
        self.model.fit(X_train, y_train)
    
    def predict_course_workload(self, course: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict workload for a single course
        
        Returns:
            Dictionary with workload predictions
        """
        try:
            # Extract features
            credits = course.get('credits', 3)
            code = course.get('code', '')
            
            # Extract course level
            level = int(''.join(filter(str.isdigit, code))[:3]) if code else 100
            
            # Department flags
            is_cs = 1 if 'CS' in code.upper() else 0
            is_math = 1 if 'MATH' in code.upper() else 0
            is_lab = 1 if 'lab' in course.get('name', '').lower() else 0
            
            features = np.array([[credits, level, is_cs, is_math, is_lab]])
            
            # Predict
            if self.model:
                base_hours = self.model.predict(features)[0]
            else:
                # Fallback calculation
                base_hours = credits * 3  # Rule of thumb: 3 hrs per credit
            
            # Add variability based on difficulty
            difficulty_multiplier = course.get('difficulty', 3) / 3.0
            predicted_hours = base_hours * difficulty_multiplier
            
            return {
                'hours_per_week': round(predicted_hours, 1),
                'min_hours': round(predicted_hours * 0.8, 1),
                'max_hours': round(predicted_hours * 1.3, 1),
                'confidence': 0.75
            }
            
        except Exception as e:
            print(f"Error predicting workload: {e}")
            return {
                'hours_per_week': course.get('credits', 3) * 3,
                'min_hours': course.get('credits', 3) * 2,
                'max_hours': course.get('credits', 3) * 4,
                'confidence': 0.5
            }
    
    def predict_schedule_workload(self, schedule: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Predict total workload for entire schedule with weekly breakdown
        """
        total_hours = 0
        course_workloads = []
        
        for course in schedule:
            workload = self.predict_course_workload(course)
            total_hours += workload['hours_per_week']
            course_workloads.append({
                'course': course['code'],
                'hours': workload['hours_per_week']
            })
        
        # Generate weekly forecast (simplified)
        weeks = []
        for week in range(1, 17):
            # Add variability: exam weeks (8, 16) are heavier
            multiplier = 1.5 if week in [8, 16] else 1.0
            if week == 9:  # Spring break
                multiplier = 0.3
            weeks.append(round(total_hours * multiplier, 1))
        
        # Assess risk
        if total_hours < 15:
            risk_level = 'low'
            risk_message = 'Light workload - you have capacity for more'
        elif total_hours < 25:
            risk_level = 'moderate'
            risk_message = 'Balanced workload - manageable for most students'
        elif total_hours < 35:
            risk_level = 'high'
            risk_message = 'Heavy workload - requires strong time management'
        else:
            risk_level = 'very_high'
            risk_message = 'Extremely heavy workload - consider reducing courses'
        
        return {
            'total_hours_per_week': round(total_hours, 1),
            'course_breakdown': course_workloads,
            'weekly_forecast': weeks,
            'risk_level': risk_level,
            'risk_message': risk_message,
            'busiest_weeks': [8, 16],
            'lightest_week': 9
        }


class CourseIntelligence:
    """
    Course analysis and similarity detection
    """
    
    def __init__(self):
        # English stop words stop generic catalog phrasing ("introduction to
        # the study of") from dominating the similarity score.
        self.vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
        self.course_embeddings = None
        self.courses_cache = []
    
    def build_course_index(self, courses: List[Dict[str, Any]]):
        """Build TF-IDF index for course similarity"""
        try:
            self.courses_cache = courses
            
            # Create text representation of each course. Department and
            # career tags are repeated so subject area outweighs incidental
            # wording shared across unrelated catalog entries.
            def course_text(c):
                tags = c.get('career_tags')
                tags_text = ' '.join(tags) if isinstance(tags, list) else ''
                department = c.get('department', '')
                return ' '.join([
                    c.get('name', ''),
                    c.get('description', ''),
                    department, department,
                    tags_text, tags_text,
                ])

            course_texts = [course_text(c) for c in courses]
            
            # Build embeddings
            self.course_embeddings = self.vectorizer.fit_transform(course_texts)
            
        except Exception as e:
            print(f"Error building course index: {e}")
    
    def find_similar_courses(self, course_id: int, top_n: int = 5) -> List[Dict[str, Any]]:
        """Find similar courses using TF-IDF similarity"""
        try:
            # A sparse matrix has no truth value, so compare against None
            # explicitly - `not matrix` raises and silently killed this feature.
            if self.course_embeddings is None or not self.courses_cache:
                return []
            
            # Find course index
            course_idx = next(
                (i for i, c in enumerate(self.courses_cache) if c.get('id') == course_id),
                None
            )
            
            if course_idx is None:
                return []
            
            # Calculate similarities
            course_vector = self.course_embeddings[course_idx]
            similarities = cosine_similarity(course_vector, self.course_embeddings)[0]
            
            # Get top N (excluding self)
            similar_indices = similarities.argsort()[-top_n-1:-1][::-1]
            
            similar_courses = []
            for idx in similar_indices:
                course = self.courses_cache[idx].copy()
                course['similarity_score'] = float(similarities[idx])
                similar_courses.append(course)
            
            return similar_courses
            
        except Exception as e:
            print(f"Error finding similar courses: {e}")
            return []


class CurriculumExtractor:
    """Turn an uploaded degree plan into structured curriculum rows.

    Output is always a DRAFT. Degree sheets photograph badly, merge columns and
    footnote their alternatives, so extraction is presented to the student for
    correction and never saved directly.
    """

    def __init__(self):
        # Reading an image needs a vision-capable model; the plain gpt-4 used
        # elsewhere in this file cannot accept image input.
        self.model = os.getenv('OPENAI_VISION_MODEL', 'gpt-4o')
        self.max_tokens = 4000

    INSTRUCTIONS = """You extract degree requirements from a university curriculum sheet.

Return ONLY a JSON array. One object per course, with these fields:
  course_code      e.g. "CS225". Use the code exactly as printed.
  title            the course name as printed, or null
  credits          number, or null if not shown
  category         one of "core", "elective", "gen-ed", "other" - your best read
  offered_terms    array like ["Fall"] or ["Fall","Spring"], [] if not stated
  suggested_year   1-4 if the sheet places it in a year, else null
  suggested_term   "Fall"/"Spring"/"Summer" if placed, else null
  prerequisites    array of course codes if stated, else []
  notes            anything ambiguous a student should check, else null

Rules:
- Transcribe only what the document shows. Never invent a course, a code or a
  credit value. If a field is not shown, use null or [].
- A placeholder like "Technical Elective" or "Humanities I" IS a requirement.
  Keep it, set course_code to the label as printed, and category "elective"
  or "gen-ed".
- When a requirement offers alternatives ("CS210 or CS220"), emit the first
  and record the alternatives in notes.
- Do not include totals, GPA rules, headings or footnotes as courses.
- Return [] if the document contains no course requirements."""

    def extract(self, text: Optional[str] = None, images: Optional[List[str]] = None):
        """Extract rows from document text and/or base64 data-URL images."""
        images = images or []
        if not text and not images:
            return {'success': False, 'error': 'No curriculum content provided', 'courses': []}

        content = [{'type': 'text', 'text': self.INSTRUCTIONS}]
        if text:
            content.append({
                'type': 'text',
                'text': f"Curriculum document text:\n\n{text[:20000]}",
            })
        for image in images:
            content.append({'type': 'image_url', 'image_url': {'url': image}})

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': 'You transcribe academic documents into structured JSON. You never invent data.'},
                    {'role': 'user', 'content': content},
                ],
                temperature=0,
                max_tokens=self.max_tokens,
            )
            raw = response.choices[0].message.content
            courses = self._parse_array(raw)
            return {
                'success': True,
                'courses': courses,
                'count': len(courses),
                'model': self.model,
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'courses': []}

    @staticmethod
    def _parse_array(raw: str):
        """Pull a JSON array out of the reply, tolerating code fences."""
        if not raw:
            return []
        text = raw.strip()
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        start, end = text.find('['), text.rfind(']')
        if start == -1 or end == -1:
            return []
        try:
            parsed = json.loads(text[start:end + 1])
        except (ValueError, TypeError):
            return []
        return [c for c in parsed if isinstance(c, dict) and c.get('course_code')]


# Global instances
ai_recommender = AIRecommendationEngine()
workload_predictor = WorkloadPredictor()
course_intelligence = CourseIntelligence()
curriculum_extractor = CurriculumExtractor()

