# LuminaText Backend

FastAPI backend for audio/video transcription using **Deepgram API** (free tier available!) and **MongoDB** for history storage.

## Features

- Audio and video file transcription using Deepgram AI
- File size validation (configurable, default 100MB)
- MongoDB integration for transcription history
- CORS enabled for frontend integration
- Health check endpoint
- **100% FREE** - No OpenAI costs!

## Requirements

- Python 3.8+
- MongoDB (local or cloud like MongoDB Atlas)
- Deepgram API key (FREE tier available!)

## Why Deepgram?

- **FREE tier**: 45,000 minutes/month free transcription
- **Fast & accurate**: Industry-leading speech-to-text
- **No credit card required** for free tier
- **Nova-2 model**: Latest AI for best accuracy

## Installation

1. **Install dependencies**:
```bash
cd backend
pip install -r requirements.txt
```

2. **Set up MongoDB**:

**Option A: Local MongoDB**
```bash
# Install MongoDB locally
brew install mongodb-community  # macOS
# or
sudo apt-get install mongodb  # Linux

# Start MongoDB
mongod --dbpath /path/to/data
```

**Option B: MongoDB Atlas (Cloud - FREE)**
1. Go to [mongodb.com/atlas](https://www.mongodb.com/cloud/atlas)
2. Create free account
3. Create cluster (free M0 tier)
4. Get connection string

3. **Get Deepgram API Key (FREE)**:
1. Go to [console.deepgram.com](https://console.deepgram.com/)
2. Sign up (no credit card required)
3. Create API key
4. Get 45,000 minutes/month FREE!

4. **Create `.env` file**:
```bash
cp .env.example .env
```

Edit `.env`:
```env
PORT=8000
MONGODB_URI=mongodb://localhost:27017/luminatext
DEEPGRAM_API_KEY=your_deepgram_api_key_here
MAX_FILE_SIZE=104857600
```

## Running the Server

### Development
```bash
python main.py
```

Or using uvicorn:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Root
```
GET /
```
Returns API information and version

### Health Check
```
GET /api/health
```

Response:
```json
{
  "status": "healthy",
  "message": "API is running",
  "database": "connected"
}
```

### Transcribe Audio/Video
```
POST /api/transcribe
```

Request:
- Method: POST
- Content-Type: multipart/form-data
- Body: `file` (audio/video file)

Response:
```json
{
  "text": "Transcribed text here...",
  "fileName": "audio.mp3",
  "duration": "2m 30s",
  "fileSize": "5.23 MB",
  "date": "2025-11-07 12:34:56"
}
```

### Get Transcription History
```
GET /api/history?limit=10&skip=0
```

Response:
```json
{
  "transcriptions": [
    {
      "id": "507f1f77bcf86cd799439011",
      "text": "Full transcription text...",
      "fileName": "audio.mp3",
      "duration": "2m 30s",
      "fileSize": "5.23 MB",
      "date": "2025-11-07 12:34:56",
      "preview": "First 100 characters..."
    }
  ],
  "total": 42,
  "limit": 10,
  "skip": 0
}
```

### Delete Transcription
```
DELETE /api/history/{transcription_id}
```

Response:
```json
{
  "message": "Transcription deleted successfully"
}
```

## Supported File Formats
- MP3 (.mp3)
- WAV (.wav)
- MP4 (.mp4)
- M4A (.m4a)
- MPEG (.mpeg, .mpga)
- WEBM (.webm)
- OGG (.ogg)
- FLAC (.flac)
- OPUS (.opus)

## File Size Limit
Default: 100MB (configurable via `MAX_FILE_SIZE` env variable)

## Testing

Test the transcription API:
```bash
curl -X POST "http://localhost:8000/api/transcribe" \
  -F "file=@your-audio-file.mp3"
```

Test health endpoint:
```bash
curl "http://localhost:8000/api/health"
```

Get transcription history:
```bash
curl "http://localhost:8000/api/history?limit=5"
```

## Deployment

### Option 1: Railway.app (Recommended)

1. Create new project on Railway
2. Add MongoDB service (or connect to MongoDB Atlas)
3. Connect GitHub repository
4. Set root directory: `backend`
5. Add environment variables:
   - `DEEPGRAM_API_KEY`
   - `MONGODB_URI` (from Railway MongoDB or Atlas)
   - `MAX_FILE_SIZE=104857600`
6. Deploy!

### Option 2: Render.com

1. Create Web Service
2. Connect repository
3. Root directory: `backend`
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add environment variables
7. Add MongoDB (use MongoDB Atlas free tier)

### Option 3: Heroku

```bash
cd backend
heroku create luminatext-backend
heroku addons:create mongolab:sandbox  # Free MongoDB addon
heroku config:set DEEPGRAM_API_KEY=your-key
git push heroku main
```

### Option 4: Docker

Build:
```bash
docker build -t luminatext-backend .
```

Run:
```bash
docker run -p 8000:8000 \
  -e DEEPGRAM_API_KEY=your-key \
  -e MONGODB_URI=mongodb://host.docker.internal:27017/luminatext \
  luminatext-backend
```

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PORT` | Server port | 8000 | No |
| `MONGODB_URI` | MongoDB connection string | `mongodb://localhost:27017/luminatext` | Yes |
| `DEEPGRAM_API_KEY` | Deepgram API key | - | Yes |
| `MAX_FILE_SIZE` | Max upload size in bytes | 104857600 (100MB) | No |

## Free Tier Limits

### Deepgram
- **45,000 minutes/month FREE**
- No credit card required
- Perfect for personal projects and MVPs

Example usage:
- 1,500 x 30-minute files/month = FREE
- 90,000 x 30-second clips/month = FREE

### MongoDB Atlas
- **512MB storage FREE**
- Shared cluster
- Perfect for storing thousands of transcriptions

## Error Handling

HTTP Status Codes:
- `200`: Success
- `400`: Bad request (invalid file format, empty file)
- `413`: File too large
- `500`: Server error (API key missing, database error)

## CORS Configuration

Default: Allows all origins

For production, update `main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://luminatext.netlify.app",
        "https://your-custom-domain.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Database Schema

### Transcriptions Collection
```javascript
{
  _id: ObjectId,
  text: String,              // Full transcription text
  fileName: String,          // Original filename
  duration: String,          // Formatted duration (e.g., "2m 30s")
  fileSize: String,          // Formatted size (e.g., "5.23 MB")
  date: String,              // Formatted date
  createdAt: Date,           // MongoDB timestamp
  metadata: {
    duration_seconds: Number,
    file_size_bytes: Number,
    model: String,           // "nova-2"
    provider: String         // "deepgram"
  }
}
```

## Troubleshooting

### MongoDB Connection Error
- Check MongoDB is running: `mongosh`
- Verify connection string in `.env`
- For Atlas: whitelist your IP address

### Deepgram API Error
- Verify API key is correct
- Check you haven't exceeded free tier (45k min/month)
- Test key at [console.deepgram.com](https://console.deepgram.com/)

### File Upload Error
- Check file size < MAX_FILE_SIZE
- Verify file format is supported
- Ensure multipart/form-data is used

## Performance Tips

1. **Use MongoDB indexes** for faster queries:
```javascript
db.transcriptions.createIndex({ createdAt: -1 })
db.transcriptions.createIndex({ fileName: "text" })
```

2. **Increase workers** for production:
```bash
uvicorn main:app --workers 4
```

3. **Enable gzip compression** in production reverse proxy

## License

MIT

## Support

For issues:
- Deepgram: [support.deepgram.com](https://support.deepgram.com/)
- MongoDB: [docs.mongodb.com](https://docs.mongodb.com/)
- GitHub Issues: [Your repo issues page]

---

Built with ❤️ using Deepgram (FREE tier!) and MongoDB
