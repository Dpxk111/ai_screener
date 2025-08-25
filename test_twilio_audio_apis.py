#!/usr/bin/env python3
"""
Test script for Twilio Audio Recording APIs

This script demonstrates how to use the new Twilio audio recording APIs:
1. List all Twilio recordings
2. Get transcript for a specific recording

Usage:
    python test_twilio_audio_apis.py

Requirements:
    - requests library
    - Valid API key set in environment variable API_KEY
    - Valid Twilio credentials set in environment variables
"""

import os
import requests
import json
from datetime import datetime, timedelta

# Configuration
API_BASE_URL = "http://localhost:8000/api"  # Change this to your domain
API_KEY = os.getenv('API_KEY', 'your_api_key_here')

# Headers for API requests
HEADERS = {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
}

def test_list_recordings():
    """Test the list recordings API"""
    print("=" * 60)
    print("Testing List Recordings API")
    print("=" * 60)
    
    # Test 1: Get recent recordings
    print("\n1. Getting recent recordings...")
    try:
        response = requests.get(
            f"{API_BASE_URL}/twilio/recordings/?limit=5",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Found {data['total_recordings']} recordings")
            print(f"Summary: {data['summary']}")
            
            if data['recordings']:
                print("\nFirst recording details:")
                recording = data['recordings'][0]
                print(f"  SID: {recording['sid']}")
                print(f"  Status: {recording['status']}")
                print(f"  Duration: {recording['duration']} seconds")
                print(f"  Media accessible: {recording['media_accessible']}")
                print(f"  Created: {recording['date_created']}")
                
                return recording['sid']  # Return for transcript testing
            else:
                print("⚠️  No recordings found")
                return None
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        return None

def test_get_transcript(recording_sid):
    """Test the get transcript API"""
    print("\n" + "=" * 60)
    print("Testing Get Transcript API")
    print("=" * 60)
    
    if not recording_sid:
        print("⚠️  No recording SID available, skipping transcript test")
        return
    
    print(f"\n1. Getting transcript for recording: {recording_sid}")
    try:
        payload = {
            'recording_sid': recording_sid
        }
        
        response = requests.post(
            f"{API_BASE_URL}/twilio/transcript/",
            headers=HEADERS,
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Success! Transcript retrieved")
            print(f"Audio URL: {data['audio_url']}")
            print(f"Status: {data['status']}")
            print(f"Timestamp: {data['timestamp']}")
            
            if 'recording_details' in data:
                details = data['recording_details']
                print(f"Recording duration: {details.get('duration')} seconds")
                print(f"Recording status: {details.get('status')}")
            
            print(f"\nTranscript:")
            print("-" * 40)
            print(data['transcript'])
            print("-" * 40)
            
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def test_filter_recordings():
    """Test filtering recordings by date and status"""
    print("\n" + "=" * 60)
    print("Testing Filtered Recordings API")
    print("=" * 60)
    
    # Get recordings from the last 7 days
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    print(f"\n1. Getting recordings from the last 7 days (since {week_ago})...")
    try:
        response = requests.get(
            f"{API_BASE_URL}/twilio/recordings/?date_created_after={week_ago}&status=completed",
            headers=HEADERS
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Found {data['total_recordings']} completed recordings from last week")
            print(f"Summary: {data['summary']}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def test_transcript_with_audio_url():
    """Test transcript API with direct audio URL"""
    print("\n" + "=" * 60)
    print("Testing Transcript API with Audio URL")
    print("=" * 60)
    
    # This is a test - you would need a real audio URL
    test_audio_url = "https://api.twilio.com/2010-04-01/Accounts/AC1234567890abcdef/Recordings/RE1234567890abcdef.mp3"
    
    print(f"\n1. Testing transcript with audio URL (this will likely fail with test URL)...")
    try:
        payload = {
            'audio_url': test_audio_url
        }
        
        response = requests.post(
            f"{API_BASE_URL}/twilio/transcript/",
            headers=HEADERS,
            json=payload
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Success! Transcript retrieved from audio URL")
            print(f"Transcript: {data['transcript'][:100]}...")
        else:
            print(f"❌ Expected error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def test_error_handling():
    """Test error handling scenarios"""
    print("\n" + "=" * 60)
    print("Testing Error Handling")
    print("=" * 60)
    
    # Test 1: Missing API key
    print("\n1. Testing with missing API key...")
    try:
        response = requests.get(f"{API_BASE_URL}/twilio/recordings/")
        print(f"Status: {response.status_code}")
        if response.status_code == 401:
            print("✅ Correctly rejected request without API key")
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    # Test 2: Invalid recording SID
    print("\n2. Testing with invalid recording SID...")
    try:
        payload = {
            'recording_sid': 'INVALID_SID'
        }
        
        response = requests.post(
            f"{API_BASE_URL}/twilio/transcript/",
            headers=HEADERS,
            json=payload
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code in [400, 500]:
            print("✅ Correctly handled invalid recording SID")
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
    
    # Test 3: Missing parameters
    print("\n3. Testing with missing parameters...")
    try:
        payload = {}
        
        response = requests.post(
            f"{API_BASE_URL}/twilio/transcript/",
            headers=HEADERS,
            json=payload
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 400:
            print("✅ Correctly rejected request with missing parameters")
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def main():
    """Main test function"""
    print("Twilio Audio Recording APIs Test Script")
    print("=" * 60)
    
    # Check if API key is set
    if API_KEY == 'your_api_key_here':
        print("⚠️  Warning: API_KEY not set in environment variables")
        print("Please set the API_KEY environment variable to run the tests")
        return
    
    # Run tests
    recording_sid = test_list_recordings()
    test_get_transcript(recording_sid)
    test_filter_recordings()
    test_transcript_with_audio_url()
    test_error_handling()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
