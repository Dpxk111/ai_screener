# Twilio Service and Webhook Implementation

## Overview

This document describes the rewritten Twilio service and webhook implementation for the AI Interview Screener. The new implementation provides a robust, multi-question interview flow with proper error handling and state management.

## Key Improvements

### 1. Multi-Question Interview Flow
- **Before**: Only handled the first question
- **After**: Supports complete interview flow with multiple questions
- **Features**: 
  - Automatic progression through questions
  - Proper state management
  - Completion handling

### 2. Robust Webhook Handling
- **Before**: Incomplete webhook implementation with missing imports
- **After**: Comprehensive webhook system with proper routing
- **Features**:
  - Call status webhooks
  - Recording response webhooks
  - Recording status webhooks
  - Proper error handling

### 3. Enhanced TwiML Generation
- **Before**: Basic TwiML for single question
- **After**: Dynamic TwiML generation for complete interview flow
- **Features**:
  - Welcome messages
  - Question progression
  - Completion messages
  - Error handling

## Architecture

### TwilioService Class

The `TwilioService` class handles all Twilio-related operations:

```python
class TwilioService:
    def __init__(self):
        # Initialize Twilio client with environment variables
        
    def initiate_call(self, interview_id, candidate_phone, questions):
        # Start the interview call
        
    def _create_interview_twiml(self, interview_id, question_number, questions):
        # Generate TwiML for interview flow
        
    def create_next_question_twiml(self, interview_id, question_number, questions):
        # Generate TwiML for next question
        
    def create_completion_twiml(self):
        # Generate completion TwiML
        
    def get_call_status(self, call_sid):
        # Get call status from Twilio
        
    def get_recording_url(self, recording_sid):
        # Get recording media URL
```

### Webhook Flow

1. **Call Initiation**: `TriggerInterviewView` creates interview and initiates call
2. **First Question**: TwiML asks first question and starts recording
3. **Recording Complete**: Webhook receives recording and processes response
4. **Next Question**: Generate TwiML for next question or completion
5. **Interview Complete**: Generate final results and recommendations

## Webhook Endpoints

### 1. Call Status Webhook
- **URL**: `/api/webhooks/call-status/`
- **Purpose**: Handle call completion, failure, or other status updates
- **Parameters**:
  - `CallSid`: Twilio call identifier
  - `CallStatus`: Status of the call (completed, failed, busy, etc.)
  - `CallDuration`: Duration of the call in seconds

### 2. Record Response Webhook
- **URL**: `/api/webhooks/record-response/`
- **Purpose**: Handle recording completion and process responses
- **Parameters**:
  - `RecordingUrl`: URL of the recorded audio
  - `RecordingSid`: Twilio recording identifier
  - `RecordingDuration`: Duration of the recording
  - `interview_id`: Interview identifier (from URL parameters)
  - `question_number`: Question number (from URL parameters)

### 3. Recording Status Webhook
- **URL**: `/api/webhooks/recording-status/`
- **Purpose**: Handle recording status updates
- **Parameters**:
  - `RecordingSid`: Twilio recording identifier
  - `RecordingStatus`: Status of the recording (completed, failed)

## Interview Flow

### 1. Interview Initiation
```python
# Create interview record
interview = Interview.objects.create(
    candidate=candidate,
    job_description=job_description,
    status='pending'
)

# Initiate Twilio call
twilio_service = TwilioService()
call_sid = twilio_service.initiate_call(
    str(interview.id),
    candidate.phone,
    job_description.questions
)
```

### 2. Question Progression
```python
# Generate TwiML for current question
twiml = twilio_service._create_interview_twiml(
    interview_id,
    question_number,
    questions
)
```

### 3. Response Processing
```python
# Save response
response = InterviewResponse.objects.create(
    interview=interview,
    question_number=question_number,
    question=question_text,
    audio_url=recording_url,
    transcript='Processing...'
)

# Start transcription
transcription_service = TranscriptionService()
transcript = transcription_service.transcribe_audio(recording_url)
response.transcript = transcript
response.save()

# Analyze response
openai_service = OpenAIService()
score, feedback = openai_service.analyze_response(
    response.question,
    response.transcript
)
response.score = score
response.feedback = feedback
response.save()
```

### 4. Interview Completion
```python
# Generate final results
final_result = openai_service.generate_final_recommendation(
    list(responses),
    resume_context
)

InterviewResult.objects.create(
    interview=interview,
    overall_score=final_result['overall_score'],
    recommendation=final_result['recommendation'],
    strengths=final_result['strengths'],
    areas_for_improvement=final_result['areas_for_improvement']
)
```

## Configuration

### Environment Variables

