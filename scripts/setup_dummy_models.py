import pickle
import os

class DummyModel:
    def __init__(self, name, always_predict=0):
        self.name = name
        self.always_predict = always_predict
        
    def predict(self, *args, **kwargs):
        # Return 0 (Safe) or 1 (Threat)
        # We will return 1 for specific inputs just for demo if needed, but 0 by default.
        return [self.always_predict]

def main():
    models_to_create = [
        ("app/modules/text_guard/models", "injection_clf", 0),
        ("app/modules/file_guard/models", "malware_sig_model", 0),
        ("app/modules/audio_guard/models", "voice_auth_model", 0)
    ]

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for directory, model_name, default_pred in models_to_create:
        full_dir = os.path.join(base_dir, directory)
        os.makedirs(full_dir, exist_ok=True)
        
        model_path = os.path.join(full_dir, f"{model_name}.pkl")
        if not os.path.exists(model_path):
            with open(model_path, "wb") as f:
                pickle.dump(DummyModel(model_name, default_pred), f)
            print(f"Created {model_path}")
        else:
            print(f"Exists already: {model_path}")

if __name__ == "__main__":
    main()
