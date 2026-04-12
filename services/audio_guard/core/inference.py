import torch
import torchaudio
import os
import soundfile as sf

from model import WavLM_AASIST_Model

class AudioDeepfakeDetector:
    def __init__(self, 
                 model_dir="models/wavlm-base", 
                 checkpoint_path="output/2_best_model_FineTuned.pth",
                 device=None):
        """
        Initializes the deepfake detector model.
        Args:
            model_dir (str): Path to the WavLM base model directory.
            checkpoint_path (str): Path to the trained .pth weights file.
            device (str): "cuda" or "cpu" to enforce a specific device. None defaults to auto-detect.
        """
        if device:
            self.device = torch.device(device)
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            
        print(f"[{self.__class__.__name__}] Using device: {self.device}")

        if not os.path.exists(model_dir):
            raise FileNotFoundError(f"Missing WavLM base directory at {model_dir}")
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Missing checkpoint file at {checkpoint_path}")

        print(f"[{self.__class__.__name__}] Loading model architecture...")
        self.model = WavLM_AASIST_Model(
            model_path=model_dir,
            freeze_wavlm=True
        ).to(self.device)

        print(f"[{self.__class__.__name__}] Loading weights from {checkpoint_path}...")
        self.model.load_state_dict(torch.load(checkpoint_path, map_location=self.device))
        self.model.eval()

    def _preprocess_audio(self, audio_path, target_sr=16000, chunk_sec=5):
        """
        Loads audio, converts to mono, resamples, and splits into 5-second chunks.
        Returns a tensor of shape (num_chunks, 1, samples_per_chunk).
        """
        try:
            waveform_np, sr = sf.read(audio_path, dtype='float32')
            waveform = torch.from_numpy(waveform_np)
            
            if waveform.ndim == 2:
                waveform = waveform.transpose(0, 1)
            elif waveform.ndim == 1:
                waveform = waveform.unsqueeze(0)
        except Exception as e:
            raise ValueError(f"Error loading {audio_path}: {e}")

        if sr != target_sr:
            waveform = torchaudio.functional.resample(waveform, sr, target_sr)
        
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        waveform = waveform.squeeze(0)

        chunk_samples = target_sr * chunk_sec
        total_samples = waveform.shape[0]
        chunks = []

        if total_samples <= chunk_samples:
            padding = chunk_samples - total_samples
            padded_waveform = torch.nn.functional.pad(waveform, (0, padding))
            chunks.append(padded_waveform.unsqueeze(0))
        else:
            for i in range(0, total_samples, chunk_samples):
                chunk = waveform[i:i + chunk_samples]
                if chunk.shape[0] < chunk_samples:
                    padding = chunk_samples - chunk.shape[0]
                    chunk = torch.nn.functional.pad(chunk, (0, padding))
                chunks.append(chunk.unsqueeze(0))

        return torch.stack(chunks)

    def predict(self, audio_path):
        """
        Predicts if an audio file is real or fake.
        Returns:
            dict: Contains 'is_real' (bool), 'confidence_percent' (float), and 'segment_details' (list)
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Could not find audio file at {audio_path}")

        batched_waveforms = self._preprocess_audio(audio_path).to(self.device)
        
        segment_predictions = []
        with torch.no_grad():
            for i in range(batched_waveforms.shape[0]):
                output = self.model(batched_waveforms[i])
                prob = torch.sigmoid(output).item()
                segment_predictions.append(prob)

        total_prob = sum(segment_predictions)
        avg_prob = total_prob / len(segment_predictions)
        
        is_overall_real = avg_prob >= 0.5
        overall_confidence = avg_prob * 100 if is_overall_real else (1 - avg_prob) * 100
        
        # Details per 5-second chunk
        segment_details = [
            {
                "time_range": f"{i*5}s - {(i+1)*5}s",
                "is_real": p >= 0.5,
                "confidence_percent": p * 100 if p >= 0.5 else (1 - p) * 100
            } for i, p in enumerate(segment_predictions)
        ]

        return {
            "prediction": "Real" if is_overall_real else "Spoof",
            "is_real": is_overall_real,
            "overall_confidence_percent": overall_confidence,
            "segment_count": len(segment_details),
            "segment_details": segment_details
        }

if __name__ == "__main__":
    # Example usage:
    detector = AudioDeepfakeDetector()
    # Replace with an actual wav file path to test
    # result = detector.predict("test_audio.wav")
    # print(result)
    print("Ready for deepfake inference integration!")
