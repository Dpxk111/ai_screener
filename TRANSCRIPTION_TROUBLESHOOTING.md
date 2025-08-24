# Transcription Troubleshooting Guide

## Common Transcription Issues and Solutions

### 1. Webhook Not Triggering (Most Common)

**Problem**: Transcription service is never called because webhooks aren't being triggered.

**Symptoms**:
- Calls are initiated successfully
- No transcription attempts in logs
- No webhook callbacks received

**Solutions**:
1. **Check webhook URLs in Twilio console**
2. **Verify webhook endpoints are accessible**
3. **Use manual transcription as fallback**

### 2. Audio Download Issues

**Problem**: Cannot download audio file from Twilio.

**Common Causes**:
- Invalid recording SID
- Expired recording URL
- Authentication issues
- Network connectivity problems

**Solutions**:
1. **Verify recording SID format** (should start with RE and be 34 characters)
2. **Check Twilio credentials**
3. **Increase timeout values**
4. **Use Twilio client instead of direct download**

### 3. OpenAI Whisper Issues

**Problem**: Transcription fails at OpenAI Whisper step.

**Common Causes**:
- Invalid audio format
- File too large
- OpenAI API issues
- Rate limiting

**Solutions**:
1. **Ensure audio is in supported format** (MP3, WAV, M4A, etc.)
2. **Check file size** (should be under 25MB)
3. **Verify OpenAI API key**
4. **Check OpenAI service status**

## Testing Steps

### Step 1: Test Transcription Service Directly

```bash
python test_transcription.py
```

Choose option 1 and provide a Twilio recording URL.

### Step 2: Test via API Endpoint

```bash
curl -X POST "http://localhost:8000/api/transcription-test/" \
  -H "Content-Type: application/json" \
  -d '{"audio_url": "YOUR_TWILIO_RECORDING_URL"}'
```

### Step 3: Test Manual Transcription

```bash
curl -X POST "http://localhost:8000/api/interviews/{INTERVIEW_ID}/transcribe/" \
  -H "X-API-Key: YOUR_API_KEY"
```

## Debugging Tools

### 1. Check Recording Details

```python
from twilio.rest import Client
import os

client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))

# Get recording details
recording = client.recordings('RE_RECORDING_SID').fetch()
print(f"Recording SID: {recording.sid}")
print(f"Duration: {recording.duration}")
print(f"Status: {recording.status}")
print(f"URI: {recording.uri}")
```

### 2. Test Audio Download

```python
import requests

# Download audio file
response = requests.get(
    f"https://api.twilio.com{recording.uri}.mp3",
    auth=(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN')),
    timeout=60
)

print(f"Status: {response.status_code}")
print(f"Size: {len(response.content)} bytes")
```

### 3. Test OpenAI Whisper

```python
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Test with a small audio file
with open("test_audio.mp3", "rb") as audio_file:
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="text"
    )
    print(f"Transcript: {transcript}")
```

## Environment Variables

Make sure these are set correctly:

```env
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Webhook Configuration
WEBHOOK_BASE_URL=https://your-domain.com
```

## Common Error Messages

### "Could not extract recording SID from URL"
- Check URL format
- Ensure URL contains a valid recording SID
- Verify URL is from Twilio

### "Failed to fetch recording"
- Check Twilio credentials
- Verify recording SID exists
- Check recording status

### "Failed to download audio"
- Check network connectivity
- Verify authentication
- Check file permissions

### "OpenAI transcription failed"
- Check OpenAI API key
- Verify audio format
- Check file size
- Monitor rate limits

## Manual Transcription Workflow

If webhooks aren't working, use manual transcription:

1. **Get interview ID** from your application
2. **Call manual transcription endpoint**:
   ```bash
   POST /api/interviews/{interview_id}/transcribe/
   ```
3. **Check results** in the response
4. **Review any errors** and fix them

## Production Checklist

- [ ] Webhook URLs are publicly accessible
- [ ] Twilio credentials are valid
- [ ] OpenAI API key is valid
- [ ] Audio files are in supported format
- [ ] File size limits are respected
- [ ] Error handling is implemented
- [ ] Logging is configured
- [ ] Manual transcription fallback is available

## Monitoring

Check these logs for transcription issues:

- `logs/django.log` - General application logs
- `logs/errors.log` - Error logs
- Console output - Debug print statements

## Emergency Fixes

### 1. Immediate Transcription Test

```python
# Quick test script
import os
from interviews.services import TranscriptionService

service = TranscriptionService()
result = service.transcribe_audio("YOUR_RECORDING_URL")
print(result)
```

### 2. Batch Transcription

```python
# Transcribe all pending responses
from interviews.models import InterviewResponse

pending = InterviewResponse.objects.filter(
    transcript__in=['Processing...', 'Unable to transcribe audio']
)

for response in pending:
    if response.audio_url:
        service = TranscriptionService()
        transcript = service.transcribe_audio(response.audio_url)
        if not transcript.startswith('Transcription failed:'):
            response.transcript = transcript
            response.save()
```

### 3. Alternative Transcription Service

If OpenAI Whisper fails, consider:
- Google Speech-to-Text
- Amazon Transcribe
- Azure Speech Services
- Local Whisper models

## Support

If you're still having issues:

1. **Check Twilio console** for recording details
2. **Verify webhook delivery** in Twilio console
3. **Test with a known good audio file**
4. **Check OpenAI service status**
5. **Review all error logs**
6. **Use manual transcription as temporary solution**
