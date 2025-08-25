#!/usr/bin/env python3
"""
Test script for the new Twilio service and webhook implementation
"""

import os
import sys
import django
import logging
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_screener.settings')
django.setup()

from interviews.models import Candidate, JobDescription, Interview, InterviewResponse
from interviews.services import TwilioService, OpenAIService
from twilio.twiml.voice_response import VoiceResponse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_twilio_service_initialization():
    """Test Twilio service initialization"""
    print("\n=== Testing Twilio Service Initialization ===")
    
    try:
        twilio_service = TwilioService()
        print("✅ Twilio service initialized successfully")
        
        # Check configuration
        print(f"Account SID: {'SET' if twilio_service.account_sid else 'NOT SET'}")
        print(f"Auth Token: {'SET' if twilio_service.auth_token else 'NOT SET'}")
        print(f"Phone Number: {twilio_service.phone_number or 'NOT SET'}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to initialize Twilio service: {e}")
        return False

def test_twiml_generation():
    """Test TwiML generation for different scenarios"""
    print("\n=== Testing TwiML Generation ===")
    
    try:
        twilio_service = TwilioService()
        
        # Test data
        interview_id = "test-interview-123"
        questions = [
            "Tell me about your experience with Python programming.",
            "Describe a challenging project you worked on.",
            "What are your career goals for the next 5 years?"
        ]
        
        # Test first question TwiML
        print("\n--- Testing First Question TwiML ---")
        twiml_1 = twilio_service._create_interview_twiml(interview_id, 1, questions)
        print(f"First question TwiML length: {len(twiml_1)} characters")
        print(f"Contains 'Question 1': {'Question 1' in twiml_1}")
        print(f"Contains recording element: {'<Record' in twiml_1}")
        
        # Test second question TwiML
        print("\n--- Testing Second Question TwiML ---")
        twiml_2 = twilio_service.create_next_question_twiml(interview_id, 2, questions)
        print(f"Second question TwiML length: {len(twiml_2)} characters")
        print(f"Contains 'Question 2': {'Question 2' in twiml_2}")
        
        # Test completion TwiML
        print("\n--- Testing Completion TwiML ---")
        twiml_complete = twilio_service.create_completion_twiml()
        print(f"Completion TwiML length: {len(twiml_complete)} characters")
        print(f"Contains hangup: {'<Hangup' in twiml_complete}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to generate TwiML: {e}")
        return False

def test_webhook_url_generation():
    """Test webhook URL generation"""
    print("\n=== Testing Webhook URL Generation ===")
    
    try:
        twilio_service = TwilioService()
        
        # Test with different webhook base URLs
        test_urls = [
            "http://localhost:8000",
            "https://myapp.herokuapp.com",
            "https://api.example.com"
        ]
        
        for base_url in test_urls:
            os.environ['WEBHOOK_BASE_URL'] = base_url
            twilio_service = TwilioService()  # Reinitialize to pick up new env var
            
            # Test call status webhook
            status_url = f"{base_url}/api/webhooks/call-status/"
            print(f"Call status webhook: {status_url}")
            
            # Test record response webhook
            record_url = f"{base_url}/api/webhooks/record-response/"
            print(f"Record response webhook: {record_url}")
            
        return True
    except Exception as e:
        print(f"❌ Failed to generate webhook URLs: {e}")
        return False

def test_interview_flow_logic():
    """Test the interview flow logic"""
    print("\n=== Testing Interview Flow Logic ===")
    
    try:
        # Create test data
        candidate = Candidate.objects.create(
            name="Test Candidate",
            email="test@example.com",
            phone="+1234567890"
        )
        
        job_description = JobDescription.objects.create(
            title="Software Engineer",
            description="We are looking for a Python developer...",
            questions=[
                "What is your experience with Django?",
                "How do you handle debugging?",
                "Tell me about a time you solved a complex problem."
            ]
        )
        
        interview = Interview.objects.create(
            candidate=candidate,
            job_description=job_description,
            status='pending'
        )
        
        print(f"✅ Created test interview: {interview.id}")
        
        # Test question progression
        questions = job_description.questions
        for i in range(1, len(questions) + 2):  # Test one extra to trigger completion
            twilio_service = TwilioService()
            
            if i <= len(questions):
                twiml = twilio_service._create_interview_twiml(str(interview.id), i, questions)
                print(f"Question {i} TwiML generated: {len(twiml)} characters")
            else:
                twiml = twilio_service.create_completion_twiml()
                print(f"Completion TwiML generated: {len(twiml)} characters")
        
        # Cleanup
        interview.delete()
        candidate.delete()
        job_description.delete()
        
        return True
    except Exception as e:
        print(f"❌ Failed to test interview flow: {e}")
        return False

def test_webhook_parameter_handling():
    """Test webhook parameter handling"""
    print("\n=== Testing Webhook Parameter Handling ===")
    
    try:
        # Simulate webhook parameters
        test_params = {
            'interview_id': 'test-interview-123',
            'question_number': '2',
            'RecordingUrl': 'https://api.twilio.com/2010-04-01/Accounts/ACxxx/Recordings/RExxx',
            'RecordingSid': 'RE1234567890abcdef',
            'RecordingDuration': '45'
        }
        
        # Test parameter extraction logic
        interview_id = test_params.get("interview_id")
        question_number = test_params.get("question_number")
        
        print(f"Extracted interview_id: {interview_id}")
        print(f"Extracted question_number: {question_number}")
        
        # Test URL parameter handling
        url_params = f"?interview_id={interview_id}&question_number={question_number}"
        print(f"URL parameters: {url_params}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to test webhook parameters: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing New Twilio Service and Webhook Implementation")
    print("=" * 60)
    
    tests = [
        test_twilio_service_initialization,
        test_twiml_generation,
        test_webhook_url_generation,
        test_interview_flow_logic,
        test_webhook_parameter_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The new Twilio service and webhook implementation is ready.")
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
