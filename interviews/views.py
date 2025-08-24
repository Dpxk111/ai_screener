import os
import logging
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
from datetime import datetime
from django.utils import timezone
from django.db.models import Q

# Set up logger for this module
logger = logging.getLogger('interviews')

from .models import Candidate, JobDescription, Interview, InterviewResponse, InterviewResult
from .serializers import (
    CandidateSerializer, JobDescriptionSerializer, InterviewSerializer,
    InterviewResultSerializer, CreateInterviewSerializer, ResumeUploadSerializer,
    JDToQuestionsSerializer, CandidateCreateSerializer
)
from .services import OpenAIService, TwilioService, ResumeParserService, TranscriptionService


class APIKeyPermission(BasePermission):
    """Custom permission to check API key"""
    
    def has_permission(self, request, view):
        api_key = request.headers.get('X-API-Key') or request.GET.get('api_key')
        return api_key == os.getenv('API_KEY')


class BaseAPIView(APIView):
    """Base API view with API key authentication"""
    permission_classes = [APIKeyPermission]


class JDToQuestionsView(APIView):
    """Convert job description to interview questions using OpenAI"""

    def post(self, request):
        logger.info("JDToQuestionsView: Processing job description to questions request")
        serializer = JDToQuestionsSerializer(data=request.data)
        if serializer.is_valid():
            title = serializer.validated_data["title"]
            description = serializer.validated_data["description"]
            logger.info(f"JDToQuestionsView: Processing job title: {title}")

            # Check if JD already exists (duplicate)
            existing_jd = JobDescription.objects.filter(
                Q(title=title) & Q(description=description)
            ).first()

            if existing_jd:
                logger.info(f"JDToQuestionsView: Found existing job description with ID: {existing_jd.id}")
                return Response(
                    {
                        "id": existing_jd.id,
                        "title": existing_jd.title,
                        "questions": existing_jd.questions,
                        "message": "Job description already exists"
                    },
                    status=status.HTTP_200_OK
                )

            # Object does not exist, create new
            logger.info("JDToQuestionsView: Generating new questions from job description")
            openai_service = OpenAIService()
            try:
                questions = openai_service.generate_questions_from_jd(title, description)
                logger.info(f"JDToQuestionsView: Generated {len(questions)} questions successfully")
            except Exception as e:
                logger.error(f"JDToQuestionsView: Failed to generate questions: {str(e)}", exc_info=True)
                return Response(
                    {"error": f"Failed to generate questions: {e}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            try:
                jd = JobDescription.objects.create(
                    title=title,
                    description=description,
                    questions=questions
                )
                logger.info(f"JDToQuestionsView: Created job description with ID: {jd.id}")
            except Exception as e:
                logger.error(f"JDToQuestionsView: Failed to create job description: {str(e)}", exc_info=True)
                return Response(
                    {"error": f"Failed to save job description: {e}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(
                {
                    "id": jd.id,
                    "title": jd.title,
                    "questions": jd.questions,
                    "message": "Job description created successfully"
                },
                status=status.HTTP_201_CREATED
            )

        logger.warning(f"JDToQuestionsView: Invalid serializer data: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class UploadResumeView(BaseAPIView):
    """Upload and parse resume"""
    
    def post(self, request):
        logger.info("UploadResumeView: Processing resume upload request")
        serializer = ResumeUploadSerializer(data=request.data)
        if serializer.is_valid():
            resume_file = serializer.validated_data['resume']
            logger.info(f"UploadResumeView: Processing resume file: {resume_file.name}")
            
            # Parse resume
            parser_service = ResumeParserService()
            try:
                resume_text = parser_service.parse_resume(resume_file)
                logger.info(f"UploadResumeView: Successfully parsed resume, text length: {len(resume_text)}")
            except Exception as e:
                logger.error(f"UploadResumeView: Failed to parse resume: {str(e)}", exc_info=True)
                return Response({
                    'error': f'Failed to parse resume: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                'resume_text': resume_text,
                'filename': resume_file.name
            }, status=status.HTTP_200_OK)
        
        logger.warning(f"UploadResumeView: Invalid serializer data: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateCandidateView(BaseAPIView):
    """Create a new candidate"""
    
    def post(self, request):
        logger.info("CreateCandidateView: Processing candidate creation request")
        serializer = CandidateCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                candidate = serializer.save()
                logger.info(f"CreateCandidateView: Created candidate with ID: {candidate.id}")
                
                # Parse resume if provided
                if candidate.resume:
                    logger.info(f"CreateCandidateView: Parsing resume for candidate {candidate.id}")
                    parser_service = ResumeParserService()
                    try:
                        candidate.resume_text = parser_service.parse_resume(candidate.resume)
                        candidate.save()
                        logger.info(f"CreateCandidateView: Successfully parsed resume for candidate {candidate.id}")
                    except Exception as e:
                        logger.error(f"CreateCandidateView: Failed to parse resume for candidate {candidate.id}: {str(e)}", exc_info=True)
                        # Continue without resume text
                
                return Response(CandidateSerializer(candidate).data, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"CreateCandidateView: Failed to create candidate: {str(e)}", exc_info=True)
                return Response({
                    'error': f'Failed to create candidate: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        logger.warning(f"CreateCandidateView: Invalid serializer data: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetCandidateView(BaseAPIView):
    """Get candidate details"""
    
    def get(self, request, candidate_id):
        candidate = get_object_or_404(Candidate, id=candidate_id)
        return Response(CandidateSerializer(candidate).data)


class ListCandidatesView(BaseAPIView):
    """List all candidates"""
    
    def get(self, request):
        candidates = Candidate.objects.all().order_by('-created_at')
        return Response(CandidateSerializer(candidates, many=True).data)


class TriggerInterviewView(BaseAPIView):
    """Trigger an interview call"""
    
    def post(self, request):
        logger.info("TriggerInterviewView: Processing interview trigger request")
        serializer = CreateInterviewSerializer(data=request.data)
        if serializer.is_valid():
            try:
                candidate_id = serializer.validated_data['candidate_id']
                job_description_id = serializer.validated_data['job_description_id']
                
                logger.info(f"TriggerInterviewView: Triggering interview for candidate {candidate_id} with job description {job_description_id}")
                
                candidate = get_object_or_404(Candidate, id=candidate_id)
                logger.info(f"TriggerInterviewView: Found candidate {candidate.id}")

                job_description = get_object_or_404(JobDescription, id=job_description_id)
                logger.info(f"TriggerInterviewView: Found job description {job_description.id}")

                
                # Create interview record
                interview = Interview.objects.create(
                    candidate=candidate,
                    job_description=job_description,
                    status='pending'
                )
                logger.info(f"TriggerInterviewView: Created interview record with ID: {interview.id}")
                
                # Initiate call
                twilio_service = TwilioService()
                try:
                    call_sid = twilio_service.initiate_call(
                        str(interview.id),
                        candidate.phone,
                        job_description.questions
                    )
                    logger.info(f"TriggerInterviewView: Initiated Twilio call with SID: {call_sid}")
                except Exception as e:
                    logger.error(f"TriggerInterviewView: Failed to initiate Twilio call: {str(e)}", exc_info=True)
                    interview.status = 'failed'
                    interview.save()
                    raise e
                
                interview.twilio_call_sid = call_sid
                interview.status = 'in_progress'
                interview.save()
                logger.info(f"TriggerInterviewView: Updated interview {interview.id} status to in_progress")
                
                return Response({
                    'interview_id': interview.id,
                    'call_sid': call_sid,
                    'status': 'call_initiated'
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"TriggerInterviewView: Error during interview trigger: {str(e)}", exc_info=True)
                if 'interview' in locals():
                    interview.status = 'failed'
                    interview.save()
                    logger.info(f"TriggerInterviewView: Marked interview {interview.id} as failed")
                return Response({
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        logger.warning(f"TriggerInterviewView: Invalid serializer data: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetInterviewStatusView(BaseAPIView):
    """Get interview status and details"""
    
    def get(self, request, interview_id):
        interview = get_object_or_404(Interview, id=interview_id)
        return Response(InterviewSerializer(interview).data)


class GetResultsView(BaseAPIView):
    """Get interview results and recommendations"""
    
    def get(self, request, interview_id):
        interview = get_object_or_404(Interview, id=interview_id)
        
        # Check if results exist
        try:
            result = InterviewResult.objects.get(interview=interview)
            return Response(InterviewResultSerializer(result).data)
        except InterviewResult.DoesNotExist:
            return Response({
                'error': 'Results not yet available. Interview may still be in progress.'
            }, status=status.HTTP_404_NOT_FOUND)

class ManualTranscriptionView(BaseAPIView):
    """Manually transcribe interview responses"""
    
    def post(self, request, interview_id):
        interview = get_object_or_404(Interview, id=interview_id)
        
        # Get all responses that need transcription
        responses = InterviewResponse.objects.filter(
            interview=interview,
            transcript__in=['Processing...', 'Unable to transcribe audio']
        )
        
        if not responses.exists():
            return Response({
                'message': 'No responses need transcription',
                'transcribed_count': 0
            })
        
        transcribed_count = 0
        errors = []
        
        for response in responses:
            try:
                if response.audio_url:
                    print(f"[DEBUG] ManualTranscriptionView: Transcribing response {response.id}")
                    transcription_service = TranscriptionService()
                    transcript = transcription_service.transcribe_audio(response.audio_url)
                    
                    if not transcript.startswith('Transcription failed:'):
                        response.transcript = transcript
                        response.save()
                        transcribed_count += 1
                        print(f"[DEBUG] ManualTranscriptionView: Successfully transcribed response {response.id}")
                    else:
                        errors.append(f"Response {response.id}: {transcript}")
                else:
                    errors.append(f"Response {response.id}: No audio URL")
            except Exception as e:
                error_msg = f"Response {response.id}: {str(e)}"
                errors.append(error_msg)
                print(f"[ERROR] ManualTranscriptionView: {error_msg}")
        
        return Response({
            'message': f'Transcribed {transcribed_count} responses',
            'transcribed_count': transcribed_count,
            'errors': errors
        })


class ListInterviewsView(BaseAPIView):
    """List all interviews"""
    
    def get(self, request):
        interviews = Interview.objects.all().order_by('-created_at')
        return Response(InterviewSerializer(interviews, many=True).data)


class ListJobDescriptionsView(BaseAPIView):
    """List all job descriptions"""
    
    def get(self, request):
        jds = JobDescription.objects.all().order_by('-created_at')
        return Response(JobDescriptionSerializer(jds, many=True).data)


class HealthCheckView(APIView):
    """Health check endpoint"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({
            'status': 'healthy',
            'message': 'AI Interview Screener API is running'
        })

class WebhookTestView(APIView):
    """Test endpoint for webhook debugging"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        print(f"[DEBUG] WebhookTestView: Test request received")
        print(f"[DEBUG] WebhookTestView: Headers: {dict(request.headers)}")
        print(f"[DEBUG] WebhookTestView: GET params: {dict(request.GET)}")
        return Response({
            'status': 'webhook_test_successful',
            'message': 'Webhook endpoint is accessible',
            'headers': dict(request.headers),
            'params': dict(request.GET)
        })
    
    def post(self, request):
        print(f"[DEBUG] WebhookTestView: Test POST request received")
        print(f"[DEBUG] WebhookTestView: Headers: {dict(request.headers)}")
        print(f"[DEBUG] WebhookTestView: POST data: {dict(request.POST)}")
        return Response({
            'status': 'webhook_post_test_successful',
            'message': 'Webhook POST endpoint is accessible',
            'headers': dict(request.headers),
            'post_data': dict(request.POST)
        })

class TranscriptionTestView(APIView):
    """Test endpoint for transcription debugging"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        print(f"[DEBUG] TranscriptionTestView: Test transcription request received")
        
        audio_url = request.data.get('audio_url')
        if not audio_url:
            return Response({
                'error': 'audio_url is required'
            }, status=400)
        
        print(f"[DEBUG] TranscriptionTestView: Testing transcription for URL: {audio_url}")
        
        try:
            transcription_service = TranscriptionService()
            transcript = transcription_service.transcribe_audio(audio_url)
            
            return Response({
                'status': 'transcription_successful',
                'transcript': transcript,
                'audio_url': audio_url
            })
        except Exception as e:
            print(f"[ERROR] TranscriptionTestView: Transcription failed: {str(e)}")
            return Response({
                'status': 'transcription_failed',
                'error': str(e),
                'audio_url': audio_url
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class TwilioWebhookView(View):
    """Handle Twilio webhooks for call status and recorded responses"""

    def post(self, request, *args, **kwargs):
        print(f"[DEBUG] TwilioWebhookView: Received webhook request")
        print(f"[DEBUG] TwilioWebhookView: Method: {request.method}")
        print(f"[DEBUG] TwilioWebhookView: URL: {request.path}")
        print(f"[DEBUG] TwilioWebhookView: Headers: {dict(request.headers)}")
        print(f"[DEBUG] TwilioWebhookView: POST data: {dict(request.POST)}")
        print(f"[DEBUG] TwilioWebhookView: GET data: {dict(request.GET)}")
        
        webhook_type = kwargs.get('webhook_type')
        print(f"[DEBUG] TwilioWebhookView: Webhook type: {webhook_type}")
        
        if webhook_type == 'call-status':
            print(f"[DEBUG] TwilioWebhookView: Handling call status webhook")
            return self.handle_call_status(request)
        elif webhook_type == 'record-response':
            print(f"[DEBUG] TwilioWebhookView: Handling record response webhook")
            return self.handle_record_response(request)
        else:
            print(f"[ERROR] TwilioWebhookView: Invalid webhook type: {webhook_type}")
            return HttpResponse("Invalid webhook type", status=400)

    def handle_call_status(self, request):
        """Handle call status webhook"""
        print(f"[DEBUG] TwilioWebhookView: Handling call status webhook")
        
        call_sid = request.POST.get('CallSid')
        call_status = request.POST.get('CallStatus')
        recording_url = request.POST.get('RecordingUrl')
        recording_sid = request.POST.get('RecordingSid')
        call_duration = request.POST.get('CallDuration')

        print(f"[DEBUG] TwilioWebhookView: Call SID: {call_sid}")
        print(f"[DEBUG] TwilioWebhookView: Call Status: {call_status}")
        print(f"[DEBUG] TwilioWebhookView: Recording URL: {recording_url}")
        print(f"[DEBUG] TwilioWebhookView: Recording SID: {recording_sid}")
        print(f"[DEBUG] TwilioWebhookView: Call Duration: {call_duration}")

        logger.info(f"TwilioWebhookView: Call status update - SID: {call_sid}, Status: {call_status}, Recording: {recording_url}")

        try:
            print(f"[DEBUG] TwilioWebhookView: Looking for interview with call SID: {call_sid}")
            interview = Interview.objects.get(twilio_call_sid=call_sid)
            print(f"[DEBUG] TwilioWebhookView: Found interview {interview.id}")
            logger.info(f"TwilioWebhookView: Found interview {interview.id} for call SID {call_sid}")

            if call_status == 'completed':
                print(f"[DEBUG] TwilioWebhookView: Call completed, checking questions")
                # Check if all questions have been answered
                total_questions = len(interview.job_description.questions)
                answered_questions = InterviewResponse.objects.filter(interview=interview).count()
                
                print(f"[DEBUG] TwilioWebhookView: Total questions: {total_questions}")
                print(f"[DEBUG] TwilioWebhookView: Answered questions: {answered_questions}")
                
                logger.info(f"TwilioWebhookView: Interview {interview.id} completed - Questions: {answered_questions}/{total_questions}")
                
                if answered_questions >= total_questions:
                    print(f"[DEBUG] TwilioWebhookView: All questions answered, marking as completed")
                    interview.status = 'completed'
                    interview.audio_url = recording_url
                    interview.twilio_recording_sid = recording_sid
                    interview.duration = int(call_duration) if call_duration else None
                    interview.completed_at = datetime.now()
                    interview.save()

                    logger.info(f"TwilioWebhookView: Interview {interview.id} marked as completed")

                    # Generate final results only after all questions are answered
                    try:
                        print(f"[DEBUG] TwilioWebhookView: Generating final results")
                        self.generate_final_results(interview)
                        logger.info(f"TwilioWebhookView: Generated final results for interview {interview.id}")
                    except Exception as e:
                        print(f"[ERROR] TwilioWebhookView: Failed to generate final results: {str(e)}")
                        logger.error(f"TwilioWebhookView: Failed to generate final results for interview {interview.id}: {str(e)}", exc_info=True)
                else:
                    print(f"[DEBUG] TwilioWebhookView: Not all questions answered, marking as failed")
                    logger.warning(f"TwilioWebhookView: Interview {interview.id} incomplete - only {answered_questions}/{total_questions} questions answered")
                    interview.status = 'failed'
                    interview.save()

            print(f"[DEBUG] TwilioWebhookView: Returning 200 OK")
            return HttpResponse(status=200)
        except Interview.DoesNotExist:
            print(f"[ERROR] TwilioWebhookView: Interview with SID {call_sid} not found")
            logger.error(f"TwilioWebhookView: Interview with SID {call_sid} not found")
            return HttpResponse(status=404)
        except Exception as e:
            print(f"[ERROR] TwilioWebhookView: Error handling call status: {str(e)}")
            import traceback
            print(f"[ERROR] TwilioWebhookView: Traceback: {traceback.format_exc()}")
            logger.error(f"TwilioWebhookView: Error handling call status: {str(e)}", exc_info=True)
            return HttpResponse(status=500)

    def handle_record_response(self, request):
        """Handle recorded response and return next question"""
        print(f"[DEBUG] TwilioWebhookView: Handling record response webhook")
        
        interview_id = request.GET.get('interview_id')
        question_number = int(request.GET.get('question_number', 1))

        print(f"[DEBUG] TwilioWebhookView: Interview ID: {interview_id}")
        print(f"[DEBUG] TwilioWebhookView: Question number: {question_number}")

        logger.info(f"TwilioWebhookView: Processing recorded response - Interview: {interview_id}, Question: {question_number}")

        try:
            print(f"[DEBUG] TwilioWebhookView: Looking for interview with ID: {interview_id}")
            interview = get_object_or_404(Interview, id=interview_id)
            questions = interview.job_description.questions
            print(f"[DEBUG] TwilioWebhookView: Found interview with {len(questions)} questions")
            logger.info(f"TwilioWebhookView: Found interview {interview_id} with {len(questions)} questions")

            # Save current recording
            recording_url = request.POST.get('RecordingUrl')
            print(f"[DEBUG] TwilioWebhookView: Recording URL: {recording_url}")
            
            if question_number <= len(questions):
                question_text = questions[question_number - 1]
            else:
                question_text = f"Question {question_number}"
            
            print(f"[DEBUG] TwilioWebhookView: Question text: {question_text}")

            response_obj, created = InterviewResponse.objects.get_or_create(
                interview=interview,
                question_number=question_number,
                defaults={"question": question_text, "transcript": "Processing..."}
            )
            response_obj.audio_url = recording_url
            response_obj.save()
            print(f"[DEBUG] TwilioWebhookView: Saved response object, created: {created}")
            logger.info(f"TwilioWebhookView: Saved response for Q{question_number}, URL: {recording_url}")

            # Transcribe the audio recording
            try:
                print(f"[DEBUG] TwilioWebhookView: Starting transcription")
                transcription_service = TranscriptionService()
                transcript = transcription_service.transcribe_audio(recording_url)
                response_obj.transcript = transcript
                response_obj.save()
                print(f"[DEBUG] TwilioWebhookView: Transcription completed: {transcript[:100]}...")
                logger.info(f"TwilioWebhookView: Transcribed Q{question_number}: {transcript[:100]}...")
            except Exception as e:
                print(f"[ERROR] TwilioWebhookView: Transcription error: {str(e)}")
                logger.error(f"TwilioWebhookView: Transcription error for Q{question_number}: {str(e)}", exc_info=True)
                response_obj.transcript = "Unable to transcribe audio"
                response_obj.save()

            # Analyze response with actual transcript
            try:
                print(f"[DEBUG] TwilioWebhookView: Starting response analysis")
                openai_service = OpenAIService()
                score, feedback = openai_service.analyze_response(
                    question_text,
                    response_obj.transcript,
                    interview.candidate.resume_text
                )
                response_obj.score = score
                response_obj.feedback = feedback
                response_obj.save()
                print(f"[DEBUG] TwilioWebhookView: Analysis completed, score: {score}")
                logger.info(f"TwilioWebhookView: Analyzed response Q{question_number} - Score: {score}")
            except Exception as e:
                print(f"[ERROR] TwilioWebhookView: Analysis error: {str(e)}")
                logger.error(f"TwilioWebhookView: Analysis error for Q{question_number}: {str(e)}", exc_info=True)

            # Generate TwiML for next question
            next_question_number = question_number + 1
            print(f"[DEBUG] TwilioWebhookView: Generating TwiML for next question {next_question_number}")
            twiml = TwilioService()._create_interview_twiml(interview_id, next_question_number, questions)
            print(f"[DEBUG] TwilioWebhookView: Generated TwiML length: {len(twiml)}")
            logger.info(f"TwilioWebhookView: Generated TwiML for next question {next_question_number}")

            print(f"[DEBUG] TwilioWebhookView: Returning TwiML response")
            return HttpResponse(twiml, content_type='text/xml')
        except Exception as e:
            print(f"[ERROR] TwilioWebhookView: Error handling recorded response: {str(e)}")
            import traceback
            print(f"[ERROR] TwilioWebhookView: Traceback: {traceback.format_exc()}")
            logger.error(f"TwilioWebhookView: Error handling recorded response: {str(e)}", exc_info=True)
            return HttpResponse("Error processing response", status=500)

    def generate_final_results(self, interview):
        """Generate final interview results after all questions are done"""
        logger.info(f"TwilioWebhookView: Generating final results for interview {interview.id}")
        responses = InterviewResponse.objects.filter(interview=interview).order_by('question_number')
        if not responses.exists():
            logger.warning(f"TwilioWebhookView: No responses found for interview {interview.id}")
            return

        try:
            openai_service = OpenAIService()
            result_data = openai_service.generate_final_recommendation(
                responses,
                interview.candidate.resume_text
            )

            InterviewResult.objects.create(
                interview=interview,
                overall_score=result_data.get('overall_score', 5.0),
                recommendation=result_data.get('recommendation', 'Consider'),
                strengths=result_data.get('strengths', []),
                areas_for_improvement=result_data.get('areas_for_improvement', [])
            )
            logger.info(f"TwilioWebhookView: Generated final results for interview {interview.id} - Score: {result_data.get('overall_score', 5.0)}, Recommendation: {result_data.get('recommendation', 'Consider')}")
        except Exception as e:
            logger.error(f"TwilioWebhookView: Error generating final results for interview {interview.id}: {str(e)}", exc_info=True)