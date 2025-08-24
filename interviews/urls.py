from django.urls import path
from . import views

urlpatterns = [
    # Health check
    path('health/', views.HealthCheckView.as_view(), name='health_check'),
    
    # Core API endpoints
    path('jd-to-questions/', views.JDToQuestionsView.as_view(), name='jd_to_questions'),
    path('upload-resume/', views.UploadResumeView.as_view(), name='upload_resume'),
    path('candidates/', views.CreateCandidateView.as_view(), name='create_candidate'),
    path('candidates/<uuid:candidate_id>/', views.GetCandidateView.as_view(), name='get_candidate'),
    path('candidates/list/', views.ListCandidatesView.as_view(), name='list_candidates'),
    path('trigger-interview/', views.TriggerInterviewView.as_view(), name='trigger_interview'),
    path('interviews/<uuid:interview_id>/', views.GetInterviewStatusView.as_view(), name='get_interview_status'),
    path('interviews/<uuid:interview_id>/results/', views.GetResultsView.as_view(), name='get_results'),
    path('interviews/<uuid:interview_id>/transcribe/', views.ManualTranscriptionView.as_view(), name='manual_transcription'),
    path('interviews/<uuid:interview_id>/fix-stuck/', views.FixStuckInterviewView.as_view(), name='fix_stuck_interview'),
    path('interviews/<uuid:interview_id>/flow/', views.InterviewFlowView.as_view(), name='interview_flow'),
    path('twilio/recordings/', views.TwilioRecordingsListView.as_view(), name='twilio_recordings_list'),
    path('twilio/debug/', views.TwilioCallDebugView.as_view(), name='twilio_call_debug'),
    path('interviews/list/', views.ListInterviewsView.as_view(), name='list_interviews'),
    path('job-descriptions/list/', views.ListJobDescriptionsView.as_view(), name='list_job_descriptions'),

    # Twilio webhooks
    path('webhooks/call-status/', views.TwilioWebhookView.as_view(), name='call_status_webhook'),
    path('webhooks/record-response/', views.TwilioWebhookView.as_view(), name='record_response_webhook'),
    path('webhooks/recording-status/', views.TwilioWebhookView.as_view(), name='recording_status_webhook'),
    
    # Debug endpoints
    path('webhook-test/', views.WebhookTestView.as_view(), name='webhook_test'),
    path('transcription-test/', views.TranscriptionTestView.as_view(), name='transcription_test'),
    path('audio-availability/', views.AudioAvailabilityView.as_view(), name='audio_availability'),
]
