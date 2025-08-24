#!/usr/bin/env python3
"""
Script to fix stuck interviews that are in progress but have no responses
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_screener.settings')
django.setup()

from interviews.models import Interview, InterviewResponse
from django.utils import timezone

def fix_stuck_interviews():
    """Find and fix stuck interviews"""
    print("🔧 Fixing stuck interviews...")
    
    # Find interviews that are in progress but have no responses
    stuck_interviews = Interview.objects.filter(
        status='in_progress',
        created_at__lt=timezone.now() - timedelta(minutes=10)  # Stuck for more than 10 minutes
    )
    
    # Check which ones have no responses
    fixed_count = 0
    for interview in stuck_interviews:
        responses = InterviewResponse.objects.filter(interview=interview)
        
        if not responses.exists():
            print(f"❌ Found stuck interview: {interview.id}")
            print(f"   Call SID: {interview.twilio_call_sid}")
            print(f"   Created: {interview.created_at}")
            print(f"   Duration stuck: {timezone.now() - interview.created_at}")
            
            # Mark as failed
            interview.status = 'failed'
            interview.completed_at = timezone.now()
            interview.save()
            
            print(f"✅ Marked interview {interview.id} as failed")
            fixed_count += 1
        else:
            print(f"ℹ️  Interview {interview.id} has {responses.count()} responses, not stuck")
    
    print(f"\n📊 Summary:")
    print(f"   Total stuck interviews found: {stuck_interviews.count()}")
    print(f"   Interviews fixed: {fixed_count}")
    
    return fixed_count

def get_call_details(call_sid):
    """Get call details from Twilio"""
    try:
        from twilio.rest import Client
        client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
        call = client.calls(call_sid).fetch()
        return {
            'status': call.status,
            'duration': call.duration,
            'start_time': call.start_time,
            'end_time': call.end_time,
            'error_code': getattr(call, 'error_code', None),
            'error_message': getattr(call, 'error_message', None)
        }
    except Exception as e:
        return {'error': str(e)}

def analyze_stuck_interview(interview_id):
    """Analyze a specific stuck interview"""
    try:
        interview = Interview.objects.get(id=interview_id)
        print(f"\n🔍 Analyzing interview: {interview.id}")
        print(f"   Status: {interview.status}")
        print(f"   Call SID: {interview.twilio_call_sid}")
        print(f"   Created: {interview.created_at}")
        print(f"   Completed: {interview.completed_at}")
        
        responses = InterviewResponse.objects.filter(interview=interview)
        print(f"   Responses: {responses.count()}")
        
        if interview.twilio_call_sid:
            call_details = get_call_details(interview.twilio_call_sid)
            print(f"   Call details: {call_details}")
        
        return interview
    except Interview.DoesNotExist:
        print(f"❌ Interview {interview_id} not found")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Analyze specific interview
        interview_id = sys.argv[1]
        analyze_stuck_interview(interview_id)
    else:
        # Fix all stuck interviews
        fix_stuck_interviews()
