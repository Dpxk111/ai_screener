import os
import requests
import time
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

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
openai.api_key = os.getenv("OPENAI_API_KEY")



class OpenAIService:
    def __init__(self):
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def _make_request(self, prompt, temperature=0.7, max_tokens=500):
        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise

    def clean_questions(self, raw_questions):
        cleaned = []
        for q in raw_questions:
            if not q or q.lower() == 'json':
                continue
            q = q.strip().strip('"').strip("'").strip()
            if q:
                cleaned.append(q)
        return cleaned

    def generate_questions_from_jd(self, job_title, job_description):
        prompt = f"""
        Based on the following job description, generate exactly 5 relevant interview questions.

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
        questions_text = questions_text.strip().strip("```").strip()

        try:
            questions = json.loads(questions_text)
        except json.JSONDecodeError:
            lines = questions_text.split("\n")
            questions = []
            for line in lines:
                line = line.strip().strip('"').strip("'")
                if line and line not in ["[", "]"]:
                    if line.endswith(","):
                        line = line[:-1].strip()
                    questions.append(line)
        return self.clean_questions(questions[:5])


    def analyze_response(self, question, response_text, resume_context=""):
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
                return result.get("score", 5.0), result.get("feedback", "No feedback available.")
            except json.JSONDecodeError:
                return 5.0, "Analysis completed but format was unexpected."
        except Exception as e:
            return 5.0, "Unable to analyze response due to technical issues."

    def generate_final_recommendation(self, interview_responses, resume_context=""):
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
                    "recommendation": "Consider - format unexpected",
                    "strengths": ["Analysis completed"],
                    "areas_for_improvement": ["Unable to parse response"]
                }
        except Exception as e:
            return {
                "overall_score": 5.0,
                "recommendation": "Consider - technical error",
                "strengths": ["Interview completed"],
                "areas_for_improvement": ["Technical analysis unavailable"]
            }   


class TwilioService:
    def __init__(self):
        self.client = Client(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN')
        )
        self.phone_number = os.getenv('TWILIO_PHONE_NUMBER')
     
    def initiate_call(self, interview_id, candidate_phone, questions):
        try:
            webhook_base_url = os.getenv('WEBHOOK_BASE_URL', 'http://localhost:8000')
            if not webhook_base_url.endswith('/'):
                webhook_base_url += '/'
            
            twiml = self._create_interview_twiml(interview_id, 1, questions, webhook_base_url)

            call = self.client.calls.create(
                twiml=twiml,
                to=candidate_phone,
                from_=self.phone_number,
                record=True,
                status_callback=f"{webhook_base_url}api/webhooks/call-status/",
                status_callback_event=['completed']
            )

            return call.sid

        except Exception as e:
            raise
         
    def _create_interview_twiml(self, interview_id, question_number, questions, webhook_base_url):
        response = VoiceResponse()

        if question_number <= len(questions):
            question = questions[question_number - 1]
            response.say(f"Question {question_number}: {question}")
            response.pause(length=1)
            response.say("Please provide your answer now.")
            response.record(
                max_length=120,
                play_beep=True,
                action=f"{webhook_base_url}api/webhooks/record-response/?interview_id={interview_id}&question_number={question_number}",
                method='POST'
            )
        else:
            response.say("Thank you for completing the interview. Goodbye!")
            response.hangup()

        return str(response)


class ResumeParserService:
    def parse_resume(self, file):
        try:
            if file.name.lower().endswith('.pdf'):
                return self._parse_pdf(file)
            elif file.name.lower().endswith('.docx'):
                return self._parse_docx(file)
            else:
                raise ValueError("Unsupported file format. Please upload PDF or DOCX.")
        except Exception as e:
            return "Unable to parse resume content."
     
    def _parse_pdf(self, file):
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            return "Unable to extract text from PDF."
     
    def _parse_docx(self, file):
        try:
            doc = Document(file)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            return "Unable to extract text from DOCX."


class TranscriptionService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.twilio_client = Client(
            os.getenv("TWILIO_ACCOUNT_SID"),
            os.getenv("TWILIO_AUTH_TOKEN")
        )

    def transcribe_audio(self, audio_url: str) -> str:
        try:
            recording_sid = self._extract_recording_sid(audio_url)
            if not recording_sid:
                raise ValueError("Invalid recording SID")

            recording = self.twilio_client.recordings(recording_sid).fetch()

            waited = 0
            while getattr(recording, "status", "") != "completed" and waited < 30:
                time.sleep(5)
                waited += 5
                recording = self.twilio_client.recordings(recording_sid).fetch()

            if getattr(recording, "status", "") != "completed":
                raise Exception(f"Recording not completed (status={recording.status})")

            base_uri = recording.uri.replace('.json', '')
            if not base_uri.endswith('.mp3'):
                media_url = f"https://api.twilio.com{base_uri}.mp3"
            else:
                media_url = f"https://api.twilio.com{base_uri}"

            response = requests.get(
                media_url,
                auth=(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN")),
                timeout=30
            )
            if response.status_code != 200:
                raise Exception(f"Failed to download audio (HTTP {response.status_code})")

            audio_data = response.content

            transcript = self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=("audio.mp3", io.BytesIO(audio_data), "audio/mpeg"),
                response_format="text"
            )

            return transcript.strip()

        except Exception as e:
            return f"Transcription failed: {e}"

    def _extract_recording_sid(self, audio_url: str) -> str | None:
        try:
            if "/Recordings/" in audio_url:
                sid = audio_url.split("/Recordings/")[-1].split("?")[0]
            elif "/recordings/" in audio_url:
                sid = audio_url.split("/recordings/")[-1].split("?")[0]
            else:
                sid = audio_url.split("/")[-1].split("?")[0]
            
            if sid.startswith("RE"):
                sid = sid.split(".")[0]
                return sid
            
            return None

        except Exception:
            return None
