from fastapi import APIRouter
from pydantic import BaseModel
import json
import os
from datetime import datetime

router = APIRouter()

FEEDBACK_FILE = "response_feedback.json"

class FeedbackRequest(BaseModel):
    request_id: str = None # Optional ID from logging
    input_data: str # sending small snippet or hash
    predicted_result: str
    actual_result: str # 'SAFE' or 'THREAT'
    comments: str = None

@router.post("/submit")
def submit_feedback(feedback: FeedbackRequest):
    """
    Continuous Feedback Mechanism:
    Allows users/analysts to mark False Positives or False Negatives.
    This data is saved locally for future retraining.
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "input": feedback.input_data, # In production, store hash or anonymized version
        "predicted": feedback.predicted_result,
        "actual": feedback.actual_result,
        "comments": feedback.comments
    }
    
    # Save to local JSON file (simulating a database)
    data = []
    if os.path.exists(FEEDBACK_FILE):
        try:
            with open(FEEDBACK_FILE, "r") as f:
                data = json.load(f)
        except:
            pass
            
    data.append(entry)
    
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(data, f, indent=4)
        
    return {"status": "Feedback received. Model will be updated in next cycle."}
