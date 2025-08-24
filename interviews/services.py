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
            openai_logger.info(f"OpenAIService: Making request to OpenAI with model {self.model}")
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            result = response.choices[0].message.content.strip()
            openai_logger.info(f"OpenAIService: Successfully received response from OpenAI")
            return result
        except Exception as e:
            openai_logger.error(f"OpenAIService: OpenAI request error: {str(e)}", exc_info=True)
            raise
    def clean_questions(self, raw_questions):
        """Cleans a list of questions returned by AI"""
        cleaned = []
        for q in raw_questions:
            # Skip any line that's not a real question
            if not q or q.lower() == 'json':
                continue
            # Remove leading/trailing whitespace and quotes
            q = q.strip().strip('"').strip("'").strip()
            if q:
                cleaned.append(q)
        return cleaned

    def generate_questions_from_jd(self, job_title, job_description):
        """Generate 5-7 interview questions from job description"""
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
        try:
            questions_text = self._make_request(prompt, temperature=0.7, max_tokens=500)
            questions_text = questions_text.strip().strip("```").strip()

            try:
                questions = json.loads(questions_text)
                openai_logger.info(f"OpenAIService: Successfully parsed JSON questions for {job_title}")
            except json.JSONDecodeError:
                openai_logger.warning(f"OpenAIService: JSON decode failed for {job_title}, falling back to line parsing")
                lines = questions_text.split("\n")
                questions = []
                for line in lines:
                    line = line.strip().strip('"').strip("'")
                    if line and line not in ["[", "]"]:
                        if line.endswith(","):
                            line = line[:-1].strip()
                        questions.append(line)
            
            res = self.clean_questions(questions[:7])
            openai_logger.info(f"OpenAIService: Generated {len(res)} questions for {job_title}")
            return res
        except Exception as e:
            openai_logger.error(f"OpenAIService: Error generating questions for {job_title}: {str(e)}", exc_info=True)
            raise


    def analyze_response(self, question, response_text, resume_context=""):
        """Analyze a candidate's response and provide score and feedback"""
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
        try:
            result_text = self._make_request(prompt, temperature=0.3, max_tokens=300)
            try:
                result = json.loads(result_text)
                score = result.get("score", 5.0)
                openai_logger.info(f"OpenAIService: Successfully analyzed response with score: {score}")
                return score, result.get("feedback", "No specific feedback available.")
            except json.JSONDecodeError:
                openai_logger.warning(f"OpenAIService: JSON decode failed for response analysis, using default values")
                return 5.0, "Analysis completed but feedback format was unexpected."
        except Exception as e:
            openai_logger.error(f"OpenAIService: Error analyzing response: {str(e)}", exc_info=True)
            return 5.0, "Unable to analyze response due to technical issues."

    def generate_final_recommendation(self, interview_responses, resume_context=""):
        """Generate final interview recommendation and overall score"""
        openai_logger.info(f"OpenAIService: Generating final recommendation for {len(interview_responses)} responses")
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
                openai_logger.info(f"OpenAIService: Successfully generated final recommendation with score: {result.get('overall_score', 5.0)}")
                return result
            except json.JSONDecodeError:
                openai_logger.warning(f"OpenAIService: JSON decode failed for final recommendation, using default values")
                return {
                    "overall_score": 5.0,
                    "recommendation": "Consider - Analysis completed but recommendation format was unexpected.",
                    "strengths": ["Analysis completed"],
                    "areas_for_improvement": ["Unable to provide specific feedback"]
                }

        except Exception as e:
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
        self.client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
    
    def initiate_call(self, interview_id, candidate_phone, questions):
        """Initiate a voice call to the candidate"""
        try:
            twilio_logger.info(f"TwilioService: Initiating call for interview {interview_id} to {candidate_phone}")
            
            # Parse whitelist from env
            whitelist_env = os.getenv('WHITELISTED_NUMBERS', '["*"]')
            try:
                whitelisted_numbers = json.loads(whitelist_env)
                twilio_logger.info(f"TwilioService: Loaded whitelist with {len(whitelisted_numbers)} numbers")
            except json.JSONDecodeError:
                twilio_logger.warning(f"TwilioService: Failed to parse whitelist, using default")
                whitelisted_numbers = ["*"]

            # Check if number is allowed
            if '*' not in whitelisted_numbers and candidate_phone not in whitelisted_numbers:
                twilio_logger.error(f"TwilioService: Phone number {candidate_phone} is not whitelisted")
                raise ValueError(f"Phone number {candidate_phone} is not whitelisted")

            twiml = self._create_interview_twiml(interview_id, question_number=1, questions=questions)
            twilio_logger.info(f"TwilioService: Generated TwiML for interview {interview_id}")

            # Make the call
            call = self.client.calls.create(
                twiml=twiml,
                to=candidate_phone,
                from_=self.phone_number,
                record=True,
                status_callback=f"{os.getenv('WEBHOOK_BASE_URL', 'http://localhost:8000')}/api/webhooks/call-status/",
                status_callback_event=['completed']
            )

            twilio_logger.info(f"TwilioService: Successfully initiated call with SID: {call.sid}")
            return call.sid

        except Exception as e:
            twilio_logger.error(f"TwilioService: Error initiating call: {str(e)}", exc_info=True)
            raise
        
    def _create_interview_twiml(self, interview_id, question_number, questions):
        response = VoiceResponse()

        if question_number <= len(questions):
            question = questions[question_number - 1]
            response.say(f"Question {question_number}: {question}")
            response.pause(length=1)
            response.say("Please provide your answer now.")
            response.record(
                max_length=120,
                play_beep=True,
                action=f"{os.getenv('WEBHOOK_BASE_URL')}/api/webhooks/record-response/?interview_id={interview_id}&question_number={question_number}",
                method='POST'
            )
        else:
            response.say("Thank you for completing the interview. We will review your responses and get back to you soon. Goodbye!")
            response.hangup()

        return str(response)


