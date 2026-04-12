import json
import os
import time
from datetime import datetime

# Ensure we always use the same absolute path for the log file across different processes
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "activity_log.json")
GMAIL_LOG_FILE = os.path.join(LOG_DIR, "gmail_activity_log.json")

print(f"DEBUG: ActivityLogger initialized with log path: {LOG_FILE}")

class ActivityLogger:
    @staticmethod
    def log_activity(module: str, input_type: str, risk_score: int, alerts: list, threat_report: dict = None):
        """
        Logs a security scan event to a local JSON file.
        """
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "module": module,
            "input_type": input_type,
            "risk_score": risk_score,
            "alerts": alerts,
            "status": "THREAT" if risk_score > 50 else "SAFE",
            "threat_report": threat_report or {}
        }

        data = []
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r") as f:
                    data = json.load(f)
            except:
                data = []

        # Prepend new entry (newest first)
        data.insert(0, entry)
        
        # Keep only last 100 entries (increased from 50)
        data = data[:100]

        # Simple retry-based lock to prevent corruption between uvicorn and gmail_sync
        max_retries = 5
        for i in range(max_retries):
            try:
                with open(LOG_FILE, "w") as f:
                    json.dump(data, f, indent=4)
                print(f"DEBUG: Successfully logged {module} event to {LOG_FILE}")
                return # Success
            except PermissionError:
                print(f"DEBUG: File lock contention on retry {i+1}/{max_retries}")
                time.sleep(0.5)
            except Exception as e:
                print(f"Error logging activity: {e}")
                break

    @staticmethod
    def get_logs():
        """
        Retrieves the recent activity logs.
        """
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

    @staticmethod
    def log_gmail_activity(module: str, input_type: str, risk_score: int, alerts: list, threat_report: dict = None):
        """
        Logs a Gmail sync event to a DEDICATED local JSON file to avoid race conditions.
        """
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "module": module,
            "input_type": input_type,
            "risk_score": risk_score,
            "alerts": alerts,
            "status": "THREAT" if risk_score > 50 else "SAFE",
            "threat_report": threat_report or {}
        }

        data = []
        if os.path.exists(GMAIL_LOG_FILE):
            try:
                with open(GMAIL_LOG_FILE, "r") as f:
                    data = json.load(f)
            except:
                data = []

        data.insert(0, entry)
        data = data[:100]

        # No heavy locking needed on dedicated file usually, but we'll use a simple write
        try:
            with open(GMAIL_LOG_FILE, "w") as f:
                json.dump(data, f, indent=4)
            print(f"DEBUG: Successfully logged {module} event to {GMAIL_LOG_FILE}")
        except Exception as e:
            print(f"Error logging gmail activity: {e}")

    @staticmethod
    def get_gmail_logs():
        """
        Retrieves the recent Gmail sync logs.
        """
        if os.path.exists(GMAIL_LOG_FILE):
            try:
                with open(GMAIL_LOG_FILE, "r") as f:
                    return json.load(f)
            except:
                return []
        return []
