import os
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

# For Audio
try:
    import librosa
except ImportError:
    librosa = None

def train_audio_model():
    print("Training Robust Audio Deepfake Model (Random Forest)...")
    if librosa is None:
        print("librosa not installed, skipping audio model.")
        return

    # In a real scenario, we load hundreds of real/fake audio files
    # Here, we generate synthetic MFCC features (e.g., shape: 40)
    # 0 = Real Human, 1 = AI Deepfake
    
    # Generate 500 fake records and 500 real records
    # Deepfakes might have altered high-frequency cepstral coefficients or extremely low variance
    np.random.seed(42)
    real_audio = np.random.normal(0, 1, size=(500, 40))
    fake_audio = np.random.normal(0.5, 0.8, size=(500, 40)) 
    
    X = np.vstack((real_audio, fake_audio))
    y = np.array([0] * 500 + [1] * 500)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    acc = model.score(X, y)
    print(f"Random Forest Audio Classifier Accuracy on Synthetic Data: {acc:.4f}")
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(BASE_DIR, "models")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "voice_auth_model_advanced.pkl"), "wb") as f:
        pickle.dump(model, f)
    print("Advanced audio model saved in models.")

def train_file_model():
    print("Training Robust File Malware Model (Random Forest)...")
    # Features: [Entropy, ByteDistributionVariance, FileSizeMB, ExecutableSignature]
    # 0 = Safe, 1 = Malware
    np.random.seed(42)
    
    # Safe documents (Low Entropy ~4.5, Low Variance, Variable Size, No signature)
    safe_entropy = np.random.normal(4.5, 0.5, 500)
    safe_var = np.random.normal(10, 2, 500)
    safe_size = np.random.uniform(0.1, 10, 500)
    safe_sig = np.zeros(500)
    safe_data = np.column_stack((safe_entropy, safe_var, safe_size, safe_sig))
    
    # Malware (High Entropy ~7.5, High Variance, Variable Size, Maybe Signature=1)
    mal_entropy = np.random.normal(7.5, 0.5, 500)
    mal_var = np.random.normal(30, 5, 500)
    mal_size = np.random.uniform(0.1, 5, 500)
    mal_sig = np.random.choice([0, 1], size=500, p=[0.3, 0.7])
    mal_data = np.column_stack((mal_entropy, mal_var, mal_size, mal_sig))
    
    X = np.vstack((safe_data, mal_data))
    y = np.array([0] * 500 + [1] * 500)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    acc = model.score(X, y)
    print(f"Random Forest Malware Classifier Accuracy on Synthetic File Data: {acc:.4f}")
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(BASE_DIR, "models")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "malware_sig_model_advanced.pkl"), "wb") as f:
        pickle.dump(model, f)
    print("Advanced file model saved in models.")

if __name__ == "__main__":
    train_audio_model()
    train_file_model()
