import argparse
import torch
import torchaudio
import os
# Optional: suppress warnings
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from model import WavLM_AASIST_Model

def load_and_chunk_audio(audio_path, target_sr=16000, chunk_sec=5):
    """
    Loads audio, converts to mono, resamples, and splits into 5-second chunks.
    Returns a tensor of shape (num_chunks, 1, samples_per_chunk).
    """
    import soundfile as sf
    try:
        # Load audio using soundfile directly to completely bypass TorchCodec and FFmpeg
        waveform_np, sr = sf.read(audio_path, dtype='float32')
        waveform = torch.from_numpy(waveform_np)
        
        # soundfile returns (frames, channels), but PyTorch expects (channels, frames)
        if waveform.ndim == 2:
            waveform = waveform.transpose(0, 1)
        elif waveform.ndim == 1:
            waveform = waveform.unsqueeze(0)
    except Exception as e:
        raise ValueError(f"Error loading {audio_path}: {e}")

    # Resample to exactly 16kHz
    if sr != target_sr:
        waveform = torchaudio.functional.resample(waveform, sr, target_sr)
    
    # Convert stereo to mono by taking the average
    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)
    waveform = waveform.squeeze(0)

    # Chunking logic (5 seconds = 80,000 samples)
    chunk_samples = target_sr * chunk_sec
    total_samples = waveform.shape[0]
    
    chunks = []
    # If the audio is shorter than 5 seconds, pad it and return 1 chunk
    if total_samples <= chunk_samples:
        padding = chunk_samples - total_samples
        padded_waveform = torch.nn.functional.pad(waveform, (0, padding))
        chunks.append(padded_waveform.unsqueeze(0))
    else:
        # Split into full 5-second segments array
        for i in range(0, total_samples, chunk_samples):
            chunk = waveform[i:i + chunk_samples]
            
            # If the last chunk is too small, pad it to 5 seconds
            # so the model still gets exactly what it expects
            if chunk.shape[0] < chunk_samples:
                padding = chunk_samples - chunk.shape[0]
                chunk = torch.nn.functional.pad(chunk, (0, padding))
            
            chunks.append(chunk.unsqueeze(0))

    # Stack the array of chunks into a batched PyTorch tensor
    # Shape becomes: (num_segments, 1, 80000)
    return torch.stack(chunks)


def main(args):
    # Initialize the device hardware
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    if not os.path.exists(args.audio_path):
        print(f"Error: Could not find audio file at {args.audio_path}")
        return

    # 1. Load, preprocess, and chunk the audio
    print(f"Loading and segmenting {args.audio_path}...")
    batched_waveforms = load_and_chunk_audio(args.audio_path)
    batched_waveforms = batched_waveforms.to(device)
    num_chunks = batched_waveforms.shape[0]

    print(f"Divided audio into {num_chunks} segment(s) of 5 seconds each.")

    # 2. Initialize the model architecture
    print("Loading model architecture...")
    model = WavLM_AASIST_Model(
        model_path="models/wavlm-base",
        freeze_wavlm=True
    ).to(device)

    # 3. Load the saved weights/checkpoint
    if not os.path.exists(args.model_checkpoint):
        print(f"Error: Model checkpoint not found at {args.model_checkpoint}")
        return
    
    print(f"Loading weights from {args.model_checkpoint}...")
    model.load_state_dict(torch.load(args.model_checkpoint, map_location=device))
    model.eval()

    # 4. Predict for each 5-second chunk
    print("\nRunning inference on all segments...")
    segment_predictions = []
    
    with torch.no_grad():
        # Process each chunk individually
        for i in range(num_chunks):
            # Isolate the current 5-second chunk
            output = model(batched_waveforms[i])
            # Apply sigmoid to convert the raw logit score to a probability
            probability = torch.sigmoid(output).item()
            segment_predictions.append(probability)

    # 5. Aggregate & Print Results for Each Timeframe
    print("\n" + "=" * 55)
    print(f"           AUDIO TIMEFRAME DETECTION RESULTS")
    print("=" * 55)
    print(f"File: {os.path.basename(args.audio_path)}")
    print("-" * 55)
    
    total_prob = 0
    fake_count = 0
    
    # Loop over the array of predictions
    for idx, prob in enumerate(segment_predictions):
        start_time = idx * 5
        end_time = start_time + 5
        
        # Project Dataset Mapping: >= 0.5 is Real, < 0.5 is Fake
        is_real = prob >= 0.5
        label = "Bonafide" if is_real else "Spoof"
        confidence = prob * 100 if is_real else (1 - prob) * 100
        
        # Keep track of totals
        total_prob += prob
        if not is_real:
            fake_count += 1
            
        print(f"[{start_time:02d}s - {end_time:02d}s]: {label: <8} | Confidence: {confidence:.2f}%")

    print("-" * 55)
    
    # Provide an overall averaged conclusion
    avg_prob = total_prob / len(segment_predictions)
    overall_label = "Bonafide (Real)" if avg_prob >= 0.5 else "Spoof (Fake)"
    overall_confidence = avg_prob * 100 if avg_prob >= 0.5 else (1 - avg_prob) * 100
    
    print(f"OVERALL CONCLUSION: {overall_label} ({overall_confidence:.2f}%)")
    
    # Alert the user if parts of the audio were spoofed (even if the overall average is highly real)
    if fake_count > 0:
        print(f"WARNING: Detected AI-generated voice in {fake_count} out of {num_chunks} segment(s)!")
    print("=" * 55 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test a long audio file for deepfakes by chunking.")
    
    # Positional argument for the audio file
    parser.add_argument('audio_path', type=str, help='Path to the audio file you want to test (.wav, .mp3, etc.)')
    
    # Optional argument to choose the trained model
    parser.add_argument('--model_checkpoint', type=str, default='output/2_best_model_FineTuned.pth', 
                        help='Path to the trained .pth model file (defaults to the fine-tuned model)')
    
    args = parser.parse_args()
    main(args)
