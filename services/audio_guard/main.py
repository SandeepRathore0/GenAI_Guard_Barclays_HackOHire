from fastapi import FastAPI, UploadFile, File, HTTPException
import os
import shutil
import uuid
import sys

# Add core to sys.path so model and inference imports work natively
sys.path.append(os.path.join(os.path.dirname(__file__), "core"))
from inference import AudioDeepfakeDetector

app = FastAPI(title="Audio Guard Microservice")

BASE_DIR = os.path.dirname(__file__)
CORE_DIR = os.path.join(BASE_DIR, "core")

try:
    print("Initializing AudioDeepfakeDetector...")
    detector = AudioDeepfakeDetector(
        model_dir=os.path.join(CORE_DIR, "models", "wavlm-base"),
        checkpoint_path=os.path.join(CORE_DIR, "output", "2_best_model_FineTuned.pth")
    )
except Exception as e:
    print(f"Warning: Failed to load model on startup. Check weights: {e}")
    detector = None

@app.post("/api/v1/analyze_audio")
async def analyze_audio(file: UploadFile = File(...)):
    if detector is None:
        return {"risk_score": 0, "alerts": ["Detector model not initialized. Missing checkpoint files?"]}
    
    temp_path = f"temp_{uuid.uuid4()}.wav"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        result = detector.predict(temp_path)
        
        is_real = result['is_real']
        confidence = result['overall_confidence_percent']
        
        # Risk score is defined as the likelihood of being a deepfake
        risk_score = (100 - confidence) if is_real else confidence
        
        alerts = []
        if risk_score > 50:
            alerts.append(f"AI/Deepfake Audio Detected (Confidence: {confidence:.2f}%)")
        else:
            alerts.append(f"Human Voice Detected (Confidence: {confidence:.2f}%)")
            
        # The user requested segment details (batches of 5 sec)
        if result.get("segment_count", 0) > 1:
            alerts.append(f"Audio analyzed in {result['segment_count']} x 5-second segments.")
            for seg in result['segment_details']:
                seg_risk = (100 - seg['confidence_percent']) if seg['is_real'] else seg['confidence_percent']
                status_str = "Deepfake" if seg_risk > 50 else "Human"
                alerts.append(f"Segment {seg['time_range']}: {status_str} (Risk: {seg_risk:.2f}%)")
        
        return {
            "risk_score": round(risk_score, 2),
            "alerts": alerts,
            "segment_details": result.get("segment_details", [])
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"risk_score": 0, "alerts": [f"Audio processing error: {str(e)}"]}
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
