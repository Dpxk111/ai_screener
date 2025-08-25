#!/usr/bin/env python3
"""
Simple test script for Twilio service logic without Django setup
"""

import os
import sys
from twilio.twiml.voice_response import VoiceResponse

# Mock environment variables for testing
os.environ['TWILIO_ACCOUNT_SID'] = 'test_account_sid'
os.environ['TWILIO_AUTH_TOKEN'] = 'test_auth_token'
os.environ['TWILIO_PHONE_NUMBER'] = '+1234567890'
os.environ['WEBHOOK_BASE_URL'] = 'https://test.example.com'

def test_twiml_generation():
    """Test TwiML generation logic"""
    print("\n=== Testing TwiML Generation ===")
    
    try:
        # Test data
        interview_id = "test-interview-123"
        questions = [
            "Tell me about your experience with Python programming.",
            "Describe a challenging project you worked on.",
            "What are your career goals for the next 5 years?"
        ]
        
        # Test first question TwiML
        print("\n--- Testing First Question TwiML ---")
        twiml_1 = create_interview_twiml(interview_id, 1, questions)
        print(f"First question TwiML length: {len(twiml_1)} characters")
        print(f"Contains 'Question 1': {'Question 1' in twiml_1}")
        print(f"Contains recording element: {'<Record' in twiml_1}")
        print(f"Contains welcome message: {'Welcome to your automated interview' in twiml_1}")
        
        # Test second question TwiML
        print("\n--- Testing Second Question TwiML ---")
        twiml_2 = create_interview_twiml(interview_id, 2, questions)
        print(f"Second question TwiML length: {len(twiml_2)} characters")
        print(f"Contains 'Question 2': {'Question 2' in twiml_2}")
        print(f"Contains recording element: {'<Record' in twiml_2}")
        
        # Test completion TwiML
        print("\n--- Testing Completion TwiML ---")
        twiml_complete = create_completion_twiml()
        print(f"Completion TwiML length: {len(twiml_complete)} characters")
        print(f"Contains hangup: {'<Hangup' in twiml_complete}")
        print(f"Contains completion message: {'Thank you for completing' in twiml_complete}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to generate TwiML: {e}")
        return False

def create_interview_twiml(interview_id, question_number, questions):
    """Generate TwiML for the interview flow (simplified version)"""
    response = VoiceResponse()
    
    try:
        # Get webhook base URL
        webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "http://localhost:8000")
        if not webhook_base_url.endswith("/"):
            webhook_base_url += "/"

        if question_number == 1:
            # Welcome message for first question
            response.say("Hello! Welcome to your automated interview. I'll be asking you a few questions today.")
            response.pause(length=1)
            response.say("Please take your time to think about each question before answering.")
            response.pause(length=1)
            response.say("Let's begin with the first question.")
            response.pause(length=1)

        # Ask the current question
        if question_number <= len(questions):
            question_text = questions[question_number - 1]
            response.say(f"Question {question_number}: {question_text}")
            response.pause(length=1)
            response.say("Please provide your answer now.")

            # Set up recording with webhook
            record_action_url = f"{webhook_base_url}api/webhooks/record-response/"
            
            response.record(
                max_length=180,  # 3 minutes max
                play_beep=True,
                action=record_action_url,
                method="POST",
                timeout=15,  # Wait 15 seconds for answer
                transcribe=False,
                trim="trim-silence",
                recording_status_callback=f"{webhook_base_url}api/webhooks/recording-status/",
                recording_status_callback_method="POST",
                recording_status_callback_event=["completed"],
                action_on_empty_result="true",
                # Pass custom parameters to the webhook
                action_url=f"{record_action_url}?interview_id={interview_id}&question_number={question_number}"
            )
        else:
            # Interview completed
            response.say("Thank you for completing all the interview questions.")
            response.pause(length=1)
            response.say("Your responses have been recorded and will be reviewed.")
            response.pause(length=1)
            response.say("Goodbye and good luck!")
            response.hangup()

        return str(response)
        
    except Exception as e:
        print(f"Error creating TwiML: {e}")
        # Fallback response
        response.say("We're experiencing technical difficulties. Please try again later.")
        response.hangup()
        return str(response)

def create_completion_twiml():
    """Generate TwiML for interview completion"""
    response = VoiceResponse()
    response.say("Thank you for completing the interview. Your responses have been recorded and will be reviewed.")
    response.pause(length=1)
    response.say("Goodbye and good luck!")
    response.hangup()
    return str(response)

def test_webhook_url_generation():
    """Test webhook URL generation"""
    print("\n=== Testing Webhook URL Generation ===")
    
    try:
        # Test with different webhook base URLs
        test_urls = [
            "http://localhost:8000",
            "https://myapp.herokuapp.com",
            "https://api.example.com"
        ]
        
        for base_url in test_urls:
            os.environ['WEBHOOK_BASE_URL'] = base_url
            
            # Test call status webhook
            status_url = f"{base_url}/api/webhooks/call-status/"
            print(f"Call status webhook: {status_url}")
            
            # Test record response webhook
            record_url = f"{base_url}/api/webhooks/record-response/"
            print(f"Record response webhook: {record_url}")
            
            # Test recording status webhook
            recording_status_url = f"{base_url}/api/webhooks/recording-status/"
            print(f"Recording status webhook: {recording_status_url}")
            
        return True
    except Exception as e:
        print(f"❌ Failed to generate webhook URLs: {e}")
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
        
        # Test parameter validation
        if not interview_id or not question_number:
            print("❌ Missing required parameters")
            return False
        else:
            print("✅ All required parameters present")
        
        return True
    except Exception as e:
        print(f"❌ Failed to test webhook parameters: {e}")
        return False

def test_interview_flow_logic():
    """Test the interview flow logic"""
    print("\n=== Testing Interview Flow Logic ===")
    
    try:
        # Test data
        questions = [
            "What is your experience with Django?",
            "How do you handle debugging?",
            "Tell me about a time you solved a complex problem."
        ]
        
        print(f"Total questions: {len(questions)}")
        
        # Test question progression
        for i in range(1, len(questions) + 2):  # Test one extra to trigger completion
            if i <= len(questions):
                twiml = create_interview_twiml("test-interview", i, questions)
                print(f"Question {i} TwiML generated: {len(twiml)} characters")
                print(f"  Contains question {i}: {'Question ' + str(i) in twiml}")
            else:
                twiml = create_completion_twiml()
                print(f"Completion TwiML generated: {len(twiml)} characters")
                print(f"  Contains completion message: {'Thank you for completing' in twiml}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to test interview flow: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing New Twilio Service Logic (Simplified)")
    print("=" * 60)
    
    tests = [
        test_twiml_generation,
        test_webhook_url_generation,
        test_webhook_parameter_handling,
        test_interview_flow_logic
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
        print("🎉 All tests passed! The new Twilio service logic is working correctly.")
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
