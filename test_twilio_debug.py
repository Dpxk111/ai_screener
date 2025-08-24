#!/usr/bin/env python3
"""
Twilio Debug Test Script
This script helps debug Twilio configuration and call issues.
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta

def print_header(title):
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)

def print_section(title):
    print(f"\n--- {title} ---")

def check_environment_variables():
    """Check if all required environment variables are set"""
    print_section("Environment Variables Check")

    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')
    WEBHOOK_BASE_URL = os.getenv('WEBHOOK_BASE_URL')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    print("SUCCESS")

def test_twilio_client():
    """Test Twilio client initialization"""
    print_section("Twilio Client Test")
    
    try:
        from twilio.rest import Client
        
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        
        if not account_sid or not auth_token:
            print("✗ Cannot initialize Twilio client - missing credentials")
            return None
        
        client = Client(account_sid, auth_token)
        print("✓ Twilio client initialized successfully")
        
        # Test API connectivity
        try:
            account = client.api.accounts(account_sid).fetch()
            print(f"✓ Twilio API connectivity test passed")
            print(f"  Account: {account.friendly_name}")
            print(f"  Status: {account.status}")
        except Exception as e:
            print(f"✗ Twilio API connectivity test failed: {str(e)}")
            return None
        
        return client
        
    except Exception as e:
        print(f"✗ Failed to initialize Twilio client: {str(e)}")
        return None

def test_webhook_urls():
    """Test webhook URL accessibility"""
    print_section("Webhook URL Test")
    
    webhook_base_url = os.getenv('WEBHOOK_BASE_URL')
    if not webhook_base_url:
        print("✗ WEBHOOK_BASE_URL not set")
        return False
    
    print(f"Webhook base URL: {webhook_base_url}")
    
    # Test endpoints
    endpoints = [
        'api/webhooks/call-status/',
        'api/webhooks/record-response/',
        'api/twilio/recordings/',
        'api/twilio/debug/'
    ]
    
    all_accessible = True
    for endpoint in endpoints:
        url = f"{webhook_base_url.rstrip('/')}/{endpoint}"
        try:
            print(f"Testing: {url}")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"✓ {endpoint}: Accessible (200)")
            else:
                print(f"⚠ {endpoint}: Status {response.status_code}")
                all_accessible = False
        except Exception as e:
            print(f"✗ {endpoint}: Error - {str(e)}")
            all_accessible = False
    
    return all_accessible

def list_recent_recordings(client):
    """List recent Twilio recordings"""
    print_section("Recent Recordings")
    
    if not client:
        print("✗ No Twilio client available")
        return
    
    try:
        # Get recordings from last 7 days
        date_after = datetime.now() - timedelta(days=7)
        
        recordings = client.recordings.list(
            limit=10,
            date_created_after=date_after
        )
        
        print(f"Found {len(recordings)} recordings in the last 7 days:")
        
        for i, recording in enumerate(recordings[:5]):  # Show first 5
            print(f"\nRecording {i+1}:")
            print(f"  SID: {recording.sid}")
            print(f"  Status: {getattr(recording, 'status', 'N/A')}")
            print(f"  Duration: {getattr(recording, 'duration', 'N/A')} seconds")
            print(f"  Date Created: {getattr(recording, 'date_created', 'N/A')}")
            print(f"  Call SID: {getattr(recording, 'call_sid', 'N/A')}")
            
            # Test media URL accessibility
            media_url = None
            if hasattr(recording, 'uri') and recording.uri:
                # Fix: Remove .json and add .mp3 correctly
                base_uri = recording.uri.replace('.json', '')
                media_url = f"https://api.twilio.com{base_uri}.mp3"
            elif hasattr(recording, 'media_location') and recording.media_location:
                media_url = recording.media_location
            
            if media_url:
                try:
                    response = requests.head(
                        media_url,
                        auth=(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN')),
                        timeout=10
                    )
                    if response.status_code == 200:
                        print(f"  Media URL: ✓ Accessible")
                    else:
                        print(f"  Media URL: ✗ Status {response.status_code}")
                except Exception as e:
                    print(f"  Media URL: ✗ Error - {str(e)}")
            else:
                print(f"  Media URL: ✗ Not available")
        
        if len(recordings) > 5:
            print(f"\n... and {len(recordings) - 5} more recordings")
            
    except Exception as e:
        print(f"✗ Error listing recordings: {str(e)}")

def list_recent_calls(client):
    """List recent Twilio calls"""
    print_section("Recent Calls")
    
    if not client:
        print("✗ No Twilio client available")
        return
    
    try:
        calls = client.calls.list(limit=5)
        
        print(f"Found {len(calls)} recent calls:")
        
        for i, call in enumerate(calls):
            print(f"\nCall {i+1}:")
            print(f"  SID: {call.sid}")
            print(f"  Status: {call.status}")
            print(f"  From: {call.from_}")
            print(f"  To: {call.to}")
            print(f"  Duration: {call.duration} seconds")
            print(f"  Date Created: {call.date_created}")
            
            if hasattr(call, 'error_code') and call.error_code:
                print(f"  Error Code: {call.error_code}")
            if hasattr(call, 'error_message') and call.error_message:
                print(f"  Error Message: {call.error_message}")
        
    except Exception as e:
        print(f"✗ Error listing calls: {str(e)}")

def test_django_api_endpoints():
    """Test Django API endpoints"""
    print_section("Django API Endpoints Test")
    
    webhook_base_url = os.getenv('WEBHOOK_BASE_URL')
    if not webhook_base_url:
        print("✗ WEBHOOK_BASE_URL not set")
        return
    
    endpoints = [
        ('GET', 'api/twilio/recordings/', 'List Twilio Recordings'),
        ('GET', 'api/twilio/debug/', 'Twilio Debug Info'),
        ('GET', 'api/interviews/list/', 'List Interviews'),
    ]
    
    for method, endpoint, description in endpoints:
        url = f"{webhook_base_url.rstrip('/')}/{endpoint}"
        try:
            print(f"Testing {method} {endpoint} ({description})...")
            response = requests.request(method, url, timeout=10)
            
            if response.status_code == 200:
                print(f"✓ {method} {endpoint}: Success (200)")
                try:
                    data = response.json()
                    if isinstance(data, dict) and 'total_recordings' in data:
                        print(f"  Found {data.get('total_recordings', 0)} recordings")
                    elif isinstance(data, dict) and 'interviews' in data:
                        print(f"  Found {len(data.get('interviews', []))} interviews")
                except:
                    pass
            else:
                print(f"⚠ {method} {endpoint}: Status {response.status_code}")
                
        except Exception as e:
            print(f"✗ {method} {endpoint}: Error - {str(e)}")

def main():
    """Main function"""
    print_header("Twilio Debug Test")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Check environment variables
    env_ok = check_environment_variables()
    
    if not env_ok:
        print("\n⚠ Some environment variables are missing. Please check your .env file.")
    
    # Test Twilio client
    client = test_twilio_client()
    
    # Test webhook URLs
    webhook_ok = test_webhook_urls()
    
    if not webhook_ok:
        print("\n⚠ Some webhook URLs are not accessible. Check your webhook configuration.")
    
    # List recent recordings and calls
    if client:
        list_recent_recordings(client)
        list_recent_calls(client)
    
    # Test Django API endpoints
    test_django_api_endpoints()
    
    print_header("Debug Test Complete")
    print("Check the output above for any issues.")
    
    if not env_ok:
        print("\n🔧 To fix environment issues:")
        print("1. Create a .env file in your project root")
        print("2. Add your Twilio and OpenAI credentials")
        print("3. Set WEBHOOK_BASE_URL to your public URL (e.g., ngrok URL)")
    
    if not webhook_ok:
        print("\n🔧 To fix webhook issues:")
        print("1. Make sure your Django server is running")
        print("2. Use ngrok or similar to expose localhost")
        print("3. Update WEBHOOK_BASE_URL with the public URL")

if __name__ == "__main__":
    main()
