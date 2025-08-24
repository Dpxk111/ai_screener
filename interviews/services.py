import os
import logging
import requests
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import PyPDF2
from docx import Document
import io
from django.conf import settings
from .models import Interview, InterviewResponse, InterviewResult
import json
import base64

# Set up loggers for different services
logger = logging.getLogger('interviews')
openai_logger = logging.getLogger('openai')
twilio_logger = logging.getLogger('twilio')

# Add comprehensive logging configuration
print(f"[DEBUG] Services: Initializing loggers")
print(f"[DEBUG] Services: OpenAI API Key set: {'YES' if os.getenv('OPENAI_API_KEY') else 'NO'}")
print(f"[DEBUG] Services: Twilio Account SID set: {'YES' if os.getenv('TWILIO_ACCOUNT_SID') else 'NO'}")
print(f"[DEBUG] Services: Twilio Auth Token set: {'YES' if os.getenv('TWILIO_AUTH_TOKEN') else 'NO'}")
print(f"[DEBUG] Services: Twilio Phone Number set: {'YES' if os.getenv('TWILIO_PHONE_NUMBER') else 'NO'}")
print(f"[DEBUG] Services: Webhook Base URL set: {'YES' if os.getenv('WEBHOOK_BASE_URL') else 'NO'}")

logger.info("Services: All service modules initialized")
openai_logger.info("OpenAI: OpenAI service logger initialized")
twilio_logger.info("Twilio: Twilio service logger initialized")

from openai import OpenAI
import openai
# Set your OpenAI API key from environment variable

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
openai.api_key = os.getenv("OPENAI_API_KEY")



