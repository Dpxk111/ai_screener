# Twilio Audio Recording APIs

This document describes the APIs for managing and transcribing Twilio audio recordings.

## API Authentication

All APIs require authentication using an API key. Include the API key in the request headers:

```
X-API-Key: your_api_key_here
```

Or as a query parameter:

```
?api_key=your_api_key_here
```

## 1. List All Twilio Recordings

**Endpoint:** `GET /api/twilio/recordings/`

**Description:** Retrieves all available Twilio recordings with detailed information including media accessibility status.

### Query Parameters

- `limit` (optional): Number of recordings to return (default: 50, max: 100)
- `status` (optional): Filter by recording status (`completed`, `in-progress`, `failed`)
- `date_created_after` (optional): Filter recordings created after this date (ISO format)
- `date_created_before` (optional): Filter recordings created before this date (ISO format)

### Example Request

```bash
curl -X GET "https://your-domain.com/api/twilio/recordings/?limit=20&status=completed" \
  -H "X-API-Key: your_api_key_here"
```

### Example Response

```json
{
  "total_recordings": 20,
  "query_parameters": {
    "limit": "20",
    "status": "completed",
    "date_created_after": null,
    "date_created_before": null
  },
  "recordings": [
    {
      "sid": "RE1234567890abcdef",
      "account_sid": "AC1234567890abcdef",
      "call_sid": "CA1234567890abcdef",
      "duration": 45,
      "status": "completed",
      "channels": 1,
      "source": "RecordVerb",
      "error_code": null,
      "uri": "/2010-04-01/Accounts/AC1234567890abcdef/Recordings/RE1234567890abcdef.json",
      "media_location": null,
      "media_url": "https://api.twilio.com/2010-04-01/Accounts/AC1234567890abcdef/Recordings/RE1234567890abcdef.mp3",
      "media_accessible": true,
      "media_status_code": 200,
      "date_created": "2024-01-15T10:30:00Z",
      "date_updated": "2024-01-15T10:30:30Z",
      "start_time": "2024-01-15T10:30:00Z",
      "price": "0.0025",
      "price_unit": "USD",
      "track": "both"
    }
  ],
  "summary": {
    "completed": 18,
    "in_progress": 1,
    "failed": 1,
    "accessible_media": 17,
    "inaccessible_media": 1
  }
}
```

### Response Fields

- `total_recordings`: Total number of recordings returned
- `query_parameters`: The parameters used for the query
- `recordings`: Array of recording objects
- `summary`: Summary statistics of the recordings

#### Recording Object Fields

- `sid`: Twilio Recording SID
- `account_sid`: Twilio Account SID
- `call_sid`: Associated Call SID
- `duration`: Recording duration in seconds
- `status`: Recording status (`completed`, `in-progress`, `failed`)
- `channels`: Number of audio channels
- `source`: How the recording was created
- `error_code`: Error code if recording failed
- `uri`: Twilio API URI for the recording
- `media_location`: Alternative media location URL
- `media_url`: Direct URL to the audio file
- `media_accessible`: Whether the media URL is accessible
- `media_status_code`: HTTP status code when testing media URL
- `date_created`: When the recording was created
- `date_updated`: When the recording was last updated
- `start_time`: When the recording started
- `price`: Cost of the recording
- `price_unit`: Currency of the price
- `track`: Audio track type

## 2. Get Transcript for Audio Recording

**Endpoint:** `POST /api/twilio/transcript/`

**Description:** Transcribes a specific Twilio audio recording using OpenAI Whisper.

### Request Body

You can provide either `recording_sid` or `audio_url`:

```json
{
  "recording_sid": "RE1234567890abcdef"
}
```

OR

```json
{
  "audio_url": "https://api.twilio.com/2010-04-01/Accounts/AC1234567890abcdef/Recordings/RE1234567890abcdef.mp3"
}
```

### Example Request

```bash
curl -X POST "https://your-domain.com/api/twilio/transcript/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{
    "recording_sid": "RE1234567890abcdef"
  }'
```

### Example Response

```json
{
  "recording_sid": "RE1234567890abcdef",
  "audio_url": "https://api.twilio.com/2010-04-01/Accounts/AC1234567890abcdef/Recordings/RE1234567890abcdef.mp3",
  "transcript": "Hello, this is my response to the interview question. I have experience in software development and I'm excited about this opportunity.",
  "recording_details": {
    "status": "completed",
    "duration": 45,
    "date_created": "2024-01-15T10:30:00Z",
    "call_sid": "CA1234567890abcdef"
  },
  "status": "completed",
  "timestamp": "2024-01-15T10:35:00Z"
}
```

### Response Fields

- `recording_sid`: The Twilio Recording SID
- `audio_url`: The URL used for transcription
- `transcript`: The transcribed text from the audio
- `recording_details`: Additional recording information (only when using recording_sid)
- `status`: Status of the transcription process
- `timestamp`: When the transcription was completed

### Error Responses

#### Missing Parameters
```json
{
  "error": "Either recording_sid or audio_url is required"
}
```

#### Recording Not Found
```json
{
  "error": "Failed to fetch recording details: Recording not found"
}
```

#### Transcription Failed
```json
{
  "error": "Unexpected error occurred",
  "details": "Transcription failed: Recording not completed (status=in-progress)"
}
```

## Usage Examples

### 1. List Recent Completed Recordings

```bash
curl -X GET "https://your-domain.com/api/twilio/recordings/?limit=10&status=completed" \
  -H "X-API-Key: your_api_key_here"
```

### 2. Get Transcript for a Specific Recording

```bash
curl -X POST "https://your-domain.com/api/twilio/transcript/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{
    "recording_sid": "RE1234567890abcdef"
  }'
```

### 3. Transcribe Using Direct Audio URL

```bash
curl -X POST "https://your-domain.com/api/twilio/transcript/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key_here" \
  -d '{
    "audio_url": "https://api.twilio.com/2010-04-01/Accounts/AC1234567890abcdef/Recordings/RE1234567890abcdef.mp3"
  }'
```

### 4. Filter Recordings by Date Range

```bash
curl -X GET "https://your-domain.com/api/twilio/recordings/?date_created_after=2024-01-01&date_created_before=2024-01-31" \
  -H "X-API-Key: your_api_key_here"
```

## Error Handling

### Common HTTP Status Codes

- `200`: Success
- `400`: Bad Request (missing parameters, invalid data)
- `401`: Unauthorized (invalid or missing API key)
- `500`: Internal Server Error (Twilio API issues, transcription failures)

### Troubleshooting

1. **Recording Not Found**: Ensure the recording SID is correct and the recording exists
2. **Media Not Accessible**: Some recordings may not be immediately available after creation
3. **Transcription Failures**: Check if the audio file is valid and not corrupted
4. **Rate Limiting**: Twilio and OpenAI APIs have rate limits; implement retry logic if needed

## Rate Limits and Costs

- **Twilio API**: Subject to Twilio's rate limits
- **OpenAI Whisper**: Subject to OpenAI's rate limits and costs
- **Transcription Cost**: Approximately $0.006 per minute of audio

## Security Considerations

- API keys should be kept secure and not exposed in client-side code
- Consider implementing rate limiting on your endpoints
- Validate all input parameters before processing
- Log API usage for monitoring and debugging

## Integration Notes

- Recordings may take a few seconds to become available after creation
- Transcription quality depends on audio quality and clarity
- Consider implementing caching for frequently accessed transcripts
- Monitor API usage and costs regularly
