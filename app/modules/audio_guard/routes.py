from fastapi import APIRouter, File, UploadFile
from app.core.model_loader import ModelLoader
from app.core.activity_logger import ActivityLogger
import os

AUDIO_GUARD_URL = os.getenv("AUDIO_GUARD_URL", "http://localhost:8002/api/v1/analyze_audio")

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
from app.core.activity_logger import ActivityLogger

router = APIRouter()

@router.post("/detect-voice")
async def detect_deepfake(file: UploadFile = File(...)):
    """
    6. Deepfake Voice Scam Detection
    Expects audio file.
    """
    alerts = []
    risk = 0
    try:
        import httpx
        content = await file.read()
        
        # Forward request to Audio Guard Microservice
        async with httpx.AsyncClient(timeout=60.0) as client:
            files = {'file': (file.filename, content, file.content_type)}
            response = await client.post(
                AUDIO_GUARD_URL,
                files=files
            )
            response.raise_for_status()
            
            data = response.json()
            risk = data.get("risk_score", 0)
            alerts.extend(data.get("alerts", []))
            
    except Exception as e:
        print(f"Error calling Audio Microservice: {e}")
        alerts.append(f"Audio Scanner Offline: {str(e)}")
        
    ActivityLogger.log_activity(
        "Audio Guard",
        "audio",
        min(risk, 100),
        alerts
    )
        
    return {
        "filename": file.filename,
        "is_deepfake": risk > 50,
        "risk_score": min(risk, 100),
        "alerts": alerts
    }
