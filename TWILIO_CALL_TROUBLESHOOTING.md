# Twilio Call Troubleshooting Guide

This guide helps you debug and resolve Twilio call issues in the AI Interview Screener application.

## Quick Diagnostic Tools

### 1. Run the Debug Script
```bash
python test_twilio_debug.py
```

### 2. Check API Endpoints
- **List all recordings**: `GET /api/twilio/recordings/`
- **Debug Twilio config**: `GET /api/twilio/debug/`
- **Check webhook test**: `GET /api/webhook-test/`

## Common Issues and Solutions

### 1. Application Error During Calls

**Symptoms:**
- Calls fail with "application error"
- Webhooks not received
- Calls hang up immediately

**Diagnosis:**
1. Check Django server logs for errors
2. Verify webhook URLs are accessible
3. Test Twilio configuration

**Solutions:**

#### A. Webhook URL Issues
```bash
# Check if webhook URLs are accessible
curl -X GET "https://your-ngrok-url.ngrok.io/api/webhook-test/"
```

**Common fixes:**
- Update `WEBHOOK_BASE_URL` in `.env` file
- Ensure ngrok is running and URL is current
- Check firewall/network settings

#### B. Django Server Issues
```bash
# Check Django logs
python manage.py runserver 0.0.0.0:8000

# Look for these error patterns:
# - ImportError: No module named 'twilio'
# - AttributeError: 'NoneType' object has no attribute
# - ConnectionError: Failed to establish connection
```

**Common fixes:**
- Install missing dependencies: `pip install twilio`
- Check environment variables are loaded
- Restart Django server

#### C. Twilio Configuration Issues
```bash
# Test Twilio credentials
python -c "
from twilio.rest import Client
client = Client('YOUR_ACCOUNT_SID', 'YOUR_AUTH_TOKEN')
print('Twilio connection successful')
"
```

**Common fixes:**
- Verify Account SID and Auth Token
- Check phone number is verified in Twilio console
- Ensure account has sufficient credits

### 2. Recording Issues

**Symptoms:**
- Recordings not created
- Audio files not accessible (404 errors)
- Transcription failures

**Diagnosis:**
1. Check recording status in Twilio console
2. Test media URL accessibility
3. Verify recording permissions

**Solutions:**

#### A. Recording Not Created
- Ensure `record=True` in call parameters
- Check Twilio account recording settings
- Verify phone number supports recording

#### B. Media URL 404 Errors
```python
# Test media URL accessibility
import requests
response = requests.head(
    media_url,
    auth=(account_sid, auth_token),
    timeout=10
)
print(f"Status: {response.status_code}")
```

**Common fixes:**
- Wait for recording to complete (can take 1-2 minutes)
- Check recording SID format
- Verify authentication credentials

### 3. Webhook Processing Issues

**Symptoms:**
- Webhooks not received
- Call status not updated
- Responses not processed

**Diagnosis:**
1. Check webhook URL configuration
2. Monitor Django logs during calls
3. Test webhook endpoints manually

**Solutions:**

#### A. Webhook Not Received
```bash
# Test webhook endpoint
curl -X POST "https://your-ngrok-url.ngrok.io/api/webhooks/call-status/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "CallSid=test&CallStatus=completed"
```

#### B. Webhook Processing Errors
Check Django logs for:
- Database connection errors
- Missing environment variables
- Import errors

### 4. Call Initiation Issues

**Symptoms:**
- Calls not initiated
- Invalid phone number errors
- Authentication failures

**Diagnosis:**
1. Check phone number format
2. Verify Twilio credentials
3. Test call initiation manually

**Solutions:**

#### A. Phone Number Issues
```python
# Validate phone number format
phone_number = "+1234567890"  # Must include country code
```

#### B. Authentication Issues
```python
# Test Twilio client
from twilio.rest import Client
client = Client(account_sid, auth_token)
calls = client.calls.list(limit=1)
print("Authentication successful")
```

## Debugging Steps

