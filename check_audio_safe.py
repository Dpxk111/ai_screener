#!/usr/bin/env python3
"""
Safe script to check audio availability for specific recordings
No hardcoded secrets - all data provided via input
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_audio_availability(audio_url):
    """Check if audio file is available"""
    print(f"🔍 Checking audio availability for: {audio_url}")
    
    # Extract recording SID
    if '/Recordings/' in audio_url:
        recording_sid = audio_url.split('/Recordings/')[-1].split('?')[0]
    else:
        recording_sid = audio_url.split('/')[-1].split('?')[0]
    
    print(f"📋 Extracted recording SID: {recording_sid}")
    
    try:
        from twilio.rest import Client
        client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
        
        # Get recording details
        recording = client.recordings(recording_sid).fetch()
        
        print(f"✅ Recording found in Twilio")
        print(f"   SID: {recording.sid}")
        print(f"   Status: {getattr(recording, 'status', 'N/A')}")
        print(f"   Duration: {getattr(recording, 'duration', 'N/A')}")
        print(f"   URI: {getattr(recording, 'uri', 'N/A')}")
        print(f"   Media Location: {getattr(recording, 'media_location', 'N/A')}")
        print(f"   Date Created: {getattr(recording, 'date_created', 'N/A')}")
        print(f"   Date Updated: {getattr(recording, 'date_updated', 'N/A')}")
        
        # Check if recording is completed
        is_completed = getattr(recording, 'status', '') == 'completed'
        print(f"   Is Completed: {is_completed}")
        
        # Get media URL
        media_url = None
        if hasattr(recording, 'uri') and recording.uri:
            media_url = f"https://api.twilio.com{recording.uri}.mp3"
        elif hasattr(recording, 'media_location') and recording.media_location:
            media_url = recording.media_location
        
        if media_url:
            print(f"🔗 Media URL: {media_url}")
            
            # Test media URL accessibility
            try:
                print(f"🧪 Testing media URL accessibility...")
                response = requests.head(
                    media_url,
                    auth=(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN')),
                    timeout=10
                )
                print(f"📡 Media URL test response: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"✅ Media URL is accessible")
                    
                    # Try to get content length
                    content_length = response.headers.get('content-length')
                    if content_length:
                        print(f"📏 Content length: {content_length} bytes")
                    
                    # Try to download a small portion
                    try:
                        print(f"📥 Testing download...")
                        download_response = requests.get(
                            media_url,
                            auth=(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN')),
                            timeout=30,
                            stream=True
                        )
                        
                        if download_response.status_code == 200:
                            # Read first 1024 bytes to test
                            chunk = next(download_response.iter_content(1024))
                            print(f"✅ Download test successful, first {len(chunk)} bytes received")
                            print(f"📋 Content-Type: {download_response.headers.get('content-type', 'unknown')}")
                        else:
                            print(f"❌ Download test failed: {download_response.status_code}")
                            
                    except Exception as e:
                        print(f"❌ Download test error: {str(e)}")
                else:
                    print(f"❌ Media URL not accessible: {response.status_code}")
                    print(f"📋 Response headers: {dict(response.headers)}")
                    
            except Exception as e:
                print(f"❌ Media URL test error: {str(e)}")
        else:
            print(f"❌ No media URL found")
        
        return {
            'recording_sid': recording_sid,
            'status': getattr(recording, 'status', 'N/A'),
            'is_completed': is_completed,
            'media_url': media_url,
            'accessible': response.status_code == 200 if 'response' in locals() else False
        }
        
    except Exception as e:
        print(f"❌ Error checking recording: {str(e)}")
        return None

def main():
    """Main function"""
    print("🎤 Audio Availability Checker (Safe Version)")
    print("=" * 50)
    
    # Get audio URL from user input
    audio_url = input("Enter the Twilio recording URL to check: ").strip()
    
    if not audio_url:
        print("❌ No audio URL provided")
        return
    
    print(f"🔗 Checking URL: {audio_url}")
    print()
    
    result = check_audio_availability(audio_url)
    
    if result:
        print()
        print("📊 Summary:")
        print(f"   Recording SID: {result['recording_sid']}")
        print(f"   Status: {result['status']}")
        print(f"   Is Completed: {result['is_completed']}")
        print(f"   Media URL: {result['media_url']}")
        print(f"   Accessible: {result['accessible']}")
        
        if result['is_completed'] and result['accessible']:
            print("✅ Recording should be available for transcription")
        else:
            print("❌ Recording may not be available for transcription")
    else:
        print("❌ Could not check recording availability")

if __name__ == "__main__":
    main()
