import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from xgboost import XGBClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from datasets import load_dataset
import pickle

def train_advanced_text_phishing():
    print("Training Advanced Text Phishing Model (XGBoost)...")
    try:
        # Load a well-known spam/phishing dataset from HF
        dataset = load_dataset("SetFit/enron_spam", split="train")
        df = pd.DataFrame(dataset)
        
        # The dataset has 'text' and 'label' (0 or 1)
        # Drop nan texts
        df = df.dropna(subset=['text'])

        # We'll use a subset for speed in this demo, but typically use the full dataset
        df = df.sample(n=min(5000, len(df)), random_state=42)

        X = df['text']
        y = df['label']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        vectorizer = TfidfVectorizer(max_features=5000)
        model = XGBClassifier(use_label_encoder=False, eval_metric='logloss')

        # Fit
        X_train_vec = vectorizer.fit_transform(X_train)
        model.fit(X_train_vec, y_train)

        # Evaluate
        X_test_vec = vectorizer.transform(X_test)
        acc = model.score(X_test_vec, y_test)
        print(f"XGBoost Text Classifier Accuracy: {acc:.4f}")

        # Save
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out_dir = os.path.join(BASE_DIR, "app", "modules", "text_guard", "models")
        os.makedirs(out_dir, exist_ok=True)
        
        with open(os.path.join(out_dir, "tfidf_vectorizer_advanced.pkl"), "wb") as f:
            pickle.dump(vectorizer, f)
        with open(os.path.join(out_dir, "spam_classifier_xgboost.pkl"), "wb") as f:
            pickle.dump(model, f)
        
        print("Advanced text models saved successfully.")

    except Exception as e:
        print(f"Error training advanced text model: {e}")


def train_advanced_web_phishing():
    print("Training Advanced Web Phishing Model (Random Forest)...")
    try:
        from sklearn.ensemble import RandomForestClassifier
        # Synthetic dataset representing URL features: 
        # [URLLength, DomainLength, IsHTTPS, NoOfSubDomain, URLSimilarityIndex]
        # 1 = Phishing, 0 = Safe
        data = [
            [25, 12, 1, 0, 0, 0], # Safe
            [95, 20, 0, 2, 70, 1], # Phishing
            [30, 15, 1, 0, 0, 0], # Safe
            [120, 30, 0, 3, 90, 1], # Phishing
            [40, 12, 1, 1, 10, 0], # Safe
            [85, 25, 0, 2, 60, 1]  # Phishing
        ] * 50

        df = pd.DataFrame(data, columns=["URLLength", "DomainLength", "IsHTTPS", "NoOfSubDomain", "URLSimilarityIndex", "label"])

        X = df.drop("label", axis=1)
        y = df["label"]

        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X, y)
        acc = model.score(X, y)
        print(f"Random Forest Web Classifier Accuracy on synthetic batch: {acc:.4f}")

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out_dir = os.path.join(BASE_DIR, "app", "modules", "web_guard", "models")
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "model_advanced.pkl"), "wb") as f:
            pickle.dump(model, f)
            
        print("Advanced web model saved successfully.")
    except Exception as e:
         print(f"Error training advanced web model: {e}")

if __name__ == "__main__":
    train_advanced_text_phishing()
    train_advanced_web_phishing()
