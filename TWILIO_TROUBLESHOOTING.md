# Twilio Troubleshooting Guide

## Common Issues and Solutions

### 1. Webhook URL Issues (Most Common)

**Problem**: Twilio calls are initiated successfully but webhooks are not received.

**Root Cause**: Twilio cannot reach your localhost URLs.

**Solution**: Use ngrok to expose your local server.

#### Quick Fix with ngrok:

1. **Install ngrok**:
   ```bash
   # Windows
   winget install ngrok
   
   # Or download from https://ngrok.com/download
   ```

2. **Start ngrok tunnel**:
   ```bash
   ngrok http 8000
   ```

3. **Update your .env file**:
   ```
   WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok.io
   ```

4. **Restart your Django server**

### 2. Environment Variables

Make sure these are set in your `.env` file:

```env
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# Webhook Configuration (for local development)
WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok.io

# Optional: Whitelist phone numbers for testing
WHITELISTED_NUMBERS=["*"]
```

### 3. Debugging Steps

#### Step 1: Check Twilio Configuration
```python
# Add this to your Django shell or a test script
import os
from twilio.rest import Client

print(f"Account SID: {os.getenv('TWILIO_ACCOUNT_SID', 'NOT_SET')}")
print(f"Auth Token: {'SET' if os.getenv('TWILIO_AUTH_TOKEN') else 'NOT_SET'}")
print(f"Phone Number: {os.getenv('TWILIO_PHONE_NUMBER', 'NOT_SET')}")

# Test Twilio client
try:
    client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
    account = client.api.accounts(os.getenv('TWILIO_ACCOUNT_SID')).fetch()
    print(f"✅ Twilio account verified: {account.friendly_name}")
except Exception as e:
    print(f"❌ Twilio configuration error: {e}")
```

#### Step 2: Test Webhook Endpoints
```bash
# Test webhook endpoints locally
curl -X GET "http://localhost:8000/api/webhook-test/"
curl -X POST "http://localhost:8000/api/webhooks/call-status/" -d "CallSid=test&CallStatus=completed"
```

#### Step 3: Check ngrok Tunnel
```bash
# Check if ngrok is running
curl http://localhost:4040/api/tunnels
```

### 4. Common Error Messages

#### "Phone number is not whitelisted"
- Set `WHITELISTED_NUMBERS=["*"]` in your `.env` file for testing

#### "Webhook URL not accessible"
- Make sure ngrok is running
- Check that `WEBHOOK_BASE_URL` is set correctly
- Ensure the URL starts with `https://` (not `http://`)

#### "Call failed to initiate"
- Verify Twilio credentials
- Check phone number format (should be +1234567890)
- Ensure your Twilio account has sufficient credits

### 5. Testing Checklist

- [ ] Django server is running on port 8000
- [ ] ngrok tunnel is active and accessible
- [ ] `.env` file has correct Twilio credentials
- [ ] `WEBHOOK_BASE_URL` is set to ngrok URL
- [ ] Phone number is in correct format (+1234567890)
- [ ] Twilio account has sufficient credits
- [ ] Webhook endpoints are accessible via ngrok URL

### 6. Production Deployment

For production, replace ngrok with your actual domain:

```env
WEBHOOK_BASE_URL=https://yourdomain.com
```

### 7. Monitoring and Logs

Check these log files for debugging:
- `logs/django.log` - General application logs
- `logs/errors.log` - Error logs
- Console output - Debug print statements

### 8. Quick Test Script

Create a file called `test_twilio.py`:

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_webhook():
    webhook_url = os.getenv('WEBHOOK_BASE_URL')
    if not webhook_url:
        print("❌ WEBHOOK_BASE_URL not set")
        return
    
    test_url = f"{webhook_url}/api/webhook-test/"
    try:
        response = requests.get(test_url)
        print(f"✅ Webhook test successful: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")

if __name__ == "__main__":
    test_webhook()
```

Run it with: `python test_twilio.py`

### 9. Emergency Fallback

If webhooks are still not working, you can implement a polling mechanism:

```python
# In your views.py, add a status check endpoint
def check_call_status(request, call_sid):
    """Manually check call status from Twilio"""
    try:
        client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
        call = client.calls(call_sid).fetch()
        return Response({
            'status': call.status,
            'duration': call.duration,
            'recording_url': call.recording_url
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)
```

### 10. Support

If you're still having issues:
1. Check the Twilio console for call logs
2. Verify webhook delivery in Twilio console
3. Check your Django logs for any errors
4. Test with a simple TwiML response first