### Step 1: Environment Check
```bash
# Check environment variables
echo "TWILIO_ACCOUNT_SID: ${TWILIO_ACCOUNT_SID:0:10}..."
echo "TWILIO_AUTH_TOKEN: ${TWILIO_AUTH_TOKEN:+SET}"
echo "TWILIO_PHONE_NUMBER: $TWILIO_PHONE_NUMBER"
echo "WEBHOOK_BASE_URL: $WEBHOOK_BASE_URL"
```

### Step 2: Django Server Check
```bash
# Start Django server with debug logging
python manage.py runserver 0.0.0.0:8000 --verbosity=2
```

### Step 3: Webhook Test
```bash
# Test webhook accessibility
curl -X GET "$WEBHOOK_BASE_URL/api/webhook-test/"
```

### Step 4: Twilio API Test
```bash
# Test Twilio API connectivity
python -c "
from twilio.rest import Client
import os
client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
account = client.api.accounts(os.getenv('TWILIO_ACCOUNT_SID')).fetch()
print(f'Account: {account.friendly_name}')
"
```

### Step 5: Call Test
```bash
# Test call initiation
curl -X POST "http://localhost:8000/api/interviews/trigger/" \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_phone": "+1234567890",
    "job_description_id": "test-id"
  }'
```

## Log Analysis

### Key Log Patterns to Look For

#### 1. Webhook Reception
```
[DEBUG] TwilioWebhookView: Received webhook request
[DEBUG] TwilioWebhookView: POST data: {...}
```

#### 2. Call Status Updates
```
[DEBUG] TwilioWebhookView: Call SID: CA...
[DEBUG] TwilioWebhookView: Call Status: completed
```

#### 3. Recording Processing
```
[DEBUG] TwilioWebhookView: Recording SID: RE...
[DEBUG] TwilioWebhookView: Recording URL: https://...
```

#### 4. Error Patterns
```
[ERROR] TwilioWebhookView: Unhandled exception in webhook
[ERROR] TranscriptionService: Failed to download audio
[ERROR] TwilioService: Error initiating call
```

## Configuration Checklist

### Required Environment Variables
```bash
# .env file
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1234567890
WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok.io
OPENAI_API_KEY=sk-...
```

### Required Dependencies
```bash
pip install twilio openai django requests
```

### Required Twilio Settings
- [ ] Account verified
- [ ] Phone number purchased and verified
- [ ] Webhook URLs configured
- [ ] Recording enabled
- [ ] Sufficient account credits

### Required Network Settings
- [ ] ngrok running and accessible
- [ ] Django server running on 0.0.0.0:8000
- [ ] Firewall allows incoming connections
- [ ] Webhook URLs publicly accessible

## Emergency Fixes

### 1. Reset All Configuration
```bash
# Stop all services
pkill -f "python manage.py runserver"
pkill -f "ngrok"

# Clear environment
unset TWILIO_ACCOUNT_SID TWILIO_AUTH_TOKEN

# Restart with fresh configuration
source .env
ngrok http 8000
python manage.py runserver 0.0.0.0:8000
```

### 2. Test with Minimal Setup
```python
# Minimal test script
from twilio.rest import Client
client = Client('AC...', '...')
call = client.calls.create(
    twiml='<Response><Say>Hello World</Say></Response>',
    to='+1234567890',
    from_='+0987654321'
)
print(f"Call SID: {call.sid}")
```

### 3. Check Twilio Console
- Log into Twilio Console
- Check Call Logs for error details
- Verify webhook delivery status
- Check account status and credits

## Support Resources

- **Twilio Documentation**: https://www.twilio.com/docs
- **Django Documentation**: https://docs.djangoproject.com/
- **ngrok Documentation**: https://ngrok.com/docs
- **Application Logs**: Check Django server output
- **Twilio Console**: https://console.twilio.com/

## Contact Information

If you continue to experience issues:
1. Run the debug script and share output
2. Check Twilio console for error details
3. Review Django logs for application errors
4. Verify all configuration steps completed
