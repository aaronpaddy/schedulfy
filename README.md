# 🎓 Schedulfy - AI-Powered Course Scheduler

An intelligent, AI-powered course scheduling platform for university students. Built with GPT-4, Schedulfy provides personalized course recommendations, conflict-free scheduling, and natural language chat assistance to help you plan your perfect academic schedule.

## ✨ Key Features

### 🤖 AI-Powered Features

- **AI Chat Assistant**: Natural language interface powered by GPT-4
  - Ask questions about courses in plain English
  - Get personalized recommendations based on your schedule
  - Context-aware suggestions that understand your current courses and credits
  - Conversational interface for building schedules

- **Intelligent Course Recommendations**: AI analyzes your profile and suggests optimal courses
  - Major-specific recommendations
  - Career goal alignment
  - Prerequisite awareness
  - Workload balancing

- **AI Schedule Builder**: Unified interface combining:
  - Natural language chat for course discovery
  - Visual schedule builder with drag-and-drop
  - Real-time AI recommendations
  - Workload predictions and analytics

- **Smart Conflict Detection**: Automatic time conflict checking
  - Prevents overlapping courses
  - Warns about scheduling issues
  - Suggests alternatives

### 📚 Course Management

- **Course Dataset Manager**:
  - Import courses from CSV/JSON files
  - Export schedules in multiple formats
  - Web scraping for university course catalogs
  - Course catalog browser with search and filters

- **Schedule Management**:
  - Create multiple schedules per semester
  - Weekly calendar view
  - Edit existing schedules with AI suggestions
  - Save and manage multiple schedule versions

### 👤 User Experience

- **User Authentication**: Secure login and signup
- **User Profiles**: 
  - Personal information (major, graduation year, classification)
  - Career goals for personalized AI recommendations
  - Preference management
- **Modern Dashboard**: 
  - Overview of all schedules
  - Stats cards showing courses, credits, and progress
  - Quick access to AI Builder
- **Responsive Design**: Works seamlessly on desktop and mobile

## 🏗️ Tech Stack

### Frontend
- **React.js** - Modern UI with hooks and functional components
- **Material-UI** - Professional, responsive design system
- **React Router** - Client-side routing
- **Context API** - State management for authentication

### Backend
- **Flask** - Python web framework
- **Python** - Backend logic and AI integration
- **SQLAlchemy ORM** with **SQLite** database
- **OpenAI GPT-4** - Natural language processing and recommendations
- **BeautifulSoup4** - Web scraping for course data

### AI/ML Stack
- **OpenAI API** - GPT-4 for conversational AI
- **scikit-learn** - Machine learning predictions
- **pandas & numpy** - Data processing
- **Custom recommendation engine** - Course matching algorithms

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Node.js 14+
- OpenAI API key

### Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=your-api-key-here" > .env
echo "SECRET_KEY=your-secret-key-here" >> .env

python app_ai.py
```

Backend runs on `http://localhost:5003`

### Frontend Setup
```bash
cd frontend
npm install
npm start
```

Frontend runs on `http://localhost:3000`

### First Time Setup
1. **Sign up** for an account
2. **Set your profile**: major, graduation year, classification
3. **Import courses** via Dataset Manager (CSV/JSON or web scraping)
4. **Start building** your schedule with AI assistance!

## 📖 How to Use

### 1. Create Your Profile
- Set major, graduation year, and current year classification
- Add career goals for better AI recommendations
- Configure max credits per semester

### 2. Import Course Data
**Option A: File Upload**
- Go to Dataset Manager
- Upload CSV or JSON file with course data
- System validates and imports courses

**Option B: Web Scraping**
- Enter university course catalog URL
- System extracts course information
- Review and import selected courses

### 3. Build Your Schedule with AI
**Start from scratch:**
- Click "AI Builder" in navigation
- Chat with AI about your requirements
- Add recommended courses to your schedule
- Save when satisfied

**Add to existing schedule:**
- Go to Dashboard → View schedule → "AI Suggestions"
- AI sees your current courses and remaining credits
- Get context-aware recommendations
- Add courses and save changes

### 4. AI Chat Tips
Try asking:
- "I need 15 credits with no Friday classes"
- "What courses go well with Data Structures?"
- "Suggest courses for machine learning career"
- "Can you see my current schedule?"
- "I want to balance my workload this semester"

## 🔧 API Endpoints

### AI Endpoints
- `POST /api/ai/chat` - Chat with AI assistant
- `GET /api/ai/recommendations` - Get AI course recommendations
- `POST /api/ai/suggest-for-schedule/<id>` - Get suggestions for existing schedule
- `POST /api/ai/workload-prediction` - Predict course workload
- `POST /api/ai/analyze-schedule` - Analyze schedule difficulty

### Course Endpoints
- `GET /api/courses` - List all courses
- `GET /api/courses/<id>` - Get course details
- `POST /api/courses/import` - Import courses from file
- `POST /api/courses/scrape` - Scrape courses from URL
- `GET /api/courses/export` - Export courses to CSV
- `DELETE /api/courses/clear` - Clear all courses

