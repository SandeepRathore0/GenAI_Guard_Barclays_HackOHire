import httpx
from typing import Dict, Any, List
from fastapi import UploadFile
import io
from app.modules.text_guard.routes import analyze_text, TextAnalysisRequest
from app.modules.web_guard.routes import scan_web, WebAnalysisRequest
from app.modules.audio_guard.routes import detect_deepfake
from app.modules.file_guard.routes import scan_file

class EmailSandbox:
    @staticmethod
    async def analyze_email_components(parsed_email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrates the security analysis of all email components.
        """
        cumulative_score = 0
        overall_alerts = []
        threat_report = {}

        # 1. Text Analysis (Body & Subject)
        # Check for phishing/BEC in body
        if parsed_email["body"]:
            try:
                # Text Guard expects a TextAnalysisRequest
                req = TextAnalysisRequest(text=parsed_email["body"], check_type="phishing")
                text_result = await analyze_text(req)
                
                score = text_result.get("risk_score", 0)
                cumulative_score += score
                
                if score > 0:
                    overall_alerts.extend(text_result.get("alerts", []))
                    threat_report["text_analysis"] = {
                        "score": score,
                        "alerts": text_result.get("alerts", []),
                        "reason": f"Text Guard flagged body content with score {score}."
                    }
            except Exception as e:
                print(f"Error in text analysis: {e}")

        # 2. URL Analysis (Web Guard)
        if parsed_email["urls"]:
            url_alerts = []
            max_url_score = 0
            for url in parsed_email["urls"]:
                try:
                    req = WebAnalysisRequest(url=url, feature="phishing_site")
                    web_result = scan_web(req)
                    
                    score = web_result.get("risk_score", 0)
                    if score > max_url_score:
                        max_url_score = score
                        
                    if score > 0:
                        url_alerts.extend(web_result.get("alerts", []))
                        
                except Exception as e:
                    print(f"Error in web analysis for URL {url}: {e}")
            
            cumulative_score += max_url_score
            if max_url_score > 0:
                overall_alerts.extend(url_alerts)
                threat_report["url_analysis"] = {
                    "score": max_url_score,
                    "alerts": url_alerts,
                    "reason": f"Web Guard flagged {len(url_alerts)} URLs as suspicious."
                }

        # 3. Audio / File Attachments
        if parsed_email["attachments"]:
            for attachment in parsed_email["attachments"]:
                filename = attachment.get("filename", "")
                content_type = attachment.get("content_type", "")
                payload = attachment.get("payload")
                
                if not payload:
                    continue

                # Audio Guard check
                if "audio" in content_type or filename.endswith((".wav", ".mp3", ".ogg")):
                    try:
                        # Create a mock Fastapi UploadFile
                        file_obj = io.BytesIO(payload)
                        upload_file = UploadFile(filename=filename, file=file_obj)
                        
                        audio_result = await detect_deepfake(upload_file)
                        score = audio_result.get("risk_score", 0)
                        
                        cumulative_score += score
                        if score > 0:
                            overall_alerts.extend(audio_result.get("alerts", []))
                            threat_report[f"audio_analysis_{filename}"] = {
                                "score": score,
                                "alerts": audio_result.get("alerts", []),
                                "reason": f"Audio Guard flagged attachment {filename}."
                            }
                    except Exception as e:
                        print(f"Error in audio analysis for {filename}: {e}")
                        
                # File Guard check for executables/documents could go here
                elif "application" in content_type or filename.endswith((".exe", ".pdf", ".docx", ".sh", ".bat", ".ps1", ".tar", ".zip", ".gz", ".py", ".js")):
                    try:
                        file_obj = io.BytesIO(payload)
                        upload_file = UploadFile(filename=filename, file=file_obj)
                        
                        file_result = await scan_file(upload_file)
                        score = file_result.get("risk_score", 0)
                        
                        cumulative_score += score
                        if score > 0:
                            overall_alerts.extend(file_result.get("alerts", []))
                            threat_report[f"file_analysis_{filename}"] = {
                                "score": score,
                                "alerts": file_result.get("alerts", []),
                                "reason": f"File Guard flagged attachment {filename}."
                            }
                    except Exception as e:
                        print(f"Error in file analysis for {filename}: {e}")

        # Finalize the Trust Score (cap at 100)
        final_score = min(cumulative_score, 100)
        status = "SAFE"
        if final_score >= 80:
            status = "CRITICAL_RISK"
        elif final_score >= 50:
            status = "HIGH_RISK"
        elif final_score >= 20:
            status = "SUSPICIOUS"

        return {
            "email_subject": parsed_email["headers"].get("subject"),
            "final_score": final_score,
            "status": status,
            "alerts": list(set(overall_alerts)), # unique alerts
            "threat_report": threat_report
        }
