# AI Interview Screener - Design Document

## Overall Architecture

The AI Interview Screener is a Django-based REST API that automates the interview process through AI-powered question generation, voice calls, and response analysis. The system follows a microservices-inspired architecture with clear separation of concerns.

**Core Components:**
- **Django REST API**: Main application server handling HTTP requests and business logic
- **OpenAI Integration**: AI service for question generation, response analysis, and audio transcription
- **Twilio Voice Service**: Automated voice calls with TTS and recording capabilities
- **File Processing**: Resume parsing for PDF/DOCX files
- **Webhook System**: Asynchronous callbacks for interview progression

**Deployment**: Hosted on Render.com with Gunicorn WSGI server and Whitenoise for static file serving.

## Data Design Summary

**Core Entities:**
- **Candidate**: Stores candidate information (name, email, phone, resume) with UUID primary keys
- **JobDescription**: Contains job details and AI-generated questions (stored as JSON)
- **Interview**: Tracks interview sessions with status, Twilio call details, and audio URLs
- **InterviewResponse**: Individual question responses with transcripts, scores, and feedback
- **InterviewResult**: Final evaluation with overall score, recommendation, and improvement areas

**Key Relationships:**
- One-to-Many: JobDescription → Interview
- One-to-Many: Candidate → Interview  
- One-to-Many: Interview → InterviewResponse
- One-to-One: Interview → InterviewResult

**Data Flow:**
1. Job descriptions are converted to structured questions via AI
2. Resume text is extracted and stored for context
3. Interview responses are transcribed and analyzed individually
4. Final results aggregate all responses for comprehensive evaluation

## AI Usage Points

**1. Question Generation (OpenAI GPT-4o-mini)**
- **Input**: Job title and description
- **Output**: 5-7 structured interview questions
- **Purpose**: Ensure questions are relevant to role requirements
- **Context**: Assesses technical skills, problem-solving, communication, and cultural fit

**2. Response Analysis (OpenAI GPT-4o-mini)**
- **Input**: Question, candidate response, resume context
- **Output**: Score (0-10) and detailed feedback
- **Purpose**: Evaluate response quality and relevance
- **Criteria**: Relevance, clarity, specificity, professionalism

**3. Final Recommendation (OpenAI GPT-4o-mini)**
- **Input**: All interview responses, resume context
- **Output**: Overall score, hire recommendation, strengths, improvement areas
- **Purpose**: Provide comprehensive candidate evaluation
- **Decision**: Hire/Consider/Reject with reasoning

## System Flow

```
[Client] → [Django API] → [AI Services] → [Twilio Voice] → [Candidate]
    ↓           ↓              ↓              ↓              ↓
[Results] ← [Analysis] ← [Transcription] ← [Recording] ← [Response]
```

**1. Setup Phase:**
- Client uploads job description → AI generates questions
- Client uploads candidate resume → Text extraction and storage
- Client creates candidate profile with E.164 phone number

**2. Interview Phase:**
- Client triggers interview → Twilio initiates voice call
- System presents questions sequentially via TTS
- Candidate responses are recorded and transcribed
- Each response is analyzed by AI for scoring and feedback

**3. Analysis Phase:**
- Audio recordings are transcribed using OpenAI Whisper
- Each response is analyzed individually with actual transcript
- All responses are aggregated for final evaluation
- AI generates comprehensive recommendation
- Results include overall score, strengths, and improvement areas
- Audio recordings are preserved for review

**4. Results Phase:**
- Client retrieves complete interview results
- Includes individual question scores, transcripts, and final recommendation
- Audio URLs provided for playback and verification

**Webhook Integration:**
- Twilio call status updates trigger interview progression
- Recording completion triggers audio transcription and response analysis
- Interview completion requires all questions to be answered
- Asynchronous processing ensures real-time updates

**Security & Validation:**
- API key authentication for all endpoints
- Phone number whitelisting for call security
- File type validation for resume uploads
- E.164 phone number format enforcement

**Live Deployment**: https://ai-screener-5.onrender.com/
