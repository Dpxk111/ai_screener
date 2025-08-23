# AI Interview Screener Backend

A complete AI-powered interview screening system that automates the interview process using voice calls, AI-generated questions, and intelligent response analysis.

**🌐 Live Demo**: https://ai-screener-5.onrender.com/

## Features

- **JD to Questions**: Convert job descriptions to 5-7 relevant interview questions using AI
- **Resume Parsing**: Upload and parse PDF/DOCX resumes for context
- **Candidate Management**: Create and manage candidates with E.164 phone numbers
- **Automated Interviews**: Trigger real voice calls with TTS questions and recording
- **AI Analysis**: Score responses and generate recommendations
- **Results Retrieval**: Get comprehensive interview results with audio links

## Tech Stack

- **Backend**: Django 5.2.5 + Django REST Framework
- **AI**: OpenAI GPT-4o-mini for question generation and response analysis
- **Voice**: Twilio for automated voice calls and recording
- **File Processing**: PyPDF2 and python-docx for resume parsing
- **Deployment**: Gunicorn + Whitenoise for production on Render.com

## Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd ai_screener

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

Copy `env.example` to `.env` and configure:

```bash
cp env.example .env
```

Edit `.env` with your actual values:

```env
# Django Settings
SECRET_KEY=your-django-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,localhost,127.0.0.1

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
TWILIO_ACCOUNT_SID=your-twilio-account-sid-here
TWILIO_AUTH_TOKEN=your-twilio-auth-token-here
TWILIO_PHONE_NUMBER=+1234567890

# Security
API_KEY=your-custom-api-key-here
WHITELISTED_NUMBERS=+1234567890,+1987654321

# Webhook URLs (for production)
WEBHOOK_BASE_URL=https://ai-screener-5.onrender.com
```

### 3. Database Setup

```bash
# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### 4. Run Development Server

```bash
python manage.py runserver
```

## API Endpoints

### Authentication
All endpoints require an API key in the header: `X-API-Key: your-api-key`

### Core Endpoints

1. **JD to Questions** - `POST /api/jd-to-questions/`
   - Convert job description to interview questions

2. **Upload Resume** - `POST /api/upload-resume/`
   - Parse PDF/DOCX resume files

3. **Create Candidate** - `POST /api/candidates/`
   - Create candidate with E.164 phone number

4. **Trigger Interview** - `POST /api/trigger-interview/`
   - Initiate automated voice interview

5. **Get Results** - `GET /api/interviews/{id}/results/`
   - Retrieve interview results and recommendations

### List Endpoints

- `GET /api/candidates/list/` - List all candidates
- `GET /api/interviews/list/` - List all interviews
- `GET /api/job-descriptions/list/` - List all job descriptions

## Postman Collection

Import the provided Postman collection and environment:

1. **Collection**: `AI_Interview_Screener.postman_collection.json`
2. **Environment**: `AI_Interview_Screener.postman_environment.json`

The environment is pre-configured with the live deployment URL. Update the environment variables with your actual values:
- `base_url`: https://ai-screener-5.onrender.com (pre-configured)
- `api_key`: Your API key
- Other IDs will be populated as you use the API

## Deployment

### Render.com Deployment

1. **Create Render Account**
   - Sign up at [render.com](https://render.com)
   - Connect your GitHub repository

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Choose the repository branch (main/master)

3. **Configure Service Settings**
   - **Name**: `ai-screener-5` (or your preferred name)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn ai_screener.wsgi:application`

4. **Set Environment Variables**
   In the Render dashboard, add these environment variables:
   ```
   SECRET_KEY=your-django-secret-key-here
   OPENAI_API_KEY=your-openai-api-key-here
   TWILIO_ACCOUNT_SID=your-twilio-account-sid-here
   TWILIO_AUTH_TOKEN=your-twilio-auth-token-here
   TWILIO_PHONE_NUMBER=your-twilio-phone-number
   API_KEY=your-custom-api-key-here
   WHITELISTED_NUMBERS=+1234567890,+1987654321
   WEBHOOK_BASE_URL=https://ai-screener-5.onrender.com
   DEBUG=False
   ALLOWED_HOSTS=ai-screener-5.onrender.com
   ```

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy your application
   - The first deployment may take 5-10 minutes

