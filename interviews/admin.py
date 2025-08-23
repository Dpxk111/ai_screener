from django.contrib import admin
from .models import Candidate, JobDescription, Interview, InterviewResponse, InterviewResult


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'created_at']
    search_fields = ['name', 'email', 'phone']
    list_filter = ['created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(JobDescription)
class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at']
    search_fields = ['title', 'description']
    list_filter = ['created_at']
    readonly_fields = ['id', 'created_at']


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'candidate', 'job_description', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['candidate__name', 'candidate__email']
    readonly_fields = ['id', 'created_at', 'completed_at']


@admin.register(InterviewResponse)
class InterviewResponseAdmin(admin.ModelAdmin):
    list_display = ['interview', 'question_number', 'score', 'created_at']
    list_filter = ['question_number', 'created_at']
    search_fields = ['interview__candidate__name', 'question']
    readonly_fields = ['id', 'created_at']


@admin.register(InterviewResult)
class InterviewResultAdmin(admin.ModelAdmin):
    list_display = ['interview', 'overall_score', 'recommendation', 'created_at']
    list_filter = ['overall_score', 'created_at']
    search_fields = ['interview__candidate__name']
    readonly_fields = ['id', 'created_at']
