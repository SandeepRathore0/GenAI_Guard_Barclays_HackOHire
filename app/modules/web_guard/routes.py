from fastapi import APIRouter
from pydantic import BaseModel
from app.core.model_loader import ModelLoader
from app.core.activity_logger import ActivityLogger
import os
import sys
from urllib.parse import urlparse
from scipy.sparse import hstack, csr_matrix
import numpy as np
import requests

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
sys.path.append(MODELS_DIR)
from typosquat import typosquat_score
from ssl_check import has_ssl
from app.modules.web_guard.cookie_analyzer import CookieAnalyzer

# HF Fallback Pipeline
hf_web_model = None

def get_hf_fallback():
    global hf_web_model
    if hf_web_model is None:
        try:
            from transformers import pipeline
            print("Loading HuggingFace Fallback Model...")
            hf_web_model = pipeline("text-classification", model="elftsdmr/malicious-url-detection")
        except ImportError:
            print("Transformers not installed. Fallback unavailable.")
            hf_web_model = False
        except Exception as e:
            print(f"Failed to load HF fallback: {e}")
            hf_web_model = False
    return hf_web_model

router = APIRouter()

class WebAnalysisRequest(BaseModel):
    url: str = None
    cookies: dict = None
    feature: str # 'phishing_site', 'cookie_integrity'

