from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.config import settings
from app.core.model_loader import ModelLoader
from app.core.activity_logger import ActivityLogger
import httpx
import os

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    shield_enabled: bool = True

LLM_GUARD_URL = os.getenv("LLM_GUARD_URL", "http://localhost:8001/api/v1/scan")

async def check_prompt_security(text: str) -> dict:
    """Interacts with the LLM Microservice to determine if a prompt is malicious before passing it to the LLM"""
    alerts = []
    risk_score = 0
    is_blocked = False
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                LLM_GUARD_URL, 
                json={"text": text, "check_type": "injection"}
            )
            response.raise_for_status()
            
            result = response.json()
            print(f"[DEBUG] Llama Response: {result}")
            risk_score = result.get("risk_score", 0)
            if "alerts" in result and result["alerts"]:
                alerts.extend(result["alerts"])
    except Exception as e:
        print(f"Error calling LLM Microservice in secure chat: {e}")
        alerts.append(f"LLM Scanner Offline/Error: {e}")
        risk_score = 100  # Fail securely if offline

    if risk_score >= 40:
        is_blocked = True
        
    return {
        "is_blocked": is_blocked,
        "risk_score": min(risk_score, 100),
        "alerts": alerts
    }

@router.post("/chat")
async def secure_chat(request: ChatRequest):
    """
    Acts as an interceptor between the user and an LLM.
    Blocks the prompt if malicious intent is detected.
    """
    prompt = request.message
    
    if request.shield_enabled:
        # Run the Guard Interceptor
        security_check = await check_prompt_security(prompt)
        
        ActivityLogger.log_activity(
            "Secure Chat Interceptor",
            "chat_prompt",
            security_check["risk_score"],
            security_check["alerts"]
        )
        
        if security_check["is_blocked"]:
            return {
                "status": "BLOCKED",
                "reason": security_check["alerts"],
                "response": "GenAI Guard Interceptor: This prompt has been blocked due to security policies."
            }
    else:
        # Bypass the shield
        ActivityLogger.log_activity(
            "Secure Chat Interceptor",
            "chat_prompt_bypassed",
            0,
            ["Shield Disabled"]
        )
    # Mock LLM Response if Safe (In a real app, send to OpenAI/Anthropic/Local LLM here)
    mock_responses = {
        "hello": "Hello! How can I help you today?",
        "weather": "The isolated environment of this application does not have access to live weather data.",
        "who are you": "I am a helpful AI assistant protected by GenAI Guard."
    }
    
    # Simple keyword response for demo
    reply = "I understand what you're saying, but I'm just a demo answering safe prompts! (Prompt was securely passed)"
    for k, v in mock_responses.items():
        if k in prompt.lower():
            reply = v
            break
            
    return {
        "status": "SAFE",
        "response": reply
    }