6. **Run Migrations**
   - In the Render dashboard, go to your service
   - Click on "Shell" tab
   - Run: `python manage.py migrate`

7. **Access Your Application**
   - Your app will be available at: `https://ai-screener-5.onrender.com`
   - The `WEBHOOK_BASE_URL` is already configured for this deployment

### Railway Deployment

1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically

### Other Platforms

The app can be deployed to any platform supporting Python/Django:
- Railway (recommended alternative)
- DigitalOcean App Platform
- AWS Elastic Beanstalk
- Google Cloud Run
- Azure App Service

## Twilio Setup

### 1. Account Setup
1. Create a Twilio account at [twilio.com](https://twilio.com)
2. Get your Account SID and Auth Token
3. Purchase a phone number

### 2. Webhook Configuration
Set your webhook URLs in the environment:
- Call Status: `https://your-domain.com/api/webhooks/call-status/`
- Record Response: `https://your-domain.com/api/webhooks/record-response/`

### 3. Phone Number Whitelist
Add test phone numbers to `WHITELISTED_NUMBERS` environment variable:
```env
WHITELISTED_NUMBERS=+1234567890,+1987654321
```

**Note**: For the live deployment, ensure your test phone numbers are whitelisted in the environment variables.

## Usage Workflow

### 1. Create Job Description
```bash
POST /api/jd-to-questions/
{
  "title": "Senior Software Engineer",
  "description": "We are looking for a Senior Software Engineer..."
}
```

### 2. Create Candidate
```bash
POST /api/candidates/
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "resume": [file upload]
}
```

### 3. Trigger Interview
```bash
POST /api/trigger-interview/
{
  "candidate_id": "uuid",
  "job_description_id": "uuid"
}
```

### 4. Monitor Status
```bash
GET /api/interviews/{interview_id}/
```

### 5. Get Results
```bash
GET /api/interviews/{interview_id}/results/
```

## File Structure

```
ai_screener/
├── ai_screener/          # Django project settings
├── interviews/           # Main app
│   ├── models.py        # Database models
│   ├── views.py         # API views
│   ├── serializers.py   # DRF serializers
│   ├── services.py      # External service integrations
│   └── urls.py          # URL patterns
├── manage.py            # Django management
├── requirements.txt     # Python dependencies
├── env.example          # Environment variables template
├── README.md           # This file
├── DESIGN_DOCUMENT.md  # System architecture and design
├── AI_Interview_Screener.postman_collection.json
└── AI_Interview_Screener.postman_environment.json
```

## Security Features

- **API Key Authentication**: All endpoints require valid API key
- **Phone Number Whitelist**: Only whitelisted numbers can receive calls
- **CSRF Protection**: Webhook endpoints are CSRF exempt
- **Environment Variables**: All sensitive data stored in environment

## Troubleshooting

### Common Issues

1. **Twilio Call Fails**
   - Check phone number is whitelisted
   - Verify Twilio credentials
   - Ensure webhook URLs are accessible

2. **OpenAI API Errors**
   - Verify OpenAI API key is valid
   - Check API quota and billing
   - Ensure proper JSON formatting

3. **File Upload Issues**
   - Check file size limits
   - Verify file format (PDF/DOCX only)
   - Ensure media directory is writable

### Logs
Check Django logs for detailed error information:
```bash
python manage.py runserver --verbosity=2
```

## Documentation

- **Design Document**: See `DESIGN_DOCUMENT.md` for comprehensive system architecture, data design, AI usage points, and system flow
- **API Documentation**: Use the provided Postman collection for detailed API examples
- **Deployment Guide**: Follow the Render.com deployment instructions above

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review Django and Twilio documentation
3. Create an issue in the repository

## License

This project is licensed under the MIT License.