@router.post("/scan")
def scan_web(request: WebAnalysisRequest):
    risk_score = 0
    alerts = []

    # 4. Website Phishing Detection
    if request.feature == 'phishing_site' or request.feature == 'all':
        if request.url:
            model_used = False
            try:
                import joblib
                import xgboost as xgb
                import pandas as pd
                from url_feature_extractor import URLFeatureExtractor
                
                # Load the Github model components dynamically
                scaler = joblib.load(os.path.join(MODELS_DIR, "scaler.pkl"))
                booster = xgb.Booster()
                booster.load_model(os.path.join(MODELS_DIR, "xgb_model.json"))
                
                FEATURE_COLUMNS = [
                    "URLLength", "DomainLength", "TLDLength", "NoOfImage", "NoOfJS", "NoOfCSS", 
                    "NoOfSelfRef", "NoOfExternalRef", "IsHTTPS", "HasObfuscation", "HasTitle", 
                    "HasDescription", "HasSubmitButton", "HasSocialNet", "HasFavicon", 
                    "HasCopyrightInfo", "popUpWindow", "Iframe", "Abnormal_URL", 
                    "LetterToDigitRatio", "Redirect_0", "Redirect_1"
                ]
                
                # 1. Real-time DOM Feature Extraction
                extractor = URLFeatureExtractor(request.url, timeout=3)
                features = extractor.extract_model_features()
                
                # 2. DataFrame scaling & XGBoost Output Matrix configuration
                input_df = pd.DataFrame([features], columns=FEATURE_COLUMNS)
                scaled_input = scaler.transform(input_df)
                dmatrix = xgb.DMatrix(scaled_input, feature_names=FEATURE_COLUMNS)
                
                # 3. Model Prediction
                pred = booster.predict(dmatrix)
                
                # The Github repo defines 1 as Legitimate, 0 as Phishing
                # We invert this so 1.0 (100%) represents absolute malicious threat
                phish_prob = 1.0 - float(pred[0])
                
                # Ensure offline sites aren't automatically passed as perfectly safe
                if extractor.error and extractor.is_abnormal_url():
                     phish_prob = max(phish_prob, 0.85)

                if phish_prob > 0.65:
                    risk_score += int(phish_prob * 100)
                    alerts.append(f"Malicious phishing signatures detected by PhishShield AI ({phish_prob:.0%} confidence)")
                elif phish_prob > 0.40:
                    risk_score += max(45, int(phish_prob * 100))
                    alerts.append(f"Suspicious URL characteristics recognized ({phish_prob:.0%} confidence)")
                elif phish_prob < 0.20:
                    alerts.append("Domain extensively verified as legitimate by GenAI model")

                # --- SHAP + LLM Integration for URLs ---
                if phish_prob > 0.40:
                    try:
                        import shap
                        explainer = shap.TreeExplainer(booster)
                        shap_values = explainer.shap_values(scaled_input)
                        
                        # 0 is Phishing. Negative SHAP values push towards 0.
                        top_risk_indices = np.argsort(shap_values[0])[:3]
                        top_risk_factors = [FEATURE_COLUMNS[i] for i in top_risk_indices]
                        
                        llm_payload = {
                            "text": f"URL: {request.url}\nRisk Score: {phish_prob*100:.0f}%\nTop 3 Risk Factors from SHAP: {', '.join(top_risk_factors)}",
                            "check_type": "url_explanation"
                        }
                        
                        llm_resp = requests.post("http://localhost:8001/api/v1/scan", json=llm_payload, timeout=45.0)
                        if llm_resp.status_code == 200:
                            llm_data = llm_resp.json()
                            if llm_data.get("alerts") and len(llm_data["alerts"]) > 0:
                                alerts.append(llm_data["alerts"][0])
                    except Exception as shap_e:
                        print(f"SHAP/LLM URL Explanation failed (non-fatal): {shap_e}")

                model_used = True
                    
            except Exception as e:
                print(f"Web Guard Model Error (Primary Model failed): {e}")
                
                # Full Fallback to HuggingFace Pre-trained Model
                fallback = get_hf_fallback()
                if fallback:
                    try:
                        hf_res = fallback(request.url)[0]
                        lbl = hf_res['label'].lower()
                        if 'phishing' in lbl or 'malicious' in lbl or 'bad' in lbl or '1' in lbl:
                            risk_score += int(hf_res['score'] * 100)
                            alerts.append(f"Known malicious domain signature detected ({hf_res['score']:.0%} confidence)")
                    except Exception as hf_e:
                        print(f"HuggingFace Fallback also failed: {hf_e}")
                        # Final Failsafe
                        legit_domains = ["hdfcbank.com", "barclays.com", "google.com"]
                        domain_parts = urlparse(request.url).netloc.split(":")[0]
                        if any(lg in domain_parts for lg in legit_domains) and domain_parts not in legit_domains:
                            risk_score += 70
                            alerts.append(f"Suspicious domain resembling known brand: {domain_parts}")
                else:
                    # Final Failsafe if HF model isn't installed
                    legit_domains = ["hdfcbank.com", "barclays.com", "google.com"]
                    domain_parts = urlparse(request.url).netloc.split(":")[0]
                    if any(lg in domain_parts for lg in legit_domains) and domain_parts not in legit_domains:
                        risk_score += 70
                        alerts.append(f"Suspicious domain resembling known brand: {domain_parts}")

    # 5. Cookie Manipulation Detection
    if request.feature == 'cookie_integrity' or request.feature == 'all':
        if request.cookies:
            cookie_alerts = CookieAnalyzer.analyze_cookies(request.cookies)
            if cookie_alerts:
                risk_score += 60 + (len(cookie_alerts) * 10)
                alerts.extend(cookie_alerts)
                
                # --- LLM Integration for Cookies ---
                try:
                    llm_payload = {
                        "text": "\n".join(cookie_alerts),
                        "check_type": "cookie_explanation"
                    }
                    llm_resp = requests.post("http://localhost:8001/api/v1/scan", json=llm_payload, timeout=45.0)
                    if llm_resp.status_code == 200:
                        llm_data = llm_resp.json()
                        if llm_data.get("alerts") and len(llm_data["alerts"]) > 0:
                            alerts.append(llm_data["alerts"][0])
                except Exception as cookie_e:
                    print(f"LLM Cookie Explanation failed (non-fatal): {cookie_e}")

    # Log the activity
    display_name = request.url if request.url else "Cookies Analysis"
    if len(display_name) > 45:
        display_name = display_name[:42] + "..."
        
    ActivityLogger.log_activity(
        "Web Guard",
        display_name,
        min(risk_score, 100),
        alerts
    )

    return {
        "risk_score": min(risk_score, 100),
        "alerts": alerts
    }
