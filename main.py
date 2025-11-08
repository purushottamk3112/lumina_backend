from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
import os
from datetime import datetime
import tempfile
from pathlib import Path
from typing import Optional, List
import traceback
from bson import ObjectId

app = FastAPI(title="LuminaText Transcription API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mongodb_client = None
db = None
deepgram_client = None

@app.on_event("startup")
async def startup_db_client():
    global mongodb_client, db, deepgram_client
    
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/luminatext")
    mongodb_client = AsyncIOMotorClient(mongodb_uri)
    db = mongodb_client.get_default_database()
    
    deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
    if deepgram_api_key:
        deepgram_client = DeepgramClient(deepgram_api_key)
        print("Deepgram client initialized successfully")

@app.on_event("shutdown")
async def shutdown_db_client():
    if mongodb_client:
        mongodb_client.close()

def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "Unknown"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"

def format_file_size(bytes_size: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

@app.get("/")
async def root():
    return {
        "message": "LuminaText Transcription API",
        "version": "2.0.0",
        "provider": "Deepgram",
        "endpoints": {
            "/api/health": "Health check",
            "/api/transcribe": "Transcribe audio/video files",
            "/api/history": "Get transcription history"
        }
    }

@app.get("/api/health")
async def health_check():
    try:
        deepgram_key = os.getenv("DEEPGRAM_API_KEY")
        mongodb_uri = os.getenv("MONGODB_URI")
        
        if not deepgram_key:
            return {
                "status": "unhealthy",
                "message": "DEEPGRAM_API_KEY not configured"
            }
        
        if not mongodb_uri:
            return {
                "status": "unhealthy", 
                "message": "MONGODB_URI not configured"
            }
            
        if db:
            await db.command("ping")
            
        return {
            "status": "healthy",
            "message": "API is running",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": str(e)
        }

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 104857600))
    ALLOWED_EXTENSIONS = {'.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm', '.ogg', '.flac', '.opus'}
    
    try:
        if not deepgram_client:
            raise HTTPException(
                status_code=500,
                detail="Deepgram API not configured. Please set DEEPGRAM_API_KEY."
            )
        
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        content = await file.read()
        file_size = len(content)
        
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds {format_file_size(MAX_FILE_SIZE)} limit"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty file uploaded"
            )
        
        # CORRECT: Use the proper Deepgram SDK v3.2.0 API structure for file transcription
        # Based on official documentation: deepgram.listen.v1.media.transcribe_file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Open the temporary file and transcribe it
            with open(temp_file_path, "rb") as audio_file:
                response = deepgram_client.listen.v1.media.transcribe_file(
                    request=audio_file.read(),
                    model="nova-2",
                    smart_format=True,
                    punctuate=True,
                    paragraphs=True,
                    utterances=True,
                )
            
            result = response.to_dict()
            
            transcribed_text = result['results']['channels'][0]['alternatives'][0]['transcript']
            duration = result['metadata'].get('duration', None)
            
            transcription_data = {
                "text": transcribed_text,
                "fileName": file.filename,
                "duration": format_duration(duration),
                "fileSize": format_file_size(file_size),
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "createdAt": datetime.now(),
                "metadata": {
                    "duration_seconds": duration,
                    "file_size_bytes": file_size,
                    "model": "nova-2",
                    "provider": "deepgram"
                }
            }
            
            if db:
                try:
                    await db.transcriptions.insert_one(transcription_data.copy())
                except Exception as e:
                    print(f"Failed to save to database: {e}")
            
            return {
                "text": transcription_data["text"],
                "fileName": transcription_data["fileName"],
                "duration": transcription_data["duration"],
                "fileSize": transcription_data["fileSize"],
                "date": transcription_data["date"]
            }
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during transcription: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Deepgram client type: {type(deepgram_client)}")
        print(f"Available methods: {dir(deepgram_client) if deepgram_client else 'None'}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error transcribing file: {str(e)}"
        )

@app.get("/api/history")
async def get_history(limit: int = 10, skip: int = 0):
    try:
        if not db:
            raise HTTPException(
                status_code=500,
                detail="Database not configured"
            )
        
        cursor = db.transcriptions.find().sort("createdAt", -1).skip(skip).limit(limit)
        transcriptions = await cursor.to_list(length=limit)
        
        for item in transcriptions:
            item["_id"] = str(item["_id"])
            item["id"] = item.pop("_id")
            if "metadata" in item:
                del item["metadata"]
            if "createdAt" in item:
                del item["createdAt"]
            
            item["preview"] = item["text"][:100] + "..." if len(item["text"]) > 100 else item["text"]
        
        total_count = await db.transcriptions.count_documents({})
        
        return {
            "transcriptions": transcriptions,
            "total": total_count,
            "limit": limit,
            "skip": skip
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching history: {str(e)}"
        )

@app.delete("/api/history/{transcription_id}")
async def delete_transcription(transcription_id: str):
    try:
        if not db:
            raise HTTPException(
                status_code=500,
                detail="Database not configured"
            )
        
        result = await db.transcriptions.delete_one({"_id": ObjectId(transcription_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Transcription not found"
            )
        
        return {"message": "Transcription deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting transcription: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting transcription: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)