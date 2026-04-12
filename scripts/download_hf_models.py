import os
from huggingface_hub import hf_hub_download

repo_id = "obsidianGalaxy/models.safetensors"

models_to_download = [
    {
        "filename": "2_best_model_FineTuned.pth",
        "local_dir": os.path.join("services", "audio_guard", "core", "output")
    },
    {
        "filename": "pytorch_model.bin",
        "local_dir": os.path.join("services", "audio_guard", "core", "models", "wavlm-base")
    },
    {
        "filename": "model.safetensors",
        "local_dir": os.path.join("services", "audio_guard", "core", "models", "wavlm-base")
    }
]

print(f"Downloading large Deep Learning models from {repo_id}...")

for model in models_to_download:
    # Ensure the local directory structure exists
    os.makedirs(model["local_dir"], exist_ok=True)
    print(f"\nFetching {model['filename']} -> {model['local_dir']}")
    
    # Download directly into the target directory
    hf_hub_download(
        repo_id=repo_id,
        filename=model["filename"],
        local_dir=model["local_dir"]
    )

print("\n All models downloaded and placed in their correct directories successfully!")
