from django.urls import path
from . import views

urlpatterns = [
    # Core API endpoints
    path('jd-to-questions/', views.JDToQuestionsView.as_view(), name='jd_to_questions'),
    path('upload-resume/', views.UploadResumeView.as_view(), name='upload_resume'),
    path('candidates/', views.CreateCandidateView.as_view(), name='create_candidate'),
    path('candidates/<uuid:candidate_id>/', views.GetCandidateView.as_view(), name='get_candidate'),
    path('candidates/list/', views.ListCandidatesView.as_view(), name='list_candidates'),
    path('trigger-interview/', views.TriggerInterviewView.as_view(), name='trigger_interview'),
    path('interviews/<uuid:interview_id>/', views.GetInterviewStatusView.as_view(), name='get_interview_status'),
    path('interviews/<uuid:interview_id>/results/', views.GetResultsView.as_view(), name='get_results'),
    path('interviews/list/', views.ListInterviewsView.as_view(), name='list_interviews'),
    path('job-descriptions/list/', views.ListJobDescriptionsView.as_view(), name='list_job_descriptions'),
    
    # Twilio webhooks
    path('webhooks/call-status/', views.TwilioWebhookView.as_view(), {'webhook_type': 'call-status'}, name='call_status_webhook'),
    path('webhooks/record-response/', views.TwilioWebhookView.as_view(), {'webhook_type': 'record-response'}, name='record_response_webhook'),
]
