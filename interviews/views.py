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

from .models import Candidate, JobDescription, Interview, InterviewResponse, InterviewResult
from .serializers import (
    CandidateSerializer, JobDescriptionSerializer, InterviewSerializer,
    InterviewResultSerializer, CreateInterviewSerializer, ResumeUploadSerializer,
    JDToQuestionsSerializer, CandidateCreateSerializer
)
from .services import OllamaService, TwilioService, ResumeParserService


class APIKeyPermission(BasePermission):
    """Custom permission to check API key"""
    
    def has_permission(self, request, view):
        api_key = request.headers.get('X-API-Key') or request.GET.get('api_key')
        return api_key == os.getenv('API_KEY')


class BaseAPIView(APIView):
    """Base API view with API key authentication"""
    permission_classes = [APIKeyPermission]


class JDToQuestionsView(BaseAPIView):
    """Convert job description to interview questions"""
    
    def post(self, request):
        serializer = JDToQuestionsSerializer(data=request.data)
        if serializer.is_valid():
            title = serializer.validated_data['title']
            description = serializer.validated_data['description']
            
            # Generate questions using Ollama
            ollama_service = OllamaService()
            questions = ollama_service.generate_questions_from_jd(title, description)
            
            # Save job description with questions
            jd = JobDescription.objects.create(
                title=title,
                description=description,
                questions=questions
            )
            
            return Response({
                'id': jd.id,
                'title': jd.title,
                'questions': jd.questions
            }, status=status.HTTP_201_CREATED)
        
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
            candidate_id = serializer.validated_data['candidate_id']
            job_description_id = serializer.validated_data['job_description_id']
            
            candidate = get_object_or_404(Candidate, id=candidate_id)
            job_description = get_object_or_404(JobDescription, id=job_description_id)
            
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


# Webhook views for Twilio
@method_decorator(csrf_exempt, name='dispatch')
class TwilioWebhookView(View):
    """Handle Twilio webhooks"""
    
    def post(self, request, *args, **kwargs):
        """Handle Twilio webhook POST requests"""
        webhook_type = kwargs.get('webhook_type')
        
        if webhook_type == 'call-status':
            return self.handle_call_status(request)
        elif webhook_type == 'record-response':
            return self.handle_record_response(request)
        else:
            return HttpResponse(status=400)
    
    def handle_call_status(self, request):
        """Handle call status webhook"""
        call_sid = request.POST.get('CallSid')
        call_status = request.POST.get('CallStatus')
        recording_url = request.POST.get('RecordingUrl')
        recording_sid = request.POST.get('RecordingSid')
        call_duration = request.POST.get('CallDuration')
        
        try:
            interview = Interview.objects.get(twilio_call_sid=call_sid)
            
            if call_status == 'completed':
                interview.status = 'completed'
                interview.audio_url = recording_url
                interview.twilio_recording_sid = recording_sid
                interview.duration = int(call_duration) if call_duration else None
                interview.completed_at = datetime.now()
                interview.save()
                
                # Generate final results
                self.generate_final_results(interview)
            
            return HttpResponse(status=200)
            
        except Interview.DoesNotExist:
            return HttpResponse(status=404)
    
    def handle_record_response(self, request):
        """Handle recorded response webhook"""
        interview_id = request.GET.get('interview_id')
        question_number = int(request.GET.get('question_number', 1))
        recording_url = request.POST.get('RecordingUrl')
        
        try:
            interview = Interview.objects.get(id=interview_id)
            job_description = interview.job_description
            
            # Get the question
            if question_number <= len(job_description.questions):
                question = job_description.questions[question_number - 1]
            else:
                question = f"Question {question_number}"
            
            # Create response record
            response = InterviewResponse.objects.create(
                interview=interview,
                question=question,
                question_number=question_number,
                audio_url=recording_url,
                transcript="Processing..."  # Will be updated by STT
            )
            
            # TODO: Implement STT to get transcript
            # For now, we'll use a placeholder
            response.transcript = f"Response to question {question_number}"
            response.save()
            
            # Analyze response
            ollama_service = OllamaService()
            score, feedback = ollama_service.analyze_response(
                question, 
                response.transcript,
                interview.candidate.resume_text
            )
            
            response.score = score
            response.feedback = feedback
            response.save()
            
            return HttpResponse(status=200)
            
        except Interview.DoesNotExist:
            return HttpResponse(status=404)
    
    def generate_final_results(self, interview):
        """Generate final interview results"""
        responses = InterviewResponse.objects.filter(interview=interview).order_by('question_number')
        
        if responses.exists():
            ollama_service = OllamaService()
            result_data = ollama_service.generate_final_recommendation(
                responses, 
                interview.candidate.resume_text
            )
            
            InterviewResult.objects.create(
                interview=interview,
                overall_score=result_data['overall_score'],
                recommendation=result_data['recommendation'],
                strengths=result_data['strengths'],
                areas_for_improvement=result_data['areas_for_improvement']
            )
