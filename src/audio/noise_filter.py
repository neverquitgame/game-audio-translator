"""
Advanced audio filtering to reduce noise and improve speech detection.
"""
import numpy as np
from typing import Tuple
import scipy.signal as signal


class NoiseFilter:
    """Applies spectral subtraction and noise gating to reduce background noise."""

    def __init__(self, sample_rate: int = 16000, noise_duration_ms: int = 500):
        self.sample_rate = sample_rate
        self.noise_duration_samples = int(sample_rate * noise_duration_ms / 1000)
        self._noise_profile = None
        self._noise_buffer = []

    def update_noise_profile(self, audio_chunk: np.ndarray):
        """
        Update noise profile from audio chunks (call during silent periods).
        """
        self._noise_buffer.append(audio_chunk)
        if len(self._noise_buffer) * len(audio_chunk) >= self.noise_duration_samples:
            # Combine buffers and compute noise spectrum
            noise_data = np.concatenate(self._noise_buffer)
            self._compute_noise_spectrum(noise_data)
            self._noise_buffer.clear()

    def _compute_noise_spectrum(self, audio: np.ndarray):
        """Compute FFT-based noise profile."""
        try:
            # Compute STFT
            f, t, Zxx = signal.stft(
                audio,
                self.sample_rate,
                nperseg=512,
                noverlap=256,
                window="hamming"
            )
            # Average magnitude spectrum across time
            magnitude = np.abs(Zxx)
            self._noise_profile = np.mean(magnitude, axis=1)
        except Exception:
            self._noise_profile = None

    def denoise(self, audio: np.ndarray, strength: float = 0.5) -> np.ndarray:
        """
        Apply spectral subtraction and noise gating.
        
        Args:
            audio: Input audio samples (float32, normalized to [-1, 1])
            strength: Noise reduction strength (0.0-1.0, higher = more aggressive)
        
        Returns:
            Denoised audio
        """
        if audio is None or len(audio) == 0:
            return audio

        # Step 1: Spectral subtraction if we have noise profile
        if self._noise_profile is not None:
            audio = self._spectral_subtraction(audio, strength)

        # Step 2: Apply noise gate (suppress very quiet signals)
        audio = self._noise_gate(audio, threshold=-40)  # dB

        # Step 3: Soft clipping to prevent distortion
        audio = np.tanh(audio)

        return audio

    def _spectral_subtraction(self, audio: np.ndarray, strength: float) -> np.ndarray:
        """Remove noise using spectral subtraction."""
        try:
            f, t, Zxx = signal.stft(
                audio,
                self.sample_rate,
                nperseg=512,
                noverlap=256,
                window="hamming"
            )

            # Subtract noise spectrum
            magnitude = np.abs(Zxx)
            phase = np.angle(Zxx)

            # Spectral subtraction: M_clean = M_noisy - strength * M_noise
            noise_profile = self._noise_profile.reshape(-1, 1)
            magnitude_subtracted = magnitude - strength * noise_profile

            # Prevent over-subtraction (floor at small value)
            magnitude_subtracted = np.maximum(magnitude_subtracted, 0.01 * magnitude)

            # Reconstruct
            Zxx_cleaned = magnitude_subtracted * np.exp(1j * phase)
            _, audio_cleaned = signal.istft(
                Zxx_cleaned,
                self.sample_rate,
                nperseg=512,
                noverlap=256,
                window="hamming"
            )

            # Match original length
            if len(audio_cleaned) != len(audio):
                audio_cleaned = audio_cleaned[:len(audio)]

            return audio_cleaned
        except Exception:
            return audio

    def _noise_gate(self, audio: np.ndarray, threshold: float = -40) -> np.ndarray:
        """
        Apply noise gate: attenuate signals below threshold.
        
        Args:
            audio: Input audio
            threshold: Gate threshold in dB
        
        Returns:
            Gated audio
        """
        # Convert threshold from dB to linear
        linear_threshold = 10 ** (threshold / 20)

        # Compute frame-wise RMS
        frame_size = 512
        gate = np.ones_like(audio)

        for i in range(0, len(audio) - frame_size, frame_size // 2):
            frame = audio[i:i + frame_size]
            rms = np.sqrt(np.mean(frame ** 2))

            if rms < linear_threshold:
                gate[i:i + frame_size] = 0.0

        return audio * gate

    def get_signal_quality_score(self, audio: np.ndarray) -> float:
        """
        Estimate audio quality (0.0-1.0).
        Higher score = more likely to be speech.
        """
        if audio is None or len(audio) == 0:
            return 0.0

        try:
            # RMS energy
            rms = np.sqrt(np.mean(audio ** 2))
            if rms < 0.001:
                return 0.0

            # Zero crossing rate (speech tends to have lower ZCR than noise)
            zcr = np.mean(np.abs(np.diff(np.sign(audio)))) / (2 * len(audio))

            # Spectral flatness (noise has higher flatness)
            fft_mag = np.abs(np.fft.rfft(audio))
            if np.max(fft_mag) == 0:
                return 0.0

            geometric_mean = np.exp(np.mean(np.log(fft_mag + 1e-10)))
            arithmetic_mean = np.mean(fft_mag)
            spectral_flatness = geometric_mean / (arithmetic_mean + 1e-10)

            # Score: higher RMS + lower ZCR + lower spectral flatness = speech-like
            score = min(1.0, (rms * 100) * (1.0 - zcr) * (1.0 - spectral_flatness))
            return max(0.0, score)
        except Exception:
            return 0.5  # Default to neutral