class OpenAIService:
    """Service for generating interview questions and analyzing responses using OpenAI v1.0+"""

    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Or gpt-4
        print(f"[DEBUG] OpenAIService: Initialized with model: {self.model}")
        openai_logger.info(f"OpenAIService: Initialized with model {self.model}")
        print(f"[DEBUG] OpenAIService: OpenAI client initialized: {'YES' if client else 'NO'}")
        print(f"[DEBUG] OpenAIService: OpenAI API key configured: {'YES' if os.getenv('OPENAI_API_KEY') else 'NO'}")

    def _make_request(self, prompt, temperature=0.7, max_tokens=500, max_retries=3):
        """Send prompt to OpenAI and return response text with retry logic"""
        import time
        
        print(f"[DEBUG] OpenAIService: Starting OpenAI request (attempt 1/{max_retries})")
        print(f"[DEBUG] OpenAIService: Model: {self.model}")
        print(f"[DEBUG] OpenAIService: Temperature: {temperature}")
        print(f"[DEBUG] OpenAIService: Max tokens: {max_tokens}")
        print(f"[DEBUG] OpenAIService: Prompt length: {len(prompt)} characters")
        print(f"[DEBUG] OpenAIService: Prompt preview: {prompt[:100]}...")
        
        for attempt in range(max_retries):
            try:
                print(f"[DEBUG] OpenAIService: Making request to OpenAI (attempt {attempt + 1}/{max_retries})")
                openai_logger.info(f"OpenAIService: Making request to OpenAI with model {self.model} (attempt {attempt + 1}/{max_retries})")
                
                start_time = time.time()
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
                end_time = time.time()
                
                result = response.choices[0].message.content.strip()
                print(f"[DEBUG] OpenAIService: Request completed in {end_time - start_time:.2f} seconds")
                print(f"[DEBUG] OpenAIService: Response length: {len(result)} characters")
                print(f"[DEBUG] OpenAIService: Response preview: {result[:100]}...")
                print(f"[DEBUG] OpenAIService: Usage - Prompt tokens: {response.usage.prompt_tokens if response.usage else 'N/A'}")
                print(f"[DEBUG] OpenAIService: Usage - Completion tokens: {response.usage.completion_tokens if response.usage else 'N/A'}")
                print(f"[DEBUG] OpenAIService: Usage - Total tokens: {response.usage.total_tokens if response.usage else 'N/A'}")
                
                openai_logger.info(f"OpenAIService: Successfully received response from OpenAI")
                return result
        except Exception as e:
                error_msg = str(e)
                openai_logger.warning(f"OpenAIService: OpenAI request error (attempt {attempt + 1}/{max_retries}): {error_msg}")
                
                # Check if it's a retryable error
                if "503" in error_msg or "429" in error_msg or "timeout" in error_msg.lower():
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                        openai_logger.info(f"OpenAIService: Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                
                # If it's the last attempt or non-retryable error, log and raise
                openai_logger.error(f"OpenAIService: Final OpenAI request error after {max_retries} attempts: {error_msg}", exc_info=True)
            raise
    def clean_questions(self, raw_questions):
        """Cleans a list of questions returned by AI"""
        print(f"[DEBUG] OpenAIService: Cleaning {len(raw_questions)} raw questions")
        print(f"[DEBUG] OpenAIService: Raw questions: {raw_questions}")
        
        cleaned = []
        for i, q in enumerate(raw_questions):
            print(f"[DEBUG] OpenAIService: Processing question {i+1}: '{q}'")
            # Skip any line that's not a real question
            if not q or q.lower() == 'json':
                print(f"[DEBUG] OpenAIService: Skipping question {i+1} (empty or 'json')")
                continue
            # Remove leading/trailing whitespace and quotes
            original_q = q
            q = q.strip().strip('"').strip("'").strip()
            print(f"[DEBUG] OpenAIService: Cleaned question {i+1}: '{original_q}' -> '{q}'")
            if q:
                cleaned.append(q)
                print(f"[DEBUG] OpenAIService: Added question {i+1} to cleaned list")
            else:
                print(f"[DEBUG] OpenAIService: Question {i+1} became empty after cleaning, skipping")
        
        print(f"[DEBUG] OpenAIService: Final cleaned questions: {cleaned}")
        print(f"[DEBUG] OpenAIService: Cleaned {len(raw_questions)} questions to {len(cleaned)} questions")
        return cleaned

    def generate_questions_from_jd(self, job_title, job_description):
        """Generate 5-7 interview questions from job description"""
        print(f"[DEBUG] OpenAIService: Starting question generation for job title: {job_title}")
        print(f"[DEBUG] OpenAIService: Job description length: {len(job_description)} characters")
        print(f"[DEBUG] OpenAIService: Job description preview: {job_description[:200]}...")
        
        openai_logger.info(f"OpenAIService: Generating questions for job title: {job_title}")
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
        
        print(f"[DEBUG] OpenAIService: Generated prompt length: {len(prompt)} characters")
        
        try:
            print(f"[DEBUG] OpenAIService: Calling OpenAI for question generation...")
            questions_text = self._make_request(prompt, temperature=0.7, max_tokens=500)
            print(f"[DEBUG] OpenAIService: Raw OpenAI response: {questions_text}")
            
            questions_text = questions_text.strip().strip("```").strip()
            print(f"[DEBUG] OpenAIService: Cleaned response: {questions_text}")

            try:
                print(f"[DEBUG] OpenAIService: Attempting to parse JSON...")
            questions = json.loads(questions_text)
                print(f"[DEBUG] OpenAIService: Successfully parsed JSON: {questions}")
                openai_logger.info(f"OpenAIService: Successfully parsed JSON questions for {job_title}")
            except json.JSONDecodeError as e:
                print(f"[WARNING] OpenAIService: JSON decode failed: {str(e)}")
                print(f"[DEBUG] OpenAIService: Falling back to line parsing...")
                openai_logger.warning(f"OpenAIService: JSON decode failed for {job_title}, falling back to line parsing")
            lines = questions_text.split("\n")
            questions = []
                for i, line in enumerate(lines):
                    print(f"[DEBUG] OpenAIService: Processing line {i+1}: '{line}'")
                line = line.strip().strip('"').strip("'")
                if line and line not in ["[", "]"]:
                    if line.endswith(","):
                        line = line[:-1].strip()
                    questions.append(line)
                        print(f"[DEBUG] OpenAIService: Added line {i+1} as question: '{line}'")
                
                print(f"[DEBUG] OpenAIService: Line parsing result: {questions}")
            
            print(f"[DEBUG] OpenAIService: Questions before cleaning: {questions}")
            res = self.clean_questions(questions[:1])
            print(f"[DEBUG] OpenAIService: Final questions after cleaning: {res}")
            openai_logger.info(f"OpenAIService: Generated {len(res)} questions for {job_title}")
        return res
        except Exception as e:
            openai_logger.error(f"OpenAIService: Error generating questions for {job_title}: {str(e)}", exc_info=True)
            # Fallback to default questions if OpenAI fails
            openai_logger.warning(f"OpenAIService: Using fallback questions for {job_title}")
            fallback_questions = [
                "Can you tell me about your relevant experience for this role?",
                "What are your key strengths that would make you successful in this position?",
                "Describe a challenging project you worked on and how you handled it.",
                "What interests you most about this opportunity?",
                "Where do you see yourself professionally in the next few years?"
            ]
            return self.clean_questions(fallback_questions[:1])


    def analyze_response(self, question, response_text, resume_context=""):
        """Analyze a candidate's response and provide score and feedback"""
        print(f"[DEBUG] OpenAIService: Starting response analysis")
        print(f"[DEBUG] OpenAIService: Question: {question}")
        print(f"[DEBUG] OpenAIService: Response text length: {len(response_text)} characters")
        print(f"[DEBUG] OpenAIService: Response preview: {response_text[:100]}...")
        print(f"[DEBUG] OpenAIService: Resume context length: {len(resume_context)} characters")
        
        openai_logger.info(f"OpenAIService: Analyzing response for question: {question[:50]}...")
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
        
        print(f"[DEBUG] OpenAIService: Analysis prompt length: {len(prompt)} characters")
        
        try:
            print(f"[DEBUG] OpenAIService: Calling OpenAI for response analysis...")
            result_text = self._make_request(prompt, temperature=0.3, max_tokens=300)
            print(f"[DEBUG] OpenAIService: Raw analysis response: {result_text}")
            
            try:
                print(f"[DEBUG] OpenAIService: Attempting to parse analysis JSON...")
                result = json.loads(result_text)
                print(f"[DEBUG] OpenAIService: Parsed analysis result: {result}")
                score = result.get("score", 5.0)
                feedback = result.get("feedback", "No specific feedback available.")
                print(f"[DEBUG] OpenAIService: Extracted score: {score}")
                print(f"[DEBUG] OpenAIService: Extracted feedback: {feedback}")
                openai_logger.info(f"OpenAIService: Successfully analyzed response with score: {score}")
                return score, feedback
            except json.JSONDecodeError as e:
                print(f"[WARNING] OpenAIService: JSON decode failed for analysis: {str(e)}")
                print(f"[DEBUG] OpenAIService: Using default values for analysis")
                openai_logger.warning(f"OpenAIService: JSON decode failed for response analysis, using default values")
                return 5.0, "Analysis completed but feedback format was unexpected."
        except Exception as e:
            print(f"[ERROR] OpenAIService: Error in response analysis: {str(e)}")
            openai_logger.error(f"OpenAIService: Error analyzing response: {str(e)}", exc_info=True)
            return 5.0, "Unable to analyze response due to technical issues."

    def generate_final_recommendation(self, interview_responses, resume_context=""):
        """Generate final interview recommendation and overall score"""
        print(f"[DEBUG] OpenAIService: Starting final recommendation generation")
        print(f"[DEBUG] OpenAIService: Number of responses: {len(interview_responses)}")
        print(f"[DEBUG] OpenAIService: Resume context length: {len(resume_context)} characters")
        
        openai_logger.info(f"OpenAIService: Generating final recommendation for {len(interview_responses)} responses")
        
        # Log each response for debugging
        for i, resp in enumerate(interview_responses):
            print(f"[DEBUG] OpenAIService: Response {i+1}:")
            print(f"[DEBUG] OpenAIService:   Question: {resp.question}")
            print(f"[DEBUG] OpenAIService:   Transcript length: {len(resp.transcript)} characters")
            print(f"[DEBUG] OpenAIService:   Score: {resp.score}")
        
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

        print(f"[DEBUG] OpenAIService: Final recommendation prompt length: {len(prompt)} characters")
        print(f"[DEBUG] OpenAIService: Responses summary length: {len(responses_summary)} characters")

        try:
            print(f"[DEBUG] OpenAIService: Calling OpenAI for final recommendation...")
            result_text = self._make_request(prompt, temperature=0.3, max_tokens=500)
            print(f"[DEBUG] OpenAIService: Raw final recommendation response: {result_text}")
            
            try:
                print(f"[DEBUG] OpenAIService: Attempting to parse final recommendation JSON...")
                result = json.loads(result_text)
                print(f"[DEBUG] OpenAIService: Parsed final recommendation: {result}")
                
                overall_score = result.get('overall_score', 5.0)
                recommendation = result.get('recommendation', 'No recommendation')
                strengths = result.get('strengths', [])
                areas_for_improvement = result.get('areas_for_improvement', [])
                
                print(f"[DEBUG] OpenAIService: Final recommendation details:")
                print(f"[DEBUG] OpenAIService:   Overall score: {overall_score}")
                print(f"[DEBUG] OpenAIService:   Recommendation: {recommendation}")
                print(f"[DEBUG] OpenAIService:   Strengths: {strengths}")
                print(f"[DEBUG] OpenAIService:   Areas for improvement: {areas_for_improvement}")
                
                openai_logger.info(f"OpenAIService: Successfully generated final recommendation with score: {overall_score}")
                return result
            except json.JSONDecodeError as e:
                print(f"[WARNING] OpenAIService: JSON decode failed for final recommendation: {str(e)}")
                print(f"[DEBUG] OpenAIService: Using default values for final recommendation")
                openai_logger.warning(f"OpenAIService: JSON decode failed for final recommendation, using default values")
                return {
                    "overall_score": 5.0,
                    "recommendation": "Consider - Analysis completed but recommendation format was unexpected.",
                    "strengths": ["Analysis completed"],
                    "areas_for_improvement": ["Unable to provide specific feedback"]
                }

        except Exception as e:
            print(f"[ERROR] OpenAIService: Error in final recommendation generation: {str(e)}")
            openai_logger.error(f"OpenAIService: Error generating final recommendation: {str(e)}", exc_info=True)
            return {
                "overall_score": 5.0,
                "recommendation": "Consider - Unable to generate recommendation due to technical issues.",
                "strengths": ["Interview completed"],
                "areas_for_improvement": ["Technical analysis unavailable"]
            }   


class TwilioService:
    """Service for Twilio voice call integration"""
    
    def __init__(self):
        print(f"[DEBUG] TwilioService: Initializing with Account SID: {os.getenv('TWILIO_ACCOUNT_SID', 'NOT_SET')[:10]}...")
        print(f"[DEBUG] TwilioService: Phone number: {os.getenv('TWILIO_PHONE_NUMBER', 'NOT_SET')}")
        print(f"[DEBUG] TwilioService: Auth token: {'SET' if os.getenv('TWILIO_AUTH_TOKEN') else 'NOT_SET'}")
        
        self.client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        # Validate configuration
        if not os.getenv('TWILIO_ACCOUNT_SID'):
            print("[ERROR] TwilioService: TWILIO_ACCOUNT_SID not set")
        if not os.getenv('TWILIO_AUTH_TOKEN'):
            print("[ERROR] TwilioService: TWILIO_AUTH_TOKEN not set")
        if not self.phone_number:
            print("[ERROR] TwilioService: TWILIO_PHONE_NUMBER not set")
    
    def initiate_call(self, interview_id, candidate_phone, questions):
        """Initiate a voice call to the candidate"""
        try:
            print(f"[DEBUG] TwilioService: Starting call initiation for interview {interview_id}")
            print(f"[DEBUG] TwilioService: Candidate phone: {candidate_phone}")
            print(f"[DEBUG] TwilioService: Number of questions: {len(questions)}")
            
            twilio_logger.info(f"TwilioService: Initiating call for interview {interview_id} to {candidate_phone}")
            
            # Validate inputs
            if not interview_id:
                print("[ERROR] TwilioService: interview_id is empty")
                raise ValueError("interview_id cannot be empty")
            if not candidate_phone:
                print("[ERROR] TwilioService: candidate_phone is empty")
                raise ValueError("candidate_phone cannot be empty")
            if not questions or len(questions) == 0:
                print("[ERROR] TwilioService: questions list is empty")
                raise ValueError("questions list cannot be empty")
            
            # Parse whitelist from env
            whitelist_env = os.getenv('WHITELISTED_NUMBERS', '["*"]')
            print(f"[DEBUG] TwilioService: Whitelist env: {whitelist_env}")
            try:
                whitelisted_numbers = json.loads(whitelist_env)
                print(f"[DEBUG] TwilioService: Parsed whitelist: {whitelisted_numbers}")
                twilio_logger.info(f"TwilioService: Loaded whitelist with {len(whitelisted_numbers)} numbers")
            except json.JSONDecodeError as e:
                print(f"[WARNING] TwilioService: Failed to parse whitelist: {e}")
                twilio_logger.warning(f"TwilioService: Failed to parse whitelist, using default")
                whitelisted_numbers = ["*"]

            # Check if number is allowed
            if '*' not in whitelisted_numbers and candidate_phone not in whitelisted_numbers:
                print(f"[ERROR] TwilioService: Phone number {candidate_phone} is not whitelisted")
                twilio_logger.error(f"TwilioService: Phone number {candidate_phone} is not whitelisted")
                raise ValueError(f"Phone number {candidate_phone} is not whitelisted")

            print(f"[DEBUG] TwilioService: Generating TwiML for interview {interview_id}")
            twiml = self._create_interview_twiml(interview_id, question_number=1, questions=questions)
            print(f"[DEBUG] TwilioService: Generated TwiML length: {len(twiml)}")
            print(f"[DEBUG] TwilioService: TwiML preview: {twiml[:200]}...")
            twilio_logger.info(f"TwilioService: Generated TwiML for interview {interview_id}")

            # Get webhook URL - IMPORTANT: For local development, you need a public URL
            webhook_base_url = os.getenv('WEBHOOK_BASE_URL')
            if not webhook_base_url:
                print("[WARNING] TwilioService: WEBHOOK_BASE_URL not set, using localhost (this won't work for Twilio)")
                webhook_base_url = 'http://localhost:8000'
            
            # Ensure the URL ends with a slash if needed
            if not webhook_base_url.endswith('/'):
                webhook_base_url += '/'
            
            status_callback_url = f"{webhook_base_url}api/webhooks/call-status/"
            print(f"[DEBUG] TwilioService: Webhook base URL: {webhook_base_url}")
            print(f"[DEBUG] TwilioService: Status callback URL: {status_callback_url}")
            
            # Check if webhook URL is accessible (for debugging)
            if webhook_base_url.startswith('http://localhost'):
                print("[WARNING] TwilioService: Using localhost URL - Twilio cannot reach this!")
                print("[WARNING] TwilioService: You need to use ngrok or similar to expose localhost")

            # Make the call
            print(f"[DEBUG] TwilioService: Creating call with Twilio API...")
            call_params = {
                'twiml': twiml,
                'to': candidate_phone,
                'from_': self.phone_number,
                'record': True,
                'status_callback': status_callback_url,
                'status_callback_event': ['completed']
            }
            print(f"[DEBUG] TwilioService: Call parameters: {call_params}")
            
            call = self.client.calls.create(**call_params)

            print(f"[DEBUG] TwilioService: Call created successfully with SID: {call.sid}")
            twilio_logger.info(f"TwilioService: Successfully initiated call with SID: {call.sid}")
            return call.sid

        except Exception as e:
            print(f"[ERROR] TwilioService: Error initiating call: {str(e)}")
            print(f"[ERROR] TwilioService: Exception type: {type(e).__name__}")
            import traceback
            print(f"[ERROR] TwilioService: Traceback: {traceback.format_exc()}")
            twilio_logger.error(f"TwilioService: Error initiating call: {str(e)}", exc_info=True)
            raise
        
    def _create_interview_twiml(self, interview_id, question_number, questions):
        print(f"[DEBUG] TwilioService: Creating TwiML for interview {interview_id}, question {question_number}")
        print(f"[DEBUG] TwilioService: Total questions: {len(questions)}")
        
        try:
        response = VoiceResponse()

            # Only ask the first question (question_number should always be 1)
            if question_number == 1 and len(questions) > 0:
                question = questions[0]  # Always use the first question
                print(f"[DEBUG] TwilioService: Question text: {question}")
                
                # Add welcome message
                response.say("Hello! Welcome to your automated interview. Let's begin.")
                response.pause(length=1)
                
                response.say(f"Question: {question}")
            response.pause(length=1)
            response.say("Please provide your answer now.")
                
                # Get webhook URL for recording
                webhook_base_url = os.getenv('WEBHOOK_BASE_URL', 'http://localhost:8000')
                # Ensure the URL ends with a slash if needed
                if not webhook_base_url.endswith('/'):
                    webhook_base_url += '/'
                record_action_url = f"{webhook_base_url}api/webhooks/record-response/?interview_id={interview_id}&question_number=1"
                print(f"[DEBUG] TwilioService: Record action URL: {record_action_url}")
                
            response.record(
                max_length=120,
                play_beep=True,
                    action=record_action_url,
                    method='POST',
                    timeout=10,
                    transcribe=False
            )
        else:
                print(f"[DEBUG] TwilioService: No question available or not first question, ending call")
                response.say("Thank you for completing the interview. We will review your response and get back to you soon. Goodbye!")
            response.hangup()

            twiml_str = str(response)
            print(f"[DEBUG] TwilioService: Generated TwiML: {twiml_str}")
            return twiml_str
            
        except Exception as e:
            print(f"[ERROR] TwilioService: Error creating TwiML: {str(e)}")
            import traceback
            print(f"[ERROR] TwilioService: TwiML creation traceback: {traceback.format_exc()}")
            
            # Fallback TwiML
            fallback_response = VoiceResponse()
            fallback_response.say("We're experiencing technical difficulties. Please try again later.")
            fallback_response.hangup()
            return str(fallback_response)


class ResumeParserService:
    """Service for parsing resume files"""
    
    def __init__(self):
        print(f"[DEBUG] ResumeParserService: Initialized")
        logger.info("ResumeParserService: Initialized")
    
    def parse_resume(self, file):
        """Parse PDF or DOCX resume and extract text"""
        print(f"[DEBUG] ResumeParserService: Starting resume parsing")
        print(f"[DEBUG] ResumeParserService: File name: {file.name}")
        print(f"[DEBUG] ResumeParserService: File size: {file.size if hasattr(file, 'size') else 'Unknown'} bytes")
        print(f"[DEBUG] ResumeParserService: File content type: {getattr(file, 'content_type', 'Unknown')}")
        
        try:
            logger.info(f"ResumeParserService: Parsing resume file: {file.name}")
            
            if file.name.lower().endswith('.pdf'):
                print(f"[DEBUG] ResumeParserService: Detected PDF file, using PDF parser")
                result = self._parse_pdf(file)
                print(f"[DEBUG] ResumeParserService: PDF parsing completed, extracted {len(result)} characters")
                logger.info(f"ResumeParserService: Successfully parsed PDF resume, extracted {len(result)} characters")
                return result
            elif file.name.lower().endswith('.docx'):
                print(f"[DEBUG] ResumeParserService: Detected DOCX file, using DOCX parser")
                result = self._parse_docx(file)
                print(f"[DEBUG] ResumeParserService: DOCX parsing completed, extracted {len(result)} characters")
                logger.info(f"ResumeParserService: Successfully parsed DOCX resume, extracted {len(result)} characters")
                return result
            else:
                print(f"[ERROR] ResumeParserService: Unsupported file format: {file.name}")
                logger.error(f"ResumeParserService: Unsupported file format: {file.name}")
                raise ValueError("Unsupported file format. Please upload PDF or DOCX.")
        except Exception as e:
            print(f"[ERROR] ResumeParserService: Error parsing resume {file.name}: {str(e)}")
            logger.error(f"ResumeParserService: Error parsing resume {file.name}: {str(e)}", exc_info=True)
            return "Unable to parse resume content."
    
    def _parse_pdf(self, file):
        """Parse PDF file"""
        try:
            print(f"[DEBUG] ResumeParserService: Starting PDF parsing for {file.name}")
            logger.info(f"ResumeParserService: Starting PDF parsing for {file.name}")
            
            pdf_reader = PyPDF2.PdfReader(file)
            print(f"[DEBUG] ResumeParserService: PDF reader created, number of pages: {len(pdf_reader.pages)}")
            
            text = ""
            for i, page in enumerate(pdf_reader.pages):
                print(f"[DEBUG] ResumeParserService: Processing page {i+1}/{len(pdf_reader.pages)}")
                page_text = page.extract_text()
                print(f"[DEBUG] ResumeParserService: Page {i+1} extracted {len(page_text)} characters")
                text += page_text + "\n"
            
            result = text.strip()
            print(f"[DEBUG] ResumeParserService: PDF parsing completed")
            print(f"[DEBUG] ResumeParserService: Total extracted text length: {len(result)} characters")
            print(f"[DEBUG] ResumeParserService: Text preview: {result[:200]}...")
            
            logger.info(f"ResumeParserService: Successfully parsed PDF with {len(pdf_reader.pages)} pages")
            return result
        except Exception as e:
            print(f"[ERROR] ResumeParserService: Error parsing PDF {file.name}: {str(e)}")
            logger.error(f"ResumeParserService: Error parsing PDF {file.name}: {str(e)}", exc_info=True)
            return "Unable to extract text from PDF."
    
    def _parse_docx(self, file):
        """Parse DOCX file"""
        try:
            print(f"[DEBUG] ResumeParserService: Starting DOCX parsing for {file.name}")
            logger.info(f"ResumeParserService: Starting DOCX parsing for {file.name}")
            
            doc = Document(file)
            print(f"[DEBUG] ResumeParserService: DOCX document loaded, number of paragraphs: {len(doc.paragraphs)}")
            
            text = ""
            for i, paragraph in enumerate(doc.paragraphs):
                if i < 10:  # Log first 10 paragraphs for debugging
                    print(f"[DEBUG] ResumeParserService: Paragraph {i+1}: {len(paragraph.text)} characters")
                text += paragraph.text + "\n"
            
            result = text.strip()
            print(f"[DEBUG] ResumeParserService: DOCX parsing completed")
            print(f"[DEBUG] ResumeParserService: Total extracted text length: {len(result)} characters")
            print(f"[DEBUG] ResumeParserService: Text preview: {result[:200]}...")
            
            logger.info(f"ResumeParserService: Successfully parsed DOCX with {len(doc.paragraphs)} paragraphs")
            return result
        except Exception as e:
            print(f"[ERROR] ResumeParserService: Error parsing DOCX {file.name}: {str(e)}")
            logger.error(f"ResumeParserService: Error parsing DOCX {file.name}: {str(e)}", exc_info=True)
            return "Unable to extract text from DOCX."


class TranscriptionService:
    """Service for transcribing audio recordings"""
    
    def __init__(self):
        print(f"[DEBUG] TranscriptionService: Initializing")
        print(f"[DEBUG] TranscriptionService: OpenAI API Key set: {'YES' if os.getenv('OPENAI_API_KEY') else 'NO'}")
        print(f"[DEBUG] TranscriptionService: Twilio Account SID set: {'YES' if os.getenv('TWILIO_ACCOUNT_SID') else 'NO'}")
        print(f"[DEBUG] TranscriptionService: Twilio Auth Token set: {'YES' if os.getenv('TWILIO_AUTH_TOKEN') else 'NO'}")
        
        try:
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            print(f"[DEBUG] TranscriptionService: OpenAI client initialized successfully")
        except Exception as e:
            print(f"[ERROR] TranscriptionService: Failed to initialize OpenAI client: {str(e)}")
            raise
        
        try:
        self.twilio_client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
            print(f"[DEBUG] TranscriptionService: Twilio client initialized successfully")
        except Exception as e:
            print(f"[ERROR] TranscriptionService: Failed to initialize Twilio client: {str(e)}")
            raise
        
        print(f"[DEBUG] TranscriptionService: Initialization completed successfully")
        logger.info("TranscriptionService: Initialized successfully")
    
    def transcribe_audio(self, audio_url):
        """Transcribe audio from URL using OpenAI Whisper"""
        try:
            logger.info(f"TranscriptionService: Starting transcription for URL: {audio_url}")
            print(f"[DEBUG] TranscriptionService: Starting transcription for URL: {audio_url}")
            
            # Extract recording SID from URL
            recording_sid = self._extract_recording_sid(audio_url)
            if not recording_sid:
                raise Exception("Could not extract recording SID from URL")
            
            print(f"[DEBUG] TranscriptionService: Extracted recording SID: {recording_sid}")
            
            # Get recording using Twilio client
            try:
                print(f"[DEBUG] TranscriptionService: Fetching recording from Twilio API...")
                recording = self.twilio_client.recordings(recording_sid).fetch()
                print(f"[DEBUG] TranscriptionService: Recording fetched successfully")
                print(f"[DEBUG] TranscriptionService: Recording SID: {recording.sid}")
                print(f"[DEBUG] TranscriptionService: Recording URI: {getattr(recording, 'uri', 'N/A')}")
                print(f"[DEBUG] TranscriptionService: Recording Media Location: {getattr(recording, 'media_location', 'N/A')}")
                print(f"[DEBUG] TranscriptionService: Recording Status: {getattr(recording, 'status', 'N/A')}")
                print(f"[DEBUG] TranscriptionService: Recording Duration: {getattr(recording, 'duration', 'N/A')}")
                logger.info(f"TranscriptionService: Recording fetched: {recording.sid}")
                
                # Check if recording is ready
                recording_status = getattr(recording, 'status', '')
                if recording_status != 'completed':
                    print(f"[WARNING] TranscriptionService: Recording status is '{recording_status}', not 'completed'")
                    print(f"[DEBUG] TranscriptionService: Waiting for recording to be completed...")
                    
                    # Wait for recording to be completed (max 30 seconds)
                    max_wait = 30
                    wait_interval = 5
                    waited = 0
                    
                    while recording_status != 'completed' and waited < max_wait:
                        import time
                        time.sleep(wait_interval)
                        waited += wait_interval
                        
                        try:
                    recording = self.twilio_client.recordings(recording_sid).fetch()
                            recording_status = getattr(recording, 'status', '')
                            print(f"[DEBUG] TranscriptionService: Recording status after {waited}s: {recording_status}")
                        except Exception as e:
                            print(f"[WARNING] TranscriptionService: Error checking recording status: {str(e)}")
                    
                    if recording_status != 'completed':
                        raise Exception(f"Recording not completed after {max_wait} seconds (status: {recording_status})")
                    else:
                        print(f"[DEBUG] TranscriptionService: Recording is now completed")
                
            except Exception as e:
                print(f"[ERROR] TranscriptionService: Failed to fetch recording: {str(e)}")
                logger.error(f"TranscriptionService: Failed to fetch recording {recording_sid}: {str(e)}", exc_info=True)
                raise Exception(f"Failed to fetch recording: {str(e)}")
            
            # Get the media URL
            media_url = None
            if hasattr(recording, 'uri') and recording.uri:
                # remove ".json" if it exists
                uri = recording.uri.replace('.json', '')
                media_url = f"https://api.twilio.com{uri}.mp3"
                print(f"[DEBUG] TranscriptionService: Using URI-based media URL: {media_url}")
            elif hasattr(recording, 'media_location') and recording.media_location:
                media_url = recording.media_location
                print(f"[DEBUG] TranscriptionService: Using media_location-based URL: {media_url}")

            if not media_url:
                print(f"[ERROR] TranscriptionService: No media URL found for recording")
                print(f"[DEBUG] TranscriptionService: Recording attributes: {dir(recording)}")
                raise Exception("No media URL found for recording")
            
            print(f"[DEBUG] TranscriptionService: Final media URL: {media_url}")
            
            # Test URL accessibility before downloading
            try:
                print(f"[DEBUG] TranscriptionService: Testing media URL accessibility...")
                test_response = requests.head(
                    media_url,
                    auth=(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN')),
                    timeout=10
                )
                print(f"[DEBUG] TranscriptionService: Media URL test response: {test_response.status_code}")
                if test_response.status_code != 200:
                    print(f"[WARNING] TranscriptionService: Media URL not accessible: {test_response.status_code}")
                    logger.warning(f"TranscriptionService: Media URL not accessible: {test_response.status_code}")
            except Exception as e:
                print(f"[WARNING] TranscriptionService: Could not test media URL: {str(e)}")
                logger.warning(f"TranscriptionService: Could not test media URL: {str(e)}")
            
            # Download audio file with retry logic for 404 errors
            max_retries = 3
            retry_delay = 5  # seconds
            
            for attempt in range(max_retries):
                try:
                    print(f"[DEBUG] TranscriptionService: Starting audio download (attempt {attempt + 1}/{max_retries})...")
                            response = requests.get(
                                media_url,
                                auth=(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN')),
                        timeout=60
                            )
                    
                    print(f"[DEBUG] TranscriptionService: Download response status: {response.status_code}")
                    print(f"[DEBUG] TranscriptionService: Download response headers: {dict(response.headers)}")
                    
                            if response.status_code == 200:
                                audio_data = response.content
                        print(f"[DEBUG] TranscriptionService: Downloaded audio successfully")
                        print(f"[DEBUG] TranscriptionService: Audio size: {len(audio_data)} bytes")
                        print(f"[DEBUG] TranscriptionService: Audio content type: {response.headers.get('content-type', 'unknown')}")
                        logger.info(f"TranscriptionService: Downloaded audio, size: {len(audio_data)} bytes")
                                break
                    elif response.status_code == 404:
                        print(f"[WARNING] TranscriptionService: Audio file not found (404) on attempt {attempt + 1}")
                        if attempt < max_retries - 1:
                            print(f"[DEBUG] TranscriptionService: Waiting {retry_delay} seconds before retry...")
                            import time
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                        else:
                            print(f"[ERROR] TranscriptionService: Audio file still not available after {max_retries} attempts")
                            raise Exception(f"Audio file not available after {max_retries} attempts (HTTP 404)")
                            else:
                        print(f"[ERROR] TranscriptionService: Download failed with status {response.status_code}")
                        print(f"[ERROR] TranscriptionService: Response content: {response.text[:500]}")
                        raise Exception(f"Failed to download audio: HTTP {response.status_code}")
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"[WARNING] TranscriptionService: Download attempt {attempt + 1} failed: {str(e)}")
                        print(f"[DEBUG] TranscriptionService: Waiting {retry_delay} seconds before retry...")
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                    else:
                        print(f"[ERROR] TranscriptionService: All download attempts failed")
                        logger.error(f"TranscriptionService: Failed to download audio from {media_url} after {max_retries} attempts: {str(e)}", exc_info=True)
                        raise Exception(f"Failed to download audio after {max_retries} attempts: {str(e)}")
            
            # Transcribe using OpenAI Whisper
            try:
                print(f"[DEBUG] TranscriptionService: Starting OpenAI transcription...")
                        transcript = self.openai_client.audio.transcriptions.create(
                            model="whisper-1",
                    file=("audio.mp3", audio_data, "audio/mpeg"),
                            response_format="text"
                        )
                        
                        result = transcript.strip()
                print(f"[DEBUG] TranscriptionService: Transcription successful: {result[:100]}...")
                logger.info(f"TranscriptionService: Transcription successful: {result[:100]}...")
                        return result
                        
                    except Exception as e:
                print(f"[ERROR] TranscriptionService: OpenAI transcription failed: {str(e)}")
                logger.error(f"TranscriptionService: OpenAI transcription failed: {str(e)}", exc_info=True)
                raise Exception(f"OpenAI transcription failed: {str(e)}")
                
        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            print(f"[ERROR] TranscriptionService: {error_msg}")
            logger.error(f"TranscriptionService: {error_msg}", exc_info=True)
            return error_msg
    
    def _extract_recording_sid(self, audio_url):
        """Extract recording SID from various URL formats"""
        print(f"[DEBUG] TranscriptionService: Extracting recording SID from URL: {audio_url}")
        
        try:
            # Handle different URL formats
            if '/Recordings/' in audio_url:
                # Format: https://api.twilio.com/2010-04-01/Accounts/ACxxx/Recordings/RExxx
                print(f"[DEBUG] TranscriptionService: Using /Recordings/ format")
                recording_sid = audio_url.split('/Recordings/')[-1].split('?')[0]
                print(f"[DEBUG] TranscriptionService: Extracted SID: {recording_sid}")
            elif '/recordings/' in audio_url:
                # Format: https://api.twilio.com/2010-04-01/Accounts/ACxxx/recordings/RExxx
                print(f"[DEBUG] TranscriptionService: Using /recordings/ format")
                recording_sid = audio_url.split('/recordings/')[-1].split('?')[0]
                print(f"[DEBUG] TranscriptionService: Extracted SID: {recording_sid}")
            else:
                # Try to extract from the end of the URL
                print(f"[DEBUG] TranscriptionService: Using fallback extraction method")
                parts = audio_url.split('/')
                print(f"[DEBUG] TranscriptionService: URL parts: {parts}")
                
                for i, part in enumerate(reversed(parts)):
                    print(f"[DEBUG] TranscriptionService: Checking part {len(parts)-i}: '{part}'")
                    if part.startswith('RE') and len(part) > 10:
                        recording_sid = part.split('?')[0]
                        print(f"[DEBUG] TranscriptionService: Found potential SID: {recording_sid}")
                        break
                else:
                    print(f"[WARNING] TranscriptionService: No recording SID found in URL")
                    return None
            
            # Validate SID format (should start with RE and be 34 characters)
            print(f"[DEBUG] TranscriptionService: Validating SID format: {recording_sid}")
            print(f"[DEBUG] TranscriptionService: SID starts with RE: {recording_sid.startswith('RE')}")
            print(f"[DEBUG] TranscriptionService: SID length: {len(recording_sid)} (expected 34)")
            
            if recording_sid.startswith('RE') and len(recording_sid) == 34:
                print(f"[DEBUG] TranscriptionService: SID validation passed: {recording_sid}")
                return recording_sid
            else:
                print(f"[WARNING] TranscriptionService: Invalid recording SID format: {recording_sid}")
                print(f"[WARNING] TranscriptionService: Expected format: RE followed by 32 characters")
                return None
                
        except Exception as e:
            print(f"[ERROR] TranscriptionService: Failed to extract recording SID: {str(e)}")
            import traceback
            print(f"[ERROR] TranscriptionService: SID extraction traceback: {traceback.format_exc()}")
            return None
