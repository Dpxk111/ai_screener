import os
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
        serializer = JDToQuestionsSerializer(data=request.data)
        if serializer.is_valid():
            title = serializer.validated_data["title"]
            description = serializer.validated_data["description"]

            # Check if JD already exists (duplicate)
            existing_jd = JobDescription.objects.filter(
                Q(title=title) & Q(description=description)
            ).first()

            if existing_jd:
                print("Existsssssss\n\n\n\n\n")
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
            openai_service = OpenAIService()
            try:
                questions = openai_service.generate_questions_from_jd(title, description)
                print(questions, "QUESTIONS/n/n/n/n/n/n/n")
            except Exception as e:
                return Response(
                    {"error": f"Failed to generate questions: {e}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            jd = JobDescription.objects.create(
                title=title,
                description=description,
                questions=questions
            )
            print(JobDescription.objects.all(), "JOB DESCRIPTION CREATED/n/n/n/n/n/n/n")

            return Response(
                {
                    "id": jd.id,
                    "title": jd.title,
                    "questions": jd.questions,
                    "message": "Job description created successfully"
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class UploadResumeView(BaseAPIView):
    """Upload and parse resume"""
    
    def post(self, request):
        serializer = ResumeUploadSerializer(data=request.data)
        if serializer.is_valid():
            resume_file = serializer.validated_data['resume']
            
            # Parse resume
            parser_service = ResumeParserService()
            resume_text = parser_service.parse_resume(resume_file)
            
            return Response({
                'resume_text': resume_text,
                'filename': resume_file.name
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateCandidateView(BaseAPIView):
    """Create a new candidate"""
    
    def post(self, request):
        serializer = CandidateCreateSerializer(data=request.data)
        if serializer.is_valid():
            candidate = serializer.save()
            
            # Parse resume if provided
            if candidate.resume:
                parser_service = ResumeParserService()
                candidate.resume_text = parser_service.parse_resume(candidate.resume)
                candidate.save()
            
            return Response(CandidateSerializer(candidate).data, status=status.HTTP_201_CREATED)
        
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
        serializer = CreateInterviewSerializer(data=request.data)
        if serializer.is_valid():
            try:
                candidate_id = serializer.validated_data['candidate_id']
                job_description_id = serializer.validated_data['job_description_id']
                
                candidate = get_object_or_404(Candidate, id=candidate_id)
                print("errorrorororororoo=============")

                job_description = get_object_or_404(JobDescription, id=job_description_id)
                print("errorrorororororoo==========")

                
                # Create interview record
                interview = Interview.objects.create(
                    candidate=candidate,
                    job_description=job_description,
                    status='pending'
                )
                
                # Initiate call
                twilio_service = TwilioService()
                call_sid = twilio_service.initiate_call(
                    str(interview.id),
                    candidate.phone,
                    job_description.questions
                )
                
                interview.twilio_call_sid = call_sid
                interview.status = 'in_progress'
                interview.save()
                
                return Response({
                    'interview_id': interview.id,
                    'call_sid': call_sid,
                    'status': 'call_initiated'
                }, status=status.HTTP_200_OK)
            except Exception as e:
                if 'interview' in locals():
                    interview.status = 'failed'
                    interview.save()
                return Response({
                    'error': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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


@method_decorator(csrf_exempt, name='dispatch')
class TwilioWebhookView(View):
    """Handle Twilio webhooks for call status and recorded responses"""

    def post(self, request, *args, **kwargs):
        webhook_type = kwargs.get('webhook_type')
        
        if webhook_type == 'call-status':
            return self.handle_call_status(request)
        elif webhook_type == 'record-response':
            return self.handle_record_response(request)
        else:
            return HttpResponse("Invalid webhook type", status=400)

    def handle_call_status(self, request):
        """Handle call status webhook"""
        call_sid = request.POST.get('CallSid')
        call_status = request.POST.get('CallStatus')
        recording_url = request.POST.get('RecordingUrl')
        recording_sid = request.POST.get('RecordingSid')
        call_duration = request.POST.get('CallDuration')

        print(f"[CALL STATUS] SID: {call_sid}, Status: {call_status}, Recording: {recording_url}")

        try:
            interview = Interview.objects.get(twilio_call_sid=call_sid)

            if call_status == 'completed':
                # Check if all questions have been answered
                total_questions = len(interview.job_description.questions)
                answered_questions = InterviewResponse.objects.filter(interview=interview).count()
                
                if answered_questions >= total_questions:
                    interview.status = 'completed'
                    interview.audio_url = recording_url
                    interview.twilio_recording_sid = recording_sid
                    interview.duration = int(call_duration) if call_duration else None
                    interview.completed_at = datetime.now()
                    interview.save()

                    print(f"[INTERVIEW COMPLETED] ID: {interview.id}, Questions: {answered_questions}/{total_questions}")

                    # Generate final results only after all questions are answered
                    self.generate_final_results(interview)
                else:
                    print(f"[INTERVIEW INCOMPLETE] ID: {interview.id}, Questions: {answered_questions}/{total_questions}")
                    interview.status = 'failed'
                    interview.save()

            return HttpResponse(status=200)
        except Interview.DoesNotExist:
            print(f"[ERROR] Interview with SID {call_sid} not found")
            return HttpResponse(status=404)

    def handle_record_response(self, request):
        """Handle recorded response and return next question"""
        interview_id = request.GET.get('interview_id')
        question_number = int(request.GET.get('question_number', 1))

        interview = get_object_or_404(Interview, id=interview_id)
        questions = interview.job_description.questions
        print(f"[RECORD RESPONSE] Interview: {interview_id}, Question: {question_number}")

        # Save current recording
        recording_url = request.POST.get('RecordingUrl')
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
        print(f"[SAVED RESPONSE] Q{question_number}, URL: {recording_url}")

        # Transcribe the audio recording
        try:
            transcription_service = TranscriptionService()
            transcript = transcription_service.transcribe_audio(recording_url)
            response_obj.transcript = transcript
            response_obj.save()
            print(f"[TRANSCRIBED] Q{question_number}: {transcript[:100]}...")
        except Exception as e:
            print(f"[TRANSCRIPTION ERROR] {e}")
            response_obj.transcript = "Unable to transcribe audio"
            response_obj.save()

        # Analyze response with actual transcript
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
            print(f"[ANALYZED RESPONSE] Score: {score}, Feedback: {feedback[:100]}...")
        except Exception as e:
            print(f"[ANALYSIS ERROR] {e}")

        # Generate TwiML for next question
        next_question_number = question_number + 1
        twiml = TwilioService()._create_interview_twiml(interview_id, next_question_number, questions)

        return HttpResponse(twiml, content_type='text/xml')

    def generate_final_results(self, interview):
        """Generate final interview results after all questions are done"""
        responses = InterviewResponse.objects.filter(interview=interview).order_by('question_number')
        if not responses.exists():
            print(f"[NO RESPONSES] Interview {interview.id}")
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
            print(f"[FINAL RESULTS GENERATED] Interview {interview.id}")
        except Exception as e:
            print(f"[FINAL RESULTS ERROR] {e}")