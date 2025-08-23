import os
import requests
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import PyPDF2
from docx import Document
import io
from django.conf import settings
from .models import Interview, InterviewResponse, InterviewResult
import json


from openai import OpenAI
import openai
# Set your OpenAI API key from environment variable

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
openai.api_key = os.getenv("OPENAI_API_KEY")



class OpenAIService:
    """Service for generating interview questions and analyzing responses using OpenAI v1.0+"""

    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Or gpt-4

    def _make_request(self, prompt, temperature=0.7, max_tokens=500):
        """Send prompt to OpenAI and return response text"""
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI request error: {e}")
            raise

    def generate_questions_from_jd(self, job_title, job_description):
        """Generate 5-7 interview questions from job description"""
        prompt = f"""
        Based on the following job description, generate 5-7 relevant interview questions.

        Job Title: {job_title}
        Job Description: {job_description}

        Generate questions that assess:
        1. Technical skills and experience
        2. Problem-solving abilities
        3. Communication skills
        4. Cultural fit
        5. Past achievements and challenges

        Return only the questions as a JSON array of strings, no additional text.
        """
        questions_text = self._make_request(prompt, temperature=0.7, max_tokens=500)
        try:
            questions = json.loads(questions_text)
        except json.JSONDecodeError:
            # fallback: split by lines
            questions = [q.strip().strip('"').strip("'") for q in questions_text.split("\n") if q.strip()]

        return questions[:7]

    def analyze_response(self, question, response_text, resume_context=""):
        """Analyze a candidate's response and provide score and feedback"""
        prompt = f"""
        Analyze this interview response and provide a score (0-10) and feedback.

        Question: {question}
        Response: {response_text}
        Resume Context: {resume_context}

        Evaluate based on:
        - Relevance to the question
        - Clarity and communication
        - Specificity and examples
        - Professionalism

        Return as JSON: {{"score": float, "feedback": "string"}}
        """
        try:
            result_text = self._make_request(prompt, temperature=0.3, max_tokens=300)
            try:
                result = json.loads(result_text)
                return result.get("score", 5.0), result.get("feedback", "No specific feedback available.")
            except json.JSONDecodeError:
                return 5.0, "Analysis completed but feedback format was unexpected."
        except Exception as e:
            print(f"Error analyzing response: {e}")
            return 5.0, "Unable to analyze response due to technical issues."

    def generate_final_recommendation(self, interview_responses, resume_context=""):
        """Generate final interview recommendation and overall score"""
        responses_summary = "\n".join([
            f"Q{i+1}: {resp.question}\nA{i+1}: {resp.transcript}\nScore: {resp.score}\n"
            for i, resp in enumerate(interview_responses)
        ])

        prompt = f"""
        Based on these interview responses, provide a comprehensive evaluation:

        Resume Context: {resume_context}

        Interview Responses:
        {responses_summary}

        Provide:
        1. Overall score (0-10)
        2. Recommendation (hire/consider/reject with reasoning)
        3. Key strengths (list)
        4. Areas for improvement (list)

        Return as JSON:
        {{
            "overall_score": float,
            "recommendation": "string",
            "strengths": ["string"],
            "areas_for_improvement": ["string"]
        }}
        """

        try:
            result_text = self._make_request(prompt, temperature=0.3, max_tokens=500)
            try:
                result = json.loads(result_text)
                return result
            except json.JSONDecodeError:
                return {
                    "overall_score": 5.0,
                    "recommendation": "Consider - Analysis completed but recommendation format was unexpected.",
                    "strengths": ["Analysis completed"],
                    "areas_for_improvement": ["Unable to provide specific feedback"]
                }

        except Exception as e:
            print(f"Error generating recommendation: {e}")
            return {
                "overall_score": 5.0,
                "recommendation": "Consider - Unable to generate recommendation due to technical issues.",
                "strengths": ["Interview completed"],
                "areas_for_improvement": ["Technical analysis unavailable"]
            }   


class TwilioService:
    """Service for Twilio voice call integration"""
    
    def __init__(self):
        self.client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
    
    def initiate_call(self, interview_id, candidate_phone, questions):
        """Initiate a voice call to the candidate"""
        try:
            # Validate phone number is whitelisted
            whitelisted_numbers = os.getenv('WHITELISTED_NUMBERS', '["*"]').split(',')
            if candidate_phone not in whitelisted_numbers:
                raise ValueError(f"Phone number {candidate_phone} is not whitelisted")
            
            # Create TwiML for the call
            twiml = self._create_interview_twiml(interview_id, questions)
            
            # Make the call
            call = self.client.calls.create(
                twiml=twiml,
                to=candidate_phone,
                from_=self.phone_number,
                record=True,
                status_callback=f"{os.getenv('WEBHOOK_BASE_URL', 'http://localhost:8000')}/api/webhooks/call-status/",
                status_callback_event=['completed']
            )
            
            return call.sid
            
        except Exception as e:
            print(f"Error initiating call: {e}")
            raise
    
    def _create_interview_twiml(self, interview_id, questions):
        """Create TwiML for the interview call"""
        response = VoiceResponse()
        
        # Introduction
        response.say("Hello! Thank you for joining this automated interview. I'll be asking you several questions. Please speak clearly and take your time to answer each question thoroughly.")
        response.pause(length=1)
        
        # Ask each question
        for i, question in enumerate(questions):
            response.say(f"Question {i+1}: {question}")
            response.pause(length=1)
            response.say("Please provide your answer now.")
            
            # Record the answer
            response.record(
                max_length=120,  # 2 minutes max per answer
                play_beep=True,
                action=f"{os.getenv('WEBHOOK_BASE_URL', 'http://localhost:8000')}/api/webhooks/record-response/?interview_id={interview_id}&question_number={i+1}",
                method='POST'
            )
            
            response.pause(length=1)
        
        # Conclusion
        response.say("Thank you for completing the interview. We will review your responses and get back to you soon. Goodbye!")
        response.hangup()
        
        return str(response)


class ResumeParserService:
    """Service for parsing resume files"""
    
    def parse_resume(self, file):
        """Parse PDF or DOCX resume and extract text"""
        try:
            if file.name.lower().endswith('.pdf'):
                return self._parse_pdf(file)
            elif file.name.lower().endswith('.docx'):
                return self._parse_docx(file)
            else:
                raise ValueError("Unsupported file format. Please upload PDF or DOCX.")
        except Exception as e:
            print(f"Error parsing resume: {e}")
            return "Unable to parse resume content."
    
    def _parse_pdf(self, file):
        """Parse PDF file"""
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error parsing PDF: {e}")
            return "Unable to extract text from PDF."
    
    def _parse_docx(self, file):
        """Parse DOCX file"""
        try:
            doc = Document(file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error parsing DOCX: {e}")
            return "Unable to extract text from DOCX."
