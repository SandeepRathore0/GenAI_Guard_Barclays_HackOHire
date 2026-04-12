# Deepfake Audio Detection Model - Integration Guide

This folder contains a ready-to-use audio deepfake prediction system. It is designed to be easily dropped into any Python project to detect AI-generated/spoofed audio using a combination of **WavLM** and an **AASIST** backend.

---

## 1. File Structure & Uses

Before integrating, here is exactly what every file and folder in this directory does:

*   **`inference.py`**: The main entry point you will interact with. It contains the `AudioDeepfakeDetector` class, which handles all the complex audio logic (loading, chunking, math) behind a simple `.predict(file)` method. Use this script to integrate the model into your app.
*   **`model.py`**: The raw PyTorch architecture blueprint. This contains the class definitions (`WavLMFeatureExtractor`, `AASIST`, and `WavLM_AASIST_Model`). PyTorch *must* have access to this file to know how the neural network's layers are stacked before it can load the saved weights.
*   **`predict.py`**: The original command-line inference script from the root project. It is left here purely as an alternative reference on how to predict audio chunk-by-chunk if you don't want to use the object-oriented `inference.py`.
*   **`requirements.txt`**: A slimmed-down requirements file. Your new project env only needs these specific libraries to run the predictions, avoiding bloated training dependencies.
*   **`models/wavlm-base/`**: This folder holds the foundational feature-extractor's vocabulary and configuration (`config.json`, etc.). Since WavLM is a HuggingFace model, it looks for this folder on initialization to understand its base architecture.
*   **`output/2_best_model_FineTuned.pth`**: The actual pre-trained "brain" of the model. This `~380MB` file contains all the learned weights and biases from the Deepfake training process.

---

## 2. How the Model Works
This model uses a two-stage deep learning architecture:

1.  **Feature Extractor (WavLM-Base)**: 
    *   WavLM is a foundational speech model pre-trained on tens of thousands of hours of audio. 
    *   Instead of using traditional audio features like MFCCs, this model extracts rich, high-dimensional contextual representations (hidden states) directly from the raw audio waveforms.
2.  **Classification Backend (AASIST-Inspired)**: 
    *   The extracted features are passed into a convolutional neural network (CNN) combined with an Attention mechanism.
    *   This backend identifies the subtle artifacts and anomalies left behind by AI voice generators (like ElevenLabs, VITS, or Tacotron).
    *   It outputs a probability score between 0 and 1, where **>= 0.5** indicates true human speech (Bonafide), and **< 0.5** indicates an AI fake (Spoof).

---

## 3. How the Audio is Processed
Because the model was trained on very specific data formatting, **audio must be preprocessed carefully before prediction**. This is handled automatically by the `AudioDeepfakeDetector` class in `inference.py`, which performs the following pipeline:

1.  **Loading**: Reads the file (WAV, MP3, FLAC, etc.) using `soundfile` to bypass potential PyTorch/FFmpeg codec issues on Windows.
2.  **Mono Conversion**: If the audio is stereo, it averages the channels down to a single mono track.
3.  **Resampling**: The audio is strictly resampled to **16,000 Hz (16 kHz)**. The model expects exactly this sample rate.
4.  **Chunking and Padding**:
    *   The model evaluates audio in exact **5.0-second segments** (80,000 samples).
    *   If the audio is longer than 5 seconds, it is split into multiple 5-second chunks.
    *   If a chunk (or the entire audio file) is shorter than 5 seconds, the end is padded out with silence (zeros) so the math always equals exactly 80,000 samples. 
5.  **Averaging**: The model predicts each 5-second chunk individually. The final project score is the average confidence of all chunks combined.

---

## 4. Things to Consider Before Running

Before integrating this into production or your new project, keep the following in mind:

### A. CUDA / GPU Setup (Crucial)
While this code works on a CPU, audio models are computationally heavy. For reasonable inference speeds, you need a GPU.
*   **Default pip behavior on Windows usually installs the CPU-only version of PyTorch.**
*   Ensure you have installed the CUDA variant of PyTorch:
    ```bash
    # Uninstall the default ones first
    pip uninstall torch torchaudio -y
    
    # Install the CUDA 11.8 or 12.1 runtime
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
    ```

### B. Dependencies
Make sure you install the required packages using the provided `requirements.txt`:
```bash
pip install -r requirements.txt
```
*(Packages include: `torch`, `torchaudio`, `transformers`, `soundfile`)*

### C. File References
The `inference.py` script expects the folder `models/` (containing the WavLM base) and `output/` (containing the `.pth` weights) to remain relatively positioned next to it. If you move `inference.py` around in your new project structure, remember to update the paths in its constructor:
```python
def __init__(self, 
             model_dir="path/to/models/wavlm-base", 
             checkpoint_path="path/to/output/2_best_model_FineTuned.pth",
             ...):
```

### D. Audio Length Performance
Because this predicts in 5-second blocks, passing a 1-hour podcast will result in 720 individual predictions running consecutively. While batching helps, extremely long audio files may consume significant RAM/VRAM.

---

## Quick Start Example
To use it in your new app, simply import the class:

```python
from inference import AudioDeepfakeDetector

# Initialize (loads to GPU automatically if available)
detector = AudioDeepfakeDetector()

# Run Prediction
result = detector.predict("suspicious_voice_note.wav")

if result['is_real']:
    print(f"Human Voice Detected! ({result['overall_confidence_percent']:.2f}% real)")
else:
    print(f"AI Deepfake Detected! ({result['overall_confidence_percent']:.2f}% fake)")
```
