# 🎤 Advanced Speech-to-Text API

A comprehensive, production-ready REST API for speech recognition with multiple advanced features. Built with Flask and powered by Google Speech Recognition.

## ✨ Features

- **Multi-Format Support**: WAV, MP3, MP4, AVI, MOV, FLAC, M4A, OGG
- **Asynchronous Processing**: Handle large files without blocking
- **Base64 Audio Support**: Direct audio data transcription
- **Multi-Language Recognition**: 14+ languages supported
- **Real-time Progress Tracking**: Monitor transcription progress
- **Transcription History**: Keep track of all processed files
- **Audio Analysis**: Get detailed audio file information
- **Export Capabilities**: Download transcription history
- **RESTful API**: Clean, well-documented endpoints
- **Production Ready**: CORS support, error handling, logging

## 🚀 Quick Start

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd speech-to-text-api
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Install FFmpeg** (required for audio conversion)
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows (using Chocolatey)
choco install ffmpeg
```

4. **Run the API**
```bash
python app.py
```

The API will be available at `http://localhost:5000`

## 📖 API Documentation

### Base URL
```
http://localhost:5000
```

### Endpoints

#### 1. **GET /** - API Information
Get API overview and available endpoints.

**Response:**
```json
{
  "name": "Advanced Speech-to-Text API",
  "version": "2.0.0",
  "description": "A comprehensive speech recognition API",
  "endpoints": {...},
  "features": [...]
}
```

#### 2. **POST /transcribe** - Synchronous Transcription
Upload and transcribe audio file synchronously.

**Parameters:**
- `file`: Audio file (multipart/form-data)
- `language`: Language code (optional, default: 'id-ID')

**Example:**
```bash
curl -X POST \
  -F "file=@audio.mp3" \
  -F "language=en-US" \
  http://localhost:5000/transcribe
```

**Response:**
```json
{
  "success": true,
  "text": "Hello, this is a transcription example.",
  "language": "en-US",
  "confidence": 0.95,
  "audio_info": {
    "duration": 10.5,
    "channels": 2,
    "sample_rate": 44100,
    "format": "mp3"
  },
  "word_count": 6,
  "character_count": 42,
  "timestamp": "2025-06-19T10:30:00"
}
```

#### 3. **POST /transcribe/async** - Asynchronous Transcription
Start asynchronous transcription for large files.

**Parameters:**
- `file`: Audio file (multipart/form-data)
- `language`: Language code (optional, default: 'id-ID')

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "queued",
  "message": "Transcription job started"
}
```

#### 4. **GET /job/{job_id}** - Check Job Status
Get status and results of asynchronous transcription.

**Response:**
```json
{
  "id": "job-uuid",
  "status": "completed",
  "progress": 100,
  "filename": "audio.mp3",
  "language": "en-US",
  "success": true,
  "text": "Transcribed text here...",
  "created_at": "2025-06-19T10:30:00"
}
```

**Status Values:**
- `queued`: Job is waiting to be processed
- `processing`: Currently transcribing
- `completed`: Successfully completed
- `failed`: Processing failed

#### 5. **POST /transcribe/base64** - Base64 Audio Transcription
Transcribe base64 encoded audio data.

**Request Body:**
```json
{
  "audio": "base64-encoded-audio-data",
  "language": "en-US"
}
```

#### 6. **GET /languages** - Supported Languages
Get list of supported languages.

**Response:**
```json
{
  "languages": {
    "id-ID": "Indonesian",
    "en-US": "English (US)",
    "en-GB": "English (UK)",
    "es-ES": "Spanish",
    "fr-FR": "French",
    ...
  },
  "count": 14
}
```

#### 7. **GET /history** - Transcription History
Get paginated transcription history.

**Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 10)

**Response:**
```json
{
  "history": [...],
  "total": 25,
  "page": 1,
  "per_page": 10,
  "total_pages": 3
}
```

#### 8. **GET /stats** - API Statistics
Get comprehensive API usage statistics.

**Response:**
```json
{
  "total_transcriptions": 150,
  "successful_transcriptions": 142,
  "success_rate": 94.67,
  "language_usage": {
    "en-US": 85,
    "id-ID": 45,
    "es-ES": 20
  },
  "active_jobs": 3,
  "supported_languages": 14,
  "supported_formats": ["wav", "mp3", "mp4", ...]
}
```

#### 9. **GET /export/history** - Export History
Download transcription history as JSON file.

#### 10. **GET /health** - Health Check
Check API health status.

## 🌍 Supported Languages

| Code | Language |
|------|----------|
| id-ID | Indonesian |
| en-US | English (US) |
| en-GB | English (UK) |
| es-ES | Spanish |
| fr-FR | French |
| de-DE | German |
| ja-JP | Japanese |
| ko-KR | Korean |
| zh-CN | Chinese (Simplified) |
| pt-BR | Portuguese (Brazil) |
| ru-RU | Russian |
| ar-SA | Arabic |
| hi-IN | Hindi |
| th-TH | Thai |

## 🔧 Configuration

### Environment Variables
Create a `.env` file:

```env
FLASK_ENV=development
UPLOAD_FOLDER=uploads
OUTPUT_FOLDER=outputs
MAX_FILE_SIZE=104857600  # 100MB
API_HOST=0.0.0.0
API_PORT=5000
```

### Production Deployment

#### Using Gunicorn
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

#### Using Docker
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## 🧪 Testing

### Test with cURL

**Basic transcription:**
```bash
curl -X POST \
  -F "file=@test_audio.wav" \
  -F "language=en-US" \
  http://localhost:5000/transcribe
