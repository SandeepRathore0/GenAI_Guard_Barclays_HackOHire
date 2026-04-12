import pickle
import os
from app.core.config import settings

class ModelLoader:
    _models = {}

    @staticmethod
    def load_model(model_name: str, model_dir: str = None):
        """
        Loads a pickle model.
        If model_dir is provided, looks there. Otherwise uses settings.MODELS_DIR.
        """
        # Cache key needs to include dir to differentiate same-named models in diff dirs? 
        # For simplicity, assuming unique model names or just cached by name.
        if model_name in ModelLoader._models:
            return ModelLoader._models[model_name]

        base_dir = model_dir if model_dir else settings.MODELS_DIR
        model_path = os.path.join(base_dir, f"{model_name}.pkl")
        
        if not os.path.exists(model_path):
            print(f"Warning: Model {model_name} not found at {model_path}. Using dummy mode.")
            return None

        try:
            with open(model_path, "rb") as f:
                model = pickle.load(f)
                ModelLoader._models[model_name] = model
                print(f"Loaded model: {model_name} from {base_dir}")
                return model
        except Exception as e:
            print(f"Error loading model {model_name}: {e}")
            return None

    @staticmethod
    def load_local_llm(model_path: str):
        """
        Example for loading a local HuggingFace model (Offline).
        Requires: transformers, torch
        """
        # from transformers import pipeline
        # return pipeline("text-classification", model=model_path)
        pass

    @staticmethod
    def predict(model_name: str, input_data, model_dir: str = None):
        """
        Generic prediction wrapper.
        If model is missing, returns a dummy safe response.
        """
        model = ModelLoader.load_model(model_name, model_dir)
        if model:
            # Assuming model has a predict method
            try:
                return model.predict([input_data])[0]
            except Exception as e:
                print(f"Prediction error with {model_name}: {e}")
                return None
        return None

    @staticmethod
    def huggingface_predict(payload: dict, endpoint: str):
        """
        Queries a HuggingFace Inference API endpoint to act as a fallback.
        Requires HUGGINGFACE_API_KEY to be set in the environment.
        """
        api_key = os.environ.get("HUGGINGFACE_API_KEY")
        if not api_key:
            print("Error: HUGGINGFACE_API_KEY not found in environment for fallback.")
            return None
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            import requests
            response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"HF API Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"HF API connection error: {e}")
            return None