```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number

# Webhook Configuration
WEBHOOK_BASE_URL=https://your-domain.com

# Optional: Phone number whitelist (JSON array)
WHITELISTED_NUMBERS=["+1234567890", "+0987654321"]
```

### Webhook URL Structure

The webhook URLs are constructed as follows:
- Call Status: `{WEBHOOK_BASE_URL}/api/webhooks/call-status/`
- Record Response: `{WEBHOOK_BASE_URL}/api/webhooks/record-response/`
- Recording Status: `{WEBHOOK_BASE_URL}/api/webhooks/recording-status/`

## Error Handling

### 1. Call Failures
- **Busy**: Interview marked as failed
- **No Answer**: Interview marked as failed
- **Failed**: Interview marked as failed with error details

### 2. Recording Failures
- **Timeout**: Handle gracefully with retry logic
- **Network Issues**: Log errors and continue
- **Transcription Failures**: Mark as "Unable to transcribe"

### 3. Webhook Failures
- **Missing Parameters**: Return error response
- **Invalid Interview ID**: Return 404 error
- **Processing Errors**: Log errors and continue

## Testing

### Manual Testing

1. **Test Twilio Service**:
   ```bash
   python test_twilio_service.py
   ```

2. **Test Webhook Endpoints**:
   ```bash
   # Test webhook accessibility
   curl -X GET https://your-domain.com/api/webhook-test/
   
   # Test call status webhook
   curl -X POST https://your-domain.com/api/webhooks/call-status/ \
     -d "CallSid=test&CallStatus=completed"
   ```

3. **Test Interview Flow**:
   ```bash
   # Create test interview
   curl -X POST https://your-domain.com/api/trigger-interview/ \
     -H "X-API-Key: your_api_key" \
     -d '{"candidate_id": "uuid", "job_description_id": "uuid"}'
   ```

### Automated Testing

The `test_twilio_service.py` script includes comprehensive tests for:
- Twilio service initialization
- TwiML generation
- Webhook URL generation
- Interview flow logic
- Webhook parameter handling

## Monitoring and Debugging

### 1. Logging
All operations are logged with appropriate levels:
- `INFO`: Normal operations
- `WARNING`: Non-critical issues
- `ERROR`: Critical failures

### 2. Debug Endpoints
- `/api/twilio/debug/`: Check Twilio configuration
- `/api/webhook-test/`: Test webhook accessibility
- `/api/audio-availability/`: Check audio file availability

### 3. Interview Status Tracking
- Monitor interview progress via `/api/interviews/{id}/flow/`
- Check response status and transcription progress
- View final results via `/api/interviews/{id}/results/`

## Troubleshooting

### Common Issues

1. **Webhook Not Receiving Calls**
   - Check `WEBHOOK_BASE_URL` configuration
   - Ensure webhook URLs are publicly accessible
   - Verify Twilio webhook configuration

2. **Recording Not Available**
   - Check recording status via Twilio API
   - Verify recording permissions
   - Check media URL accessibility

3. **Transcription Failures**
   - Verify OpenAI API key
   - Check audio file format and size
   - Review transcription service logs

4. **Interview Flow Issues**
   - Check question progression logic
   - Verify webhook parameter passing
   - Review interview status updates

### Debug Commands

```bash
# Check Twilio configuration
curl -X GET https://your-domain.com/api/twilio/debug/

# List all Twilio recordings
curl -X GET https://your-domain.com/api/twilio/recordings/

# Check interview flow status
curl -X GET https://your-domain.com/api/interviews/{id}/flow/

# Manually trigger next question
curl -X POST https://your-domain.com/api/interviews/{id}/flow/
```

## Migration from Old Implementation

### Breaking Changes
1. Webhook URL structure changed
2. TwiML generation logic updated
3. Interview flow state management improved

### Migration Steps
1. Update environment variables
2. Deploy new code
3. Test webhook endpoints
4. Monitor interview flow
5. Update any custom integrations

## Future Enhancements

### Planned Features
1. **Real-time Interview Monitoring**: WebSocket-based live updates
2. **Interview Templates**: Predefined question sets
3. **Advanced Analytics**: Detailed interview performance metrics
4. **Multi-language Support**: Internationalization for interviews
5. **Video Integration**: Support for video interviews

### Performance Optimizations
1. **Async Processing**: Background task processing
2. **Caching**: Redis-based response caching
3. **CDN Integration**: Audio file delivery optimization
4. **Database Optimization**: Query optimization and indexing

## Support

For issues or questions about the Twilio service implementation:
1. Check the logs for error details
2. Use the debug endpoints for configuration verification
3. Review this documentation for troubleshooting steps
4. Contact the development team for additional support
