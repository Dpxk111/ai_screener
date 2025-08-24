#!/usr/bin/env python3
"""
Test script for transcription service
"""

import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_transcription_service():
    """Test the transcription service directly"""
    print("🧪 Testing Transcription Service")
    print("=" * 50)
    
    # Test with a sample audio URL (you'll need to replace this with a real Twilio recording URL)
    audio_url = input("Enter Twilio recording URL to test: ").strip()
    
    if not audio_url:
        print("❌ No audio URL provided")
        return
    
    print(f"🔗 Testing with URL: {audio_url}")
    
    try:
        from interviews.services import TranscriptionService
        
        transcription_service = TranscriptionService()
        transcript = transcription_service.transcribe_audio(audio_url)
        
        print(f"✅ Transcription result: {transcript}")
        
    except Exception as e:
        print(f"❌ Transcription failed: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

def test_transcription_endpoint():
    """Test the transcription endpoint via API"""
    print("\n🌐 Testing Transcription Endpoint")
    print("=" * 50)
    
    audio_url = input("Enter Twilio recording URL to test: ").strip()
    
    if not audio_url:
        print("❌ No audio URL provided")
        return
    
    try:
        response = requests.post(
            'http://localhost:8000/api/transcription-test/',
            json={'audio_url': audio_url},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Transcription successful: {data.get('transcript', 'No transcript')}")
        else:
            print(f"❌ Transcription failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")

def test_manual_transcription():
    """Test manual transcription for an interview"""
    print("\n🔧 Testing Manual Transcription")
    print("=" * 50)
    
    interview_id = input("Enter interview ID: ").strip()
    
    if not interview_id:
        print("❌ No interview ID provided")
        return
    
    try:
        response = requests.post(
            f'http://localhost:8000/api/interviews/{interview_id}/transcribe/',
            headers={'X-API-Key': os.getenv('API_KEY', 'test-key')}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Manual transcription result: {data}")
        else:
            print(f"❌ Manual transcription failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")

def main():
    """Main test menu"""
    print("🎤 Transcription Testing Tool")
    print("=" * 50)
    
    while True:
        print("\nChoose an option:")
        print("1. Test transcription service directly")
        print("2. Test transcription endpoint")
        print("3. Test manual transcription for interview")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            test_transcription_service()
        elif choice == '2':
            test_transcription_endpoint()
        elif choice == '3':
            test_manual_transcription()
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
