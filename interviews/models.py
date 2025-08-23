from django.db import models
import uuid
import os


def candidate_resume_path(instance, filename):
    """Generate file path for candidate resume"""
    ext = filename.split('.')[-1]
    filename = f"{instance.id}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('resumes', filename)


def interview_audio_path(instance, filename):
    """Generate file path for interview audio"""
    ext = filename.split('.')[-1]
    filename = f"interview_{instance.id}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('audio', filename)


class Candidate(models.Model):
    """Candidate model for storing candidate information"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)  # E.164 format
    resume = models.FileField(upload_to=candidate_resume_path, null=True, blank=True)
    resume_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.email})"


class JobDescription(models.Model):
    """Job description model for storing JD and generated questions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    questions = models.JSONField(default=list)  # Store generated questions
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Interview(models.Model):
    """Interview model for tracking interview sessions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE)
    job_description = models.ForeignKey(JobDescription, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    twilio_call_sid = models.CharField(max_length=100, null=True, blank=True)
    twilio_recording_sid = models.CharField(max_length=100, null=True, blank=True)
    audio_url = models.URLField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)  # Duration in seconds
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Interview {self.id} - {self.candidate.name}"


class InterviewResponse(models.Model):
    """Model for storing individual question responses"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='responses')
    question = models.TextField()
    question_number = models.IntegerField()
    transcript = models.TextField(blank=True)
    audio_url = models.URLField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['question_number']

    def __str__(self):
        return f"Response {self.question_number} - {self.interview.id}"


class InterviewResult(models.Model):
    """Model for storing final interview results and recommendations"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.OneToOneField(Interview, on_delete=models.CASCADE)
    overall_score = models.FloatField()
    recommendation = models.TextField()
    strengths = models.JSONField(default=list)
    areas_for_improvement = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result for {self.interview.id}"
