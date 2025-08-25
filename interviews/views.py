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
from twilio.twiml.voice_response import VoiceResponse


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

        if not serializer.is_valid():
            logger.warning(f"JDToQuestionsView: Invalid serializer data: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        title = serializer.validated_data["title"]
        description = serializer.validated_data["description"]
        logger.info(f"JDToQuestionsView: Processing job title: {title}")

        # Check if JD already exists (case-insensitive match)
        existing_jd = JobDescription.objects.filter(
            Q(title__iexact=title) & Q(description__iexact=description)
        ).first()

        if existing_jd:
            logger.info(f"JDToQuestionsView: Found existing JD ID: {existing_jd.id}")
            return Response(
                {
                    "id": existing_jd.id,
                    "title": existing_jd.title,
                    "questions": existing_jd.questions,
                    "message": "Job description already exists",
                },
                status=status.HTTP_200_OK,
            )

        # Generate new questions
        logger.info("JDToQuestionsView: Generating new questions via OpenAIService")
        openai_service = OpenAIService()

        try:
            questions = openai_service.generate_questions_from_jd(title, description)
            logger.info(f"JDToQuestionsView: Generated {len(questions)} questions successfully")
        except Exception as e:
            logger.error(f"JDToQuestionsView: Failed to generate questions", exc_info=True)
            return Response(
                {"error": "Failed to generate interview questions. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Save JD with atomic safety
        try:
            with transaction.atomic():
                jd = JobDescription.objects.create(
                    title=title,
                    description=description,
                    questions=questions,
                )
                logger.info(f"JDToQuestionsView: Created JD with ID: {jd.id}")
        except Exception as e:
            logger.error(f"JDToQuestionsView: Failed to save JD", exc_info=True)
            return Response(
                {"error": "Failed to save job description. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "id": jd.id,
                "title": jd.title,
                "questions": jd.questions,
                "message": "Job description created successfully",
            },
            status=status.HTTP_201_CREATED,
        )


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
        audio_status = []
        
        for response in responses:
            try:
                if response.audio_url:
                    print(f"[DEBUG] ManualTranscriptionView: Processing response {response.id}")
                    print(f"[DEBUG] ManualTranscriptionView: Audio URL: {response.audio_url}")
                    
                    # Check audio availability first
                    audio_available = self._check_audio_availability(response.audio_url)
                    audio_status.append({
                        'response_id': str(response.id),
                        'audio_url': response.audio_url,
                        'available': audio_available
                    })
                    
                    if audio_available:
                        print(f"[DEBUG] ManualTranscriptionView: Audio available, transcribing response {response.id}")
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
                        errors.append(f"Response {response.id}: Audio file not available")
                else:
                    errors.append(f"Response {response.id}: No audio URL")
            except Exception as e:
                error_msg = f"Response {response.id}: {str(e)}"
                errors.append(error_msg)
                print(f"[ERROR] ManualTranscriptionView: {error_msg}")
        
        return Response({
            'message': f'Transcribed {transcribed_count} responses',
            'transcribed_count': transcribed_count,
            'errors': errors,
            'audio_status': audio_status
        })
    
    def _check_audio_availability(self, audio_url):
        """Check if audio file is available for download"""
        try:
            print(f"[DEBUG] ManualTranscriptionView: Checking audio availability for: {audio_url}")
            
            # Extract recording SID
            if '/Recordings/' in audio_url:
                recording_sid = audio_url.split('/Recordings/')[-1].split('?')[0]
            else:
                recording_sid = audio_url.split('/')[-1].split('?')[0]
            
            print(f"[DEBUG] ManualTranscriptionView: Extracted recording SID: {recording_sid}")
            
            # Check recording via Twilio API
            from twilio.rest import Client
            client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
            
            recording = client.recordings(recording_sid).fetch()
            print(f"[DEBUG] ManualTranscriptionView: Recording status: {getattr(recording, 'status', 'N/A')}")
            
            # Check if recording is completed
            if getattr(recording, 'status', '') == 'completed':
                print(f"[DEBUG] ManualTranscriptionView: Recording is completed and available")
                return True
            else:
                print(f"[DEBUG] ManualTranscriptionView: Recording status is not completed: {getattr(recording, 'status', 'N/A')}")
                return False
                
        except Exception as e:
            print(f"[ERROR] ManualTranscriptionView: Error checking audio availability: {str(e)}")
            return False

class FixStuckInterviewView(BaseAPIView):
    """Fix stuck interviews that are in progress but have no responses"""
    
    def post(self, request, interview_id):
        interview = get_object_or_404(Interview, id=interview_id)
        
        print(f"[DEBUG] FixStuckInterviewView: Fixing stuck interview {interview_id}")
        
        # Check if interview is stuck
        if interview.status != 'in_progress':
            return Response({
                'message': f'Interview is not stuck (status: {interview.status})',
                'status': interview.status
            })
        
        # Check if there are any responses
        responses = InterviewResponse.objects.filter(interview=interview)
        
        if responses.exists():
            return Response({
                'message': f'Interview has {responses.count()} responses, not stuck',
                'response_count': responses.count()
            })
        
        # Interview is stuck - mark as failed and provide details
        interview.status = 'failed'
        interview.completed_at = timezone.now()
        interview.save()
        
        print(f"[DEBUG] FixStuckInterviewView: Marked interview {interview_id} as failed")
        
        # Get call details from Twilio if possible
        call_details = {}
        if interview.twilio_call_sid:
            try:
                from twilio.rest import Client
                client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
                call = client.calls(interview.twilio_call_sid).fetch()
                call_details = {
                    'status': call.status,
                    'duration': call.duration,
                    'start_time': call.start_time,
                    'end_time': call.end_time,
                    'error_code': getattr(call, 'error_code', None),
                    'error_message': getattr(call, 'error_message', None)
                }
                print(f"[DEBUG] FixStuckInterviewView: Call details: {call_details}")
            except Exception as e:
                print(f"[ERROR] FixStuckInterviewView: Could not fetch call details: {str(e)}")
                call_details = {'error': str(e)}
        
        return Response({
            'message': 'Interview marked as failed',
            'interview_id': str(interview.id),
            'previous_status': 'in_progress',
            'new_status': 'failed',
            'call_sid': interview.twilio_call_sid,
            'call_details': call_details,
            'reason': 'No responses received - webhook likely not triggered'
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

class AudioAvailabilityView(APIView):
    """Check audio file availability"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        print(f"[DEBUG] AudioAvailabilityView: Audio availability check request received")
        
        audio_url = request.data.get('audio_url')
        if not audio_url:
            return Response({
                'error': 'audio_url is required'
            }, status=400)
        
        print(f"[DEBUG] AudioAvailabilityView: Checking availability for URL: {audio_url}")
        
        try:
            # Extract recording SID
            if '/Recordings/' in audio_url:
                recording_sid = audio_url.split('/Recordings/')[-1].split('?')[0]
            else:
                recording_sid = audio_url.split('/')[-1].split('?')[0]
            
            print(f"[DEBUG] AudioAvailabilityView: Extracted recording SID: {recording_sid}")
            
            # Check recording via Twilio API
            from twilio.rest import Client
            client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
            
            recording = client.recordings(recording_sid).fetch()
            
            # Get recording details
            recording_details = {
                'sid': recording.sid,
                'status': getattr(recording, 'status', 'N/A'),
                'duration': getattr(recording, 'duration', 'N/A'),
                'uri': getattr(recording, 'uri', 'N/A'),
                'media_location': getattr(recording, 'media_location', 'N/A'),
                'date_created': getattr(recording, 'date_created', 'N/A'),
                'date_updated': getattr(recording, 'date_updated', 'N/A')
            }
            
            print(f"[DEBUG] AudioAvailabilityView: Recording details: {recording_details}")
            
            # Check if recording is available
            is_available = getattr(recording, 'status', '') == 'completed'
            
            # Test media URL if available
            media_url = None
            media_accessible = False
            if hasattr(recording, 'uri') and recording.uri:
                media_url = f"https://api.twilio.com{recording.uri}.mp3"
            elif hasattr(recording, 'media_location') and recording.media_location:
                media_url = recording.media_location
            
            if media_url:
                try:
                    test_response = requests.head(
                        media_url,
                        auth=(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN')),
                        timeout=10
                    )
                    media_accessible = test_response.status_code == 200
                    print(f"[DEBUG] AudioAvailabilityView: Media URL test: {test_response.status_code}")
                except Exception as e:
                    print(f"[ERROR] AudioAvailabilityView: Media URL test failed: {str(e)}")
            
            return Response({
                'status': 'check_completed',
                'audio_url': audio_url,
                'recording_sid': recording_sid,
                'is_available': is_available,
                'media_accessible': media_accessible,
                'media_url': media_url,
                'recording_details': recording_details
            })
            
        except Exception as e:
            print(f"[ERROR] AudioAvailabilityView: Check failed: {str(e)}")
            return Response({
                'status': 'check_failed',
                'error': str(e),
                'audio_url': audio_url
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class TwilioWebhookView(View):
    """Handle Twilio webhooks for call status and recorded responses"""

    def post(self, request, *args, **kwargs):
        print(f"[DEBUG] TwilioWebhookView: Received webhook request")
        print(f"[DEBUG] Method: {request.method}, URL: {request.path}")
        print(f"[DEBUG] Headers: {dict(request.headers)}")
        print(f"[DEBUG] POST data: {dict(request.POST)}")
        print(f"[DEBUG] GET data: {dict(request.GET)}")
        print(f"[DEBUG] Body: {request.body.decode('utf-8') if request.body else 'No body'}")

        post_data = dict(request.POST)
        for key, value in post_data.items():
            print(f"[DEBUG] POST {key}: {value}")

        try:
            webhook_type = kwargs.get('webhook_type')
            call_status = post_data.get('CallStatus')
            recording_status = post_data.get('RecordingStatus')

            if not webhook_type:
                if call_status:
                    webhook_type = 'call-status'
                elif recording_status:
                    webhook_type = 'record-response'
                else:
                    webhook_type = 'unknown'

            if webhook_type == 'call-status':
                return self.handle_call_status(request)
            elif webhook_type == 'record-response':
                return self.handle_record_response(request)
            else:
                return HttpResponse("Invalid webhook type", status=400)

        except Exception as e:
            logger.error(f"Webhook error: {str(e)}", exc_info=True)
            return HttpResponse("Internal server error", status=500)

    def handle_call_status(self, request):
        call_sid = request.POST.get('CallSid')
        call_status = request.POST.get('CallStatus')
        recording_url = request.POST.get('RecordingUrl')
        recording_sid = request.POST.get('RecordingSid')
        call_duration = request.POST.get('CallDuration')

        try:
            interview = Interview.objects.get(twilio_call_sid=call_sid)

            if call_status == 'completed':
                answered_questions = InterviewResponse.objects.filter(interview=interview).count()
                if answered_questions >= 1:
                    interview.status = 'completed'
                    interview.audio_url = recording_url
                    interview.twilio_recording_sid = recording_sid
                    interview.duration = int(call_duration) if call_duration else None
                    interview.completed_at = timezone.now()
                    interview.save()
                    self.generate_final_results(interview)
                else:
                    interview.status = 'failed'
                    interview.completed_at = timezone.now()
                    interview.save()
            elif call_status in ['failed', 'busy', 'no-answer']:
                interview.status = 'failed'
                interview.completed_at = timezone.now()
                interview.save()

            return HttpResponse(status=200)

        except Interview.DoesNotExist:
            return HttpResponse(status=404)
        except Exception as e:
            logger.error(f"Call status error: {str(e)}", exc_info=True)
            return HttpResponse(status=500)

    def handle_record_response(self, request):
        """Handle recorded response and return next question"""
        try:
            interview_id = request.GET.get('interview_id')
            question_number = int(request.GET.get('question_number', 1))

            interview = get_object_or_404(Interview, id=interview_id)
            questions = interview.job_description.questions

            recording_url = request.POST.get('RecordingUrl')
            recording_sid = request.POST.get('RecordingSid')

            if question_number <= len(questions):
                question_text = questions[question_number - 1]
            else:
                question_text = f"Question {question_number}"

            response_obj, created = InterviewResponse.objects.get_or_create(
                interview=interview,
                question_number=question_number,
                defaults={"question": question_text, "transcript": "Processing..."}
            )
            response_obj.audio_url = recording_url
            response_obj.save()

            # Transcription
            try:
                transcription_service = TranscriptionService()
                transcript = transcription_service.transcribe_audio(recording_url)
                response_obj.transcript = transcript
                response_obj.save()
            except Exception as e:
                logger.error(f"Transcription error: {str(e)}", exc_info=True)
                response_obj.transcript = "Unable to transcribe audio"
                response_obj.save()

            # Analysis
            try:
                openai_service = OpenAIService()
                score, feedback = openai_service.analyze_response(
                    question_text,
                    response_obj.transcript,
                    interview.candidate.resume_text
                )
                response_obj.score = score
                response_obj.feedback = feedback
                response_obj.save()
            except Exception as e:
                logger.error(f"Analysis error: {str(e)}", exc_info=True)

            # Mark interview completed
            interview.status = 'completed'
            interview.completed_at = timezone.now()
            interview.save()
            self.generate_final_results(interview)

            # End call
            response = VoiceResponse()
            response.say("Thank you for completing the interview. We will review your response and get back to you soon. Goodbye!")
            response.hangup()
            return HttpResponse(str(response), content_type='text/xml')

        except Exception as e:
            logger.error(f"Record response error: {str(e)}", exc_info=True)
            return HttpResponse("Error processing response", status=500)

    def generate_final_results(self, interview):
        responses = InterviewResponse.objects.filter(interview=interview).order_by('question_number')
        if not responses.exists():
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
        except Exception as e:
            logger.error(f"Final results error: {str(e)}", exc_info=True)
class TwilioRecordingsListView(APIView):
    """API to list all available Twilio recordings"""
    
    def get(self, request):
        """Get all Twilio recordings with detailed information"""
        try:
            print(f"[DEBUG] TwilioRecordingsListView: Starting to fetch all Twilio recordings")
            logger.info("TwilioRecordingsListView: Starting to fetch all Twilio recordings")
            
            # Initialize Twilio client
            try:
                from twilio.rest import Client
                twilio_client = Client(
                    os.getenv('TWILIO_ACCOUNT_SID'),
                    os.getenv('TWILIO_AUTH_TOKEN')
                )
                print(f"[DEBUG] TwilioRecordingsListView: Twilio client initialized successfully")
            except Exception as e:
                print(f"[ERROR] TwilioRecordingsListView: Failed to initialize Twilio client: {str(e)}")
                logger.error(f"TwilioRecordingsListView: Failed to initialize Twilio client: {str(e)}", exc_info=True)
                return Response({
                    'error': 'Failed to initialize Twilio client',
                    'details': str(e)
                }, status=500)
            
            # Get query parameters for filtering
            limit = request.GET.get('limit', 50)
            status = request.GET.get('status', None)
            date_created_after = request.GET.get('date_created_after', None)
            date_created_before = request.GET.get('date_created_before', None)
            
            print(f"[DEBUG] TwilioRecordingsListView: Query parameters:")
            print(f"[DEBUG] TwilioRecordingsListView:   Limit: {limit}")
            print(f"[DEBUG] TwilioRecordingsListView:   Status: {status}")
            print(f"[DEBUG] TwilioRecordingsListView:   Date created after: {date_created_after}")
            print(f"[DEBUG] TwilioRecordingsListView:   Date created before: {date_created_before}")
            
            # Build list parameters
            list_params = {
                'limit': int(limit)
            }
            
            if status:
                list_params['status'] = status
            if date_created_after:
                list_params['date_created_after'] = date_created_after
            if date_created_before:
                list_params['date_created_before'] = date_created_before
            
            print(f"[DEBUG] TwilioRecordingsListView: List parameters: {list_params}")
            
            # Fetch recordings from Twilio
            try:
                print(f"[DEBUG] TwilioRecordingsListView: Fetching recordings from Twilio API...")
                recordings = twilio_client.recordings.list(**list_params)
                print(f"[DEBUG] TwilioRecordingsListView: Successfully fetched {len(recordings)} recordings")
                logger.info(f"TwilioRecordingsListView: Successfully fetched {len(recordings)} recordings")
            except Exception as e:
                print(f"[ERROR] TwilioRecordingsListView: Failed to fetch recordings: {str(e)}")
                logger.error(f"TwilioRecordingsListView: Failed to fetch recordings: {str(e)}", exc_info=True)
                return Response({
                    'error': 'Failed to fetch recordings from Twilio',
                    'details': str(e)
                }, status=500)
            
            # Process recordings
            recordings_data = []
            for i, recording in enumerate(recordings):
                try:
                    print(f"[DEBUG] TwilioRecordingsListView: Processing recording {i+1}/{len(recordings)}: {recording.sid}")
                    
                    # Get media URL
                    media_url = None
                    if hasattr(recording, 'uri') and recording.uri:
                        media_url = f"https://api.twilio.com{recording.uri}.mp3"
                    elif hasattr(recording, 'media_location') and recording.media_location:
                        media_url = recording.media_location
                    
                    # Test media URL accessibility
                    media_accessible = False
                    media_status_code = None
                    if media_url:
                        try:
                            import requests
                            test_response = requests.head(
                                media_url,
                                auth=(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN')),
                                timeout=10
                            )
                            media_status_code = test_response.status_code
                            media_accessible = test_response.status_code == 200
                            print(f"[DEBUG] TwilioRecordingsListView: Media URL test for {recording.sid}: {media_status_code}")
                        except Exception as e:
                            print(f"[WARNING] TwilioRecordingsListView: Could not test media URL for {recording.sid}: {str(e)}")
                    
                    recording_info = {
                        'sid': recording.sid,
                        'account_sid': getattr(recording, 'account_sid', None),
                        'call_sid': getattr(recording, 'call_sid', None),
                        'duration': getattr(recording, 'duration', None),
                        'status': getattr(recording, 'status', None),
                        'channels': getattr(recording, 'channels', None),
                        'source': getattr(recording, 'source', None),
                        'error_code': getattr(recording, 'error_code', None),
                        'uri': getattr(recording, 'uri', None),
                        'media_location': getattr(recording, 'media_location', None),
                        'media_url': media_url,
                        'media_accessible': media_accessible,
                        'media_status_code': media_status_code,
                        'date_created': getattr(recording, 'date_created', None),
                        'date_updated': getattr(recording, 'date_updated', None),
                        'start_time': getattr(recording, 'start_time', None),
                        'price': getattr(recording, 'price', None),
                        'price_unit': getattr(recording, 'price_unit', None),
                        'track': getattr(recording, 'track', None),
                    }
                    
                    recordings_data.append(recording_info)
                    print(f"[DEBUG] TwilioRecordingsListView: Successfully processed recording {recording.sid}")
                    
                except Exception as e:
                    print(f"[ERROR] TwilioRecordingsListView: Error processing recording {i+1}: {str(e)}")
                    logger.error(f"TwilioRecordingsListView: Error processing recording {i+1}: {str(e)}", exc_info=True)
                    # Continue with other recordings
                    continue
            
            # Prepare response
            response_data = {
                'total_recordings': len(recordings_data),
                'query_parameters': {
                    'limit': limit,
                    'status': status,
                    'date_created_after': date_created_after,
                    'date_created_before': date_created_before
                },
                'recordings': recordings_data,
                'summary': {
                    'completed': len([r for r in recordings_data if r['status'] == 'completed']),
                    'in_progress': len([r for r in recordings_data if r['status'] == 'in-progress']),
                    'failed': len([r for r in recordings_data if r['status'] == 'failed']),
                    'accessible_media': len([r for r in recordings_data if r['media_accessible']]),
                    'inaccessible_media': len([r for r in recordings_data if not r['media_accessible'] and r['media_url']])
                }
            }
            
            print(f"[DEBUG] TwilioRecordingsListView: Response summary:")
            print(f"[DEBUG] TwilioRecordingsListView:   Total recordings: {response_data['total_recordings']}")
            print(f"[DEBUG] TwilioRecordingsListView:   Completed: {response_data['summary']['completed']}")
            print(f"[DEBUG] TwilioRecordingsListView:   In progress: {response_data['summary']['in_progress']}")
            print(f"[DEBUG] TwilioRecordingsListView:   Failed: {response_data['summary']['failed']}")
            print(f"[DEBUG] TwilioRecordingsListView:   Accessible media: {response_data['summary']['accessible_media']}")
            print(f"[DEBUG] TwilioRecordingsListView:   Inaccessible media: {response_data['summary']['inaccessible_media']}")
            
            logger.info(f"TwilioRecordingsListView: Successfully returned {len(recordings_data)} recordings")
            return Response(response_data, status=200)
            
        except Exception as e:
            print(f"[ERROR] TwilioRecordingsListView: Unexpected error: {str(e)}")
            logger.error(f"TwilioRecordingsListView: Unexpected error: {str(e)}", exc_info=True)
            return Response({
                'error': 'Unexpected error occurred',
                'details': str(e)
            }, status=500)


class TwilioCallDebugView(APIView):
    """API to debug Twilio call issues"""
    
    def get(self, request):
        """Get Twilio configuration and test connectivity"""
        try:
            print(f"[DEBUG] TwilioCallDebugView: Starting Twilio configuration check")
            logger.info("TwilioCallDebugView: Starting Twilio configuration check")
            
            # Check environment variables
            config_status = {
                'twilio_account_sid': {
                    'set': bool(os.getenv('TWILIO_ACCOUNT_SID')),
                    'value': os.getenv('TWILIO_ACCOUNT_SID', 'NOT_SET')[:10] + '...' if os.getenv('TWILIO_ACCOUNT_SID') else 'NOT_SET'
                },
                'twilio_auth_token': {
                    'set': bool(os.getenv('TWILIO_AUTH_TOKEN')),
                    'value': 'SET' if os.getenv('TWILIO_AUTH_TOKEN') else 'NOT_SET'
                },
                'twilio_phone_number': {
                    'set': bool(os.getenv('TWILIO_PHONE_NUMBER')),
                    'value': os.getenv('TWILIO_PHONE_NUMBER', 'NOT_SET')
                },
                'webhook_base_url': {
                    'set': bool(os.getenv('WEBHOOK_BASE_URL')),
                    'value': os.getenv('WEBHOOK_BASE_URL', 'NOT_SET')
                }
            }
            
            print(f"[DEBUG] TwilioCallDebugView: Configuration status: {config_status}")
            
            # Test Twilio client initialization
            twilio_client_status = 'unknown'
            twilio_error = None
            try:
                from twilio.rest import Client
                twilio_client = Client(
                    os.getenv('TWILIO_ACCOUNT_SID'),
                    os.getenv('TWILIO_AUTH_TOKEN')
                )
                twilio_client_status = 'success'
                print(f"[DEBUG] TwilioCallDebugView: Twilio client initialized successfully")
            except Exception as e:
                twilio_client_status = 'failed'
                twilio_error = str(e)
                print(f"[ERROR] TwilioCallDebugView: Twilio client initialization failed: {str(e)}")
            
            # Test webhook URL accessibility
            webhook_status = 'unknown'
            webhook_error = None
            webhook_base_url = os.getenv('WEBHOOK_BASE_URL')
            if webhook_base_url:
                try:
                    import requests
                    test_url = f"{webhook_base_url}api/webhooks/call-status/"
                    print(f"[DEBUG] TwilioCallDebugView: Testing webhook URL: {test_url}")
                    
                    response = requests.get(test_url, timeout=10)
                    webhook_status = 'accessible' if response.status_code == 200 else f'status_{response.status_code}'
                    print(f"[DEBUG] TwilioCallDebugView: Webhook test response: {response.status_code}")
                except Exception as e:
                    webhook_status = 'inaccessible'
                    webhook_error = str(e)
                    print(f"[ERROR] TwilioCallDebugView: Webhook test failed: {str(e)}")
            else:
                webhook_status = 'not_configured'
                webhook_error = 'WEBHOOK_BASE_URL not set'
            
            # Get recent calls for debugging
            recent_calls = []
            try:
                if twilio_client_status == 'success':
                    calls = twilio_client.calls.list(limit=5)
                    for call in calls:
                        recent_calls.append({
                            'sid': call.sid,
                            'status': call.status,
                            'from_': call.from_,
                            'to': call.to,
                            'duration': call.duration,
                            'date_created': call.date_created,
                            'error_code': getattr(call, 'error_code', None),
                            'error_message': getattr(call, 'error_message', None)
                        })
                    print(f"[DEBUG] TwilioCallDebugView: Retrieved {len(recent_calls)} recent calls")
            except Exception as e:
                print(f"[ERROR] TwilioCallDebugView: Failed to get recent calls: {str(e)}")
            
            response_data = {
                'configuration': config_status,
                'twilio_client': {
                    'status': twilio_client_status,
                    'error': twilio_error
                },
                'webhook': {
                    'status': webhook_status,
                    'error': webhook_error,
                    'url': f"{webhook_base_url}api/webhooks/call-status/" if webhook_base_url else None
                },
                'recent_calls': recent_calls,
                'debug_info': {
                    'timestamp': timezone.now().isoformat(),
                    'environment': os.getenv('DJANGO_SETTINGS_MODULE', 'unknown')
                }
            }
            
            print(f"[DEBUG] TwilioCallDebugView: Debug response prepared")
            logger.info("TwilioCallDebugView: Configuration check completed")
            return Response(response_data, status=200)
            
        except Exception as e:
            print(f"[ERROR] TwilioCallDebugView: Unexpected error: {str(e)}")
            logger.error(f"TwilioCallDebugView: Unexpected error: {str(e)}", exc_info=True)
            return Response({
                'error': 'Unexpected error occurred',
                'details': str(e)
            }, status=500)