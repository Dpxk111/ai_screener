#!/usr/bin/env python3
"""
Test script to verify Twilio configuration and webhook setup
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_twilio_config():
    """Test Twilio configuration"""
    print("🔍 Testing Twilio Configuration...")
    print("-" * 50)
    
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    phone_number = os.getenv('TWILIO_PHONE_NUMBER')
    
    print(f"Account SID: {account_sid[:10] if account_sid else 'NOT_SET'}...")
    print(f"Auth Token: {'SET' if auth_token else 'NOT_SET'}")
    print(f"Phone Number: {phone_number or 'NOT_SET'}")
    
    if not all([account_sid, auth_token, phone_number]):
        print("❌ Missing Twilio configuration")
        return False
    
    # Test Twilio client
    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        account = client.api.accounts(account_sid).fetch()
        print(f"✅ Twilio account verified: {account.friendly_name}")
        return True
    except Exception as e:
        print(f"❌ Twilio configuration error: {e}")
        return False

def test_webhook_url():
    """Test webhook URL accessibility"""
    print("\n🔍 Testing Webhook URL...")
    print("-" * 50)
    
    webhook_url = os.getenv('WEBHOOK_BASE_URL')
    if not webhook_url:
        print("❌ WEBHOOK_BASE_URL not set")
        print("💡 Set this to your ngrok URL for local development")
        return False
    
    print(f"Webhook Base URL: {webhook_url}")
    
    # Test webhook endpoint
    test_url = f"{webhook_url}/api/webhook-test/"
    try:
        response = requests.get(test_url, timeout=10)
        if response.status_code == 200:
            print(f"✅ Webhook endpoint accessible: {response.status_code}")
            data = response.json()
            print(f"Response: {data.get('message', 'No message')}")
            return True
        else:
            print(f"❌ Webhook endpoint returned: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Webhook endpoint not accessible: {e}")
        if webhook_url.startswith('http://localhost'):
            print("💡 For local development, use ngrok to expose your server")
            print("   Run: ngrok http 8000")
        return False

def test_ngrok():
    """Test ngrok tunnel"""
    print("\n🔍 Testing ngrok tunnel...")
    print("-" * 50)
    
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
        if response.status_code == 200:
            tunnels = response.json()['tunnels']
            if tunnels:
                tunnel = tunnels[0]
                print(f"✅ ngrok tunnel active: {tunnel['public_url']}")
                print(f"Status: {tunnel['status']}")
                return True
            else:
                print("❌ No active ngrok tunnels")
                return False
        else:
            print(f"❌ ngrok API returned: {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print("❌ ngrok not running or not accessible")
        print("💡 Start ngrok with: ngrok http 8000")
        return False

def test_django_server():
    """Test Django server"""
    print("\n🔍 Testing Django server...")
    print("-" * 50)
    
    try:
        response = requests.get('http://localhost:8000/api/health/', timeout=5)
        if response.status_code == 200:
            print("✅ Django server is running")
            return True
        else:
            print(f"❌ Django server returned: {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print("❌ Django server not accessible")
        print("💡 Start Django server with: python manage.py runserver")
        return False

def main():
    """Run all tests"""
    print("🧪 Twilio Configuration Test Suite")
    print("=" * 60)
    
    tests = [
        ("Django Server", test_django_server),
        ("Twilio Configuration", test_twilio_config),
        ("ngrok Tunnel", test_ngrok),
        ("Webhook URL", test_webhook_url),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n📊 Test Results Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! Your Twilio setup should work correctly.")
    else:
        print("⚠️  Some tests failed. Please fix the issues above before testing Twilio calls.")
        print("\n💡 Quick fixes:")
        print("1. Install ngrok: winget install ngrok")
        print("2. Start ngrok: ngrok http 8000")
        print("3. Update .env with ngrok URL")
        print("4. Restart Django server")

if __name__ == "__main__":
    main()