```

**Async transcription:**
```bash
# Start job
curl -X POST \
  -F "file=@large_audio.mp3" \
  -F "language=id-ID" \
  http://localhost:5000/transcribe/async

# Check status
curl http://localhost:5000/job/your-job-id
```

**Base64 transcription:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"audio": "base64_audio_data", "language": "en-US"}' \
  http://localhost:5000/transcribe/base64
```

### Python Client Example

```python
import requests
import base64

# Upload file transcription
with open('audio.wav', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/transcribe',
        files={'file': f},
        data={'language': 'en-US'}
    )
    print(response.json())

# Base64 transcription
with open('audio.wav', 'rb') as f:
    audio_b64 = base64.b64encode(f.read()).decode()
    
response = requests.post(
    'http://localhost:5000/transcribe/base64',
    json={'audio': audio_b64, 'language': 'en-US'}
)
print(response.json())
```

### JavaScript Client Example

```javascript
// File upload transcription
const formData = new FormData();
formData.append('file', audioFile);
formData.append('language', 'en-US');

fetch('http://localhost:5000/transcribe', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));

// Async transcription with status polling
async function transcribeAsync(audioFile) {
    const formData = new FormData();
    formData.append('file', audioFile);
    
    // Start job
    const jobResponse = await fetch('http://localhost:5000/transcribe/async', {
        method: 'POST',
        body: formData
    });
    const job = await jobResponse.json();
    
    // Poll status
    while (true) {
        const statusResponse = await fetch(`http://localhost:5000/job/${job.job_id}`);
        const status = await statusResponse.json();
        
        if (status.status === 'completed') {
            return status;
        } else if (status.status === 'failed') {
            throw new Error(status.error);
        }
        
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
}
```

## 🚨 Error Handling

The API returns appropriate HTTP status codes and error messages:

- **400 Bad Request**: Invalid input or missing parameters
- **404 Not Found**: Resource not found (e.g., job ID)
- **413 Payload Too Large**: File exceeds size limit
- **415 Unsupported Media Type**: Invalid file format
- **500 Internal Server Error**: Server processing error

**Error Response Format:**
```json
{
  "error": "Description of the error",
  "timestamp": "2025-06-19T10:30:00"
}
```

## 📊 Performance Considerations

- **File Size Limit**: 100MB per file
- **Concurrent Jobs**: Handled via threading
- **Memory Usage**: Files are processed and cleaned up automatically
- **Rate Limiting**: Consider implementing for production use
- **Caching**: Results are stored in memory (consider Redis for production)

## 🔒 Security

- File type validation
- Secure filename handling
- Input sanitization
- Error message sanitization
- CORS configuration

## 🛠️ Development

### Project Structure
```
speech-to-text-api/
├── app.py              # Main API application
├── requirements.txt    # Python dependencies  
├── README.md          # This documentation
├── uploads/           # Temporary upload directory
├── outputs/           # Export files directory
└── tests/             # Test files (create this)
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🤝 Support

For support, please open an issue on GitHub or contact the development team.

---

**Built with ❤️ for your portfolio project**