class ResumeParserService:
    """Service for parsing resume files"""
    
    def parse_resume(self, file):
        """Parse PDF or DOCX resume and extract text"""
        try:
            logger.info(f"ResumeParserService: Parsing resume file: {file.name}")
            if file.name.lower().endswith('.pdf'):
                result = self._parse_pdf(file)
                logger.info(f"ResumeParserService: Successfully parsed PDF resume, extracted {len(result)} characters")
                return result
            elif file.name.lower().endswith('.docx'):
                result = self._parse_docx(file)
                logger.info(f"ResumeParserService: Successfully parsed DOCX resume, extracted {len(result)} characters")
                return result
            else:
                logger.error(f"ResumeParserService: Unsupported file format: {file.name}")
                raise ValueError("Unsupported file format. Please upload PDF or DOCX.")
        except Exception as e:
            logger.error(f"ResumeParserService: Error parsing resume {file.name}: {str(e)}", exc_info=True)
            return "Unable to parse resume content."
    
    def _parse_pdf(self, file):
        """Parse PDF file"""
        try:
            logger.info(f"ResumeParserService: Starting PDF parsing for {file.name}")
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            result = text.strip()
            logger.info(f"ResumeParserService: Successfully parsed PDF with {len(pdf_reader.pages)} pages")
            return result
        except Exception as e:
            logger.error(f"ResumeParserService: Error parsing PDF {file.name}: {str(e)}", exc_info=True)
            return "Unable to extract text from PDF."
    
    def _parse_docx(self, file):
        """Parse DOCX file"""
        try:
            logger.info(f"ResumeParserService: Starting DOCX parsing for {file.name}")
            doc = Document(file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            result = text.strip()
            logger.info(f"ResumeParserService: Successfully parsed DOCX with {len(doc.paragraphs)} paragraphs")
            return result
        except Exception as e:
            logger.error(f"ResumeParserService: Error parsing DOCX {file.name}: {str(e)}", exc_info=True)
            return "Unable to extract text from DOCX."


class TranscriptionService:
    """Service for transcribing audio recordings"""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.twilio_client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
    
    def transcribe_audio(self, audio_url):
        """Transcribe audio from URL using OpenAI Whisper"""
        try:
            logger.info(f"TranscriptionService: Starting transcription for URL: {audio_url}")
            
            # Method 1: Try direct download first (for some Twilio URLs)
            try:
                logger.info("TranscriptionService: Attempting direct download...")
                response = requests.get(audio_url, timeout=30)
                if response.status_code == 200:
                    audio_data = response.content
                    logger.info(f"TranscriptionService: Direct download successful, size: {len(audio_data)} bytes")
                else:
                    logger.warning(f"TranscriptionService: Direct download failed: {response.status_code}")
                    raise Exception("Direct download failed")
            except Exception as e:
                logger.warning(f"TranscriptionService: Direct download error: {str(e)}")
                
                # Method 2: Use Twilio client for authenticated access
                try:
                    logger.info("TranscriptionService: Attempting Twilio client method...")
                    
                    # Extract recording SID from various possible URL formats
                    if '/Recordings/' in audio_url:
                        recording_sid = audio_url.split('/Recordings/')[-1].split('?')[0]
                    else:
                        recording_sid = audio_url.split('/')[-1].split('?')[0]
                    
                    logger.info(f"TranscriptionService: Extracted recording SID: {recording_sid}")
                    
                    # Get the recording using Twilio client
                    recording = self.twilio_client.recordings(recording_sid).fetch()
                    logger.info(f"TranscriptionService: Recording fetched: {recording.sid}")
                    
                    # Try different media URLs
                    media_urls = []
                    if hasattr(recording, 'media_location'):
                        media_urls.append(recording.media_location)
                    if hasattr(recording, 'uri'):
                        media_urls.append(f"https://api.twilio.com{recording.uri}.mp3")
                    
                    audio_data = None
                    for media_url in media_urls:
                        try:
                            logger.info(f"TranscriptionService: Trying media URL: {media_url}")
                            response = requests.get(
                                media_url,
                                auth=(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN')),
                                timeout=30
                            )
                            if response.status_code == 200:
                                audio_data = response.content
                                logger.info(f"TranscriptionService: Media download successful, size: {len(audio_data)} bytes")
                                break
                            else:
                                logger.warning(f"TranscriptionService: Media download failed: {response.status_code}")
                        except Exception as e:
                            logger.warning(f"TranscriptionService: Media download error: {str(e)}")
                    
                    if not audio_data:
                        raise Exception("Could not download audio from any media URL")
                        
                except Exception as e:
                    logger.error(f"TranscriptionService: Twilio client method error: {str(e)}", exc_info=True)
                    raise
            
            # Determine audio format and transcribe
            if audio_data:
                logger.info(f"TranscriptionService: Audio data obtained, attempting transcription...")
                
                # Try different file formats
                file_formats = [
                    ("audio.wav", "audio/wav"),
                    ("audio.mp3", "audio/mpeg"),
                    ("audio.m4a", "audio/mp4"),
                    ("audio.webm", "audio/webm")
                ]
                
                for filename, mime_type in file_formats:
                    try:
                        logger.info(f"TranscriptionService: Trying format: {mime_type}")
                        transcript = self.openai_client.audio.transcriptions.create(
                            model="whisper-1",
                            file=(filename, audio_data, mime_type),
                            response_format="text"
                        )
                        
                        result = transcript.strip()
                        logger.info(f"TranscriptionService: Success! Transcript: {result[:100]}...")
                        return result
                        
                    except Exception as e:
                        logger.warning(f"TranscriptionService: Format {mime_type} failed: {str(e)}")
                        continue
                
                raise Exception("All audio formats failed")
            else:
                raise Exception("No audio data obtained")
                
        except Exception as e:
            logger.error(f"TranscriptionService: Final error: {str(e)}", exc_info=True)
            return f"Unable to transcribe audio: {str(e)}"
