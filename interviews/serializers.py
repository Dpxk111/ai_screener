from rest_framework import serializers
from .models import Candidate, JobDescription, Interview, InterviewResponse, InterviewResult


class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ['id', 'name', 'email', 'phone', 'resume', 'resume_text', 'created_at']
        read_only_fields = ['id', 'created_at']


class JobDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDescription
        fields = ['id', 'title', 'description', 'questions', 'created_at']
        read_only_fields = ['id', 'questions', 'created_at']


class InterviewResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewResponse
        fields = ['id', 'question', 'question_number', 'transcript', 'audio_url', 'score', 'feedback', 'created_at']
        read_only_fields = ['id', 'created_at']


class InterviewSerializer(serializers.ModelSerializer):
    candidate = CandidateSerializer(read_only=True)
    job_description = JobDescriptionSerializer(read_only=True)
    responses = InterviewResponseSerializer(many=True, read_only=True)
    
    class Meta:
        model = Interview
        fields = ['id', 'candidate', 'job_description', 'status', 'twilio_call_sid', 
                 'audio_url', 'duration', 'created_at', 'completed_at', 'responses']
        read_only_fields = ['id', 'status', 'twilio_call_sid', 'audio_url', 'duration', 'created_at', 'completed_at']


class InterviewResultSerializer(serializers.ModelSerializer):
    interview = InterviewSerializer(read_only=True)
    
    class Meta:
        model = InterviewResult
        fields = ['id', 'interview', 'overall_score', 'recommendation', 'strengths', 'areas_for_improvement', 'created_at']
        read_only_fields = ['id', 'created_at']


class CreateInterviewSerializer(serializers.Serializer):
    candidate_id = serializers.UUIDField()
    job_description_id = serializers.UUIDField()


class ResumeUploadSerializer(serializers.Serializer):
    resume = serializers.FileField()


class JDToQuestionsSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField()


class CandidateCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ['name', 'email', 'phone', 'resume']