### Schedule Endpoints
- `GET /api/schedules` - Get user's schedules
- `POST /api/schedule/generate` - Generate new schedule
- `GET /api/schedule/<id>` - Get schedule details
- `PUT /api/schedule/<id>` - Update schedule
- `DELETE /api/schedule/<id>` - Delete schedule
- `GET /api/schedule/<id>/weekly` - Get weekly calendar view

### User Endpoints
- `POST /api/auth/signup` - Create account
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/check` - Check auth status
- `GET /api/users/<id>` - Get user profile
- `PUT /api/users/<id>` - Update profile
- `GET/PUT /api/users/<id>/preferences` - Manage preferences

## 🤖 How the AI Works

### Context-Aware Recommendations
The AI considers:
- Your major and career goals
- Current year classification (Freshman, Sophomore, etc.)
- Courses already in your schedule
- Remaining credits available
- Time conflicts
- Prerequisites and course sequences
- Workload balance

### Natural Language Understanding
GPT-4 processes your requests and:
- Understands scheduling constraints
- Suggests appropriate courses
- Explains recommendations
- Answers course-related questions
- Maintains conversation context

### Intelligent Features
- **Conflict Prevention**: Won't suggest courses that overlap
- **Credit Limits**: Respects your max credits per semester
- **Smart Suggestions**: Considers your schedule when recommending
- **Conversational**: Natural back-and-forth dialogue

## 📁 Project Structure

```
schedulfy/
├── backend/
│   ├── app_ai.py              # Main Flask application with AI routes
│   ├── ai_service.py          # AI/ML logic and OpenAI integration
│   ├── models.py              # SQLAlchemy database models
│   ├── load_sample_data.py    # Sample data loader
│   ├── requirements.txt       # Python dependencies
│   └── instance/
│       └── courses.db         # SQLite database
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AIChatBot.js           # AI chat interface
│   │   │   ├── AIRecommendations.js   # AI course suggestions
│   │   │   ├── WorkloadDashboard.js   # Workload analytics
│   │   │   └── Navbar.js              # Navigation
│   │   ├── pages/
│   │   │   ├── AIScheduleBuilder.js   # Main AI builder page
│   │   │   ├── Dashboard.js           # User dashboard
│   │   │   ├── ScheduleViewer.js      # Schedule details
│   │   │   ├── CourseCatalog.js       # Course browser
│   │   │   ├── UserProfile.js         # Profile management
│   │   │   ├── Login.js               # Authentication
│   │   │   └── Signup.js
│   │   ├── contexts/
│   │   │   └── AuthContext.js         # Authentication state
│   │   └── services/
│   │       └── api.js                 # API client
│   └── package.json
└── README.md
```

## 🎯 Key Components

### Backend
- **AIRecommender**: GPT-4 integration for course recommendations
- **WorkloadPredictor**: ML-based workload estimation
- **CourseIntelligence**: Course similarity and analysis
- **Authentication**: Flask-Login for user sessions
- **Conflict Checker**: Time overlap detection

### Frontend
- **AIScheduleBuilder**: Main scheduling interface
- **AIChatBot**: Natural language course assistant
- **AIRecommendations**: Visual course suggestion cards
- **Dashboard**: User overview and schedule management
- **AuthContext**: Global authentication state

## 🔐 Environment Variables

Create `backend/.env`:
```bash
OPENAI_API_KEY=sk-your-openai-api-key
SECRET_KEY=your-flask-secret-key
FLASK_ENV=development
FLASK_DEBUG=True
DATABASE_URL=sqlite:///courses.db
MAX_CREDITS_PER_SEMESTER=18
CORS_ORIGINS=http://localhost:3000
```

## 🌟 What Makes Schedulfy Different

1. **AI-First Design**: Built around GPT-4 from the ground up
2. **Context Awareness**: AI knows your current schedule and constraints
3. **Natural Language**: Talk to your scheduler like a human advisor
4. **Smart Conflicts**: Automatic conflict detection and prevention
5. **Modern UX**: Beautiful, responsive design with Material-UI
6. **Full-Stack**: Complete solution from database to AI to UI

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## 🎯 Future Enhancements

- **Advanced ML Models**: Custom trained models for better predictions
- **Multi-University Support**: Expand beyond single institution
- **Mobile App**: Native mobile applications
- **Calendar Integration**: Sync with Google Calendar, Outlook
- **Social Features**: Share schedules with friends
- **Professor Ratings**: Integrate RateMyProfessor data
- **Real-time Updates**: Live course availability tracking

## 📞 Support

For questions or issues:
- Open a GitHub issue
- Check existing documentation
- Contact the development team

---

**Built with ❤️ and 🤖 AI for students who want smarter, easier course scheduling**

*Powered by GPT-4 • React.js • Flask • Python • SQLite • BeautifulSoup4*
