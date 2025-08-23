# AI Interview Screener - Loom Video Script

## Video Structure (5-7 minutes)

### 1. Introduction (30 seconds)
"Hi, I'm [Your Name] and today I'm walking you through my AI Interview Screener backend - a complete system that automates the interview process using AI-generated questions, real voice calls, and intelligent response analysis. This is a fully functional MVP that can be deployed and used immediately."

### 2. Project Overview & Architecture (1 minute)
"Let me show you the overall architecture. This is a Django-based backend with these key components:

- **Django REST API** - Handles all the core functionality
- **OpenAI Integration** - Generates questions from job descriptions and analyzes responses
- **Twilio Voice Integration** - Makes real phone calls and records responses
- **Resume Parser** - Extracts text from PDF/DOCX files
- **PostgreSQL-ready** - Can scale to production databases

The system follows a simple flow: Job Description → AI Questions → Candidate Creation → Voice Interview → AI Analysis → Results."

### 3. Code Structure Walkthrough (1.5 minutes)
"Let me show you the clean, well-organized code structure:

**Main App Structure:**
- `interviews/models.py` - Database models for candidates, interviews, responses
- `interviews/services.py` - External integrations (OpenAI, Twilio, Resume parsing)
- `interviews/views.py` - API endpoints with proper authentication
- `interviews/serializers.py` - Data validation and transformation

**Key Design Decisions:**
- UUID primary keys for security
- API key authentication for all endpoints
- Phone number whitelisting for safety
- Webhook-based Twilio integration
- Environment variable configuration

The code is production-ready with proper error handling, logging, and security measures."

### 4. API Endpoints Demo (2 minutes)
"Now let me demonstrate the core API endpoints using Postman:

**1. Job Description to Questions:**
- POST to `/api/jd-to-questions/`
- Send job title and description
- AI generates 5-7 relevant questions
- Returns structured JSON with questions

**2. Create Candidate:**
- POST to `/api/candidates/`
- Upload resume (PDF/DOCX)
- System parses and extracts text
- Stores candidate with E.164 phone number

**3. Trigger Interview:**
- POST to `/api/trigger-interview/`
- Links candidate to job description
- Initiates real Twilio voice call
- Returns interview ID and call status

**4. Get Results:**
- GET `/api/interviews/{id}/results/`
- Returns comprehensive analysis
- Individual question scores and feedback
- Overall recommendation and strengths/weaknesses

All endpoints require API key authentication and return proper HTTP status codes."

### 5. Live Demo - End-to-End Flow (2 minutes)
"Let me show you a complete end-to-end workflow:

**Step 1: Create Job Description**
- I'll create a "Senior Software Engineer" position
- AI generates relevant technical and behavioral questions
- Questions are stored and ready for interviews

**Step 2: Add Candidate**
- Create a candidate with resume upload
- System parses the resume automatically
- Candidate is ready for interview

**Step 3: Trigger Interview**
- Start the automated voice interview
- Twilio makes a real phone call
- System asks questions and records responses

**Step 4: View Results**
- AI analyzes each response
- Provides scores and detailed feedback
- Generates final recommendation

The entire process is automated - from question generation to final analysis."

### 6. Technical Highlights (1 minute)
"Let me highlight some key technical features:

**Security & Safety:**
- API key authentication on all endpoints
- Phone number whitelisting prevents unauthorized calls
- CSRF protection on webhooks
- Environment variable configuration

**Scalability:**
- Django ORM with PostgreSQL support
- Stateless API design
- Webhook-based async processing
- File upload handling with proper storage

**AI Integration:**
- OpenAI GPT-3.5-turbo for question generation
- Context-aware response analysis
- Resume-based scoring context
- Structured JSON responses

**Voice Integration:**
- Real Twilio voice calls
- Automated question delivery
- Response recording and storage
- Webhook-based status updates"

### 7. Deployment & Usage (30 seconds)
"The system is ready for immediate deployment:

**Quick Setup:**
- Clone the repository
- Set environment variables
- Run Django migrations
- Deploy to Render.com/Railway/AWS

**Production Features:**
- Gunicorn WSGI server
- Whitenoise static file handling
- CORS configuration
- Comprehensive logging

The Postman collection is included for easy testing, and the README provides complete setup instructions."

### 8. Conclusion (30 seconds)
"This AI Interview Screener demonstrates a complete, production-ready system that:

- Automates the entire interview process
- Uses real voice calls with AI analysis
- Provides comprehensive candidate evaluation
- Scales from MVP to enterprise use

The code is clean, well-documented, and follows Django best practices. It's ready for immediate deployment and use.

Thank you for watching! The complete source code and documentation are available in the GitHub repository."

## Video Recording Tips

### Technical Setup
- Use screen recording software (Loom, OBS, or similar)
- Have Postman open with the collection loaded
- Have the code editor open to show key files
- Prepare a test resume file and job description

### Recording Flow
1. Start with introduction and overview
2. Show code structure (brief file navigation)
3. Demonstrate API endpoints in Postman
4. Run a complete end-to-end test
5. Show deployment configuration
6. End with summary and next steps

### Key Points to Emphasize
- **Real functionality** - not just mockups
- **Production-ready** code quality
- **Complete integration** of AI and voice
- **Security and safety** measures
- **Scalability** considerations
- **Easy deployment** process

### Demo Data to Prepare
- Sample job description for "Senior Software Engineer"
- Test resume file (PDF or DOCX)
- Test phone number (whitelisted)
- API key for authentication
- Sample interview questions and responses

## Post-Recording Checklist
- [ ] Upload to Loom/YouTube
- [ ] Add timestamps for key sections
- [ ] Include GitHub repository link
- [ ] Add description with key features
- [ ] Share with stakeholders for review
