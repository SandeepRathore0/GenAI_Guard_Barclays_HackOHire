from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.pii_scrubber import PIIScrubber
from app.core.activity_logger import ActivityLogger
import httpx
import os

router = APIRouter()

class TextAnalysisRequest(BaseModel):
    text: str
    check_type: str  # 'phishing', 'credentials', 'injection'

LLM_GUARD_URL = os.getenv("LLM_GUARD_URL", "http://localhost:8001/api/v1/scan")

@router.post("/analyze")
async def analyze_text(request: TextAnalysisRequest):
    """
    Analyzes text by forwarding it to the standalone LLM Guard Microservice.
    """
    try:
        # PRIVACY FIRST: Anonymize data before any logging/storage
        scrubbed_text = PIIScrubber.scrub(request.text)
        print(f"Processing secure request: {scrubbed_text[:50]}...") # Log only scrubbed
    except Exception:
        pass

    try:
        # Forward request to LLM Microservice
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                LLM_GUARD_URL, 
                json={"text": request.text, "check_type": request.check_type}
            )
            response.raise_for_status()
            
            result = response.json()
            risk_score = result.get("risk_score", 0)
            alerts = result.get("alerts", [])
            
    except Exception as e:
        print(f"Error calling LLM Microservice: {e}")
        # Graceful Degradation: return safe by default but log an alert
        risk_score = 0
        alerts = [f"LLM Scanner Offline: {str(e)}"]

    # Calculate final status
    final_status = "SAFE" if risk_score < 50 else "THREAT"
    
    # Log the activity
    ActivityLogger.log_activity(
        "Text Guard",
        request.check_type,
        min(risk_score, 100),
        alerts
    )

    return {
        "risk_score": min(risk_score, 100),
        "alerts": alerts,
        "status": final_status
    }
