import queue
import logging
import threading
import numpy as np
from typing import Optional

import webrtcvad

from src.config import Config
from src.audio.noise_filter import NoiseFilter

logger = logging.getLogger(__name__)

# Silence threshold: number of silent chunks before cutting the segment
_SILENCE_CHUNKS_THRESHOLD = int(700 / Config.CHUNK_DURATION_MS)  # ~700ms of silence
_MIN_SPEECH_CHUNKS = int(200 / Config.CHUNK_DURATION_MS)          # at least 200ms of speech
_ENERGY_THRESHOLD = -35  # dB threshold for noise gate
_MIN_QUALITY_SCORE = 0.3  # Minimum audio quality score to consider as speech


class VoiceActivityDetector:
    def __init__(self, aggressiveness: int = None):
        level = aggressiveness if aggressiveness is not None else Config.VAD_AGGRESSIVENESS
        self._vad = webrtcvad.Vad(level)
        self._speech_buffer: list[bytes] = []
        self._silent_chunks = 0
        self._in_speech = False
        self._noise_filter = NoiseFilter(Config.SAMPLE_RATE)
        self._noise_profile_init = False
        self._energy_accumulator = []

    def _init_noise_profile(self, audio_chunk: bytes):
        """Initialize noise profile from first few chunks."""
        if not self._noise_profile_init:
            audio_float = self.pcm_to_float32(audio_chunk)
            self._noise_filter.update_noise_profile(audio_float)
            self._energy_accumulator.append(audio_float)

            # After 1 second of audio, consider noise profile initialized
            if len(self._energy_accumulator) >= int(1000 / Config.CHUNK_DURATION_MS):
                self._noise_profile_init = True
                self._energy_accumulator.clear()
                logger.info("Noise profile initialized")

    def process_chunk(self, audio_chunk: bytes) -> bool:
        """
        Enhanced VAD with noise filtering and energy checking.
        Returns True if chunk is likely speech.
        """
        try:
            # Initialize noise profile from first seconds
            if not self._noise_profile_init:
                self._init_noise_profile(audio_chunk)

            # Convert to float
            audio_float = self.pcm_to_float32(audio_chunk)

            # Apply denoising
            audio_denoised = self._noise_filter.denoise(audio_float, strength=0.3)

            # Check energy level
            rms_energy = np.sqrt(np.mean(audio_denoised ** 2))
            energy_db = 20 * np.log10(rms_energy + 1e-10)

            if energy_db < _ENERGY_THRESHOLD:
                # Too quiet, likely silence or very faint noise
                return False

            # Compute audio quality score
            quality_score = self._noise_filter.get_signal_quality_score(audio_denoised)

            # WebRTC VAD + quality filtering
            is_speech = self._vad.is_speech(audio_chunk, Config.SAMPLE_RATE)
            
            # Only consider it speech if both VAD and quality checks pass
            is_speech = is_speech and (quality_score >= _MIN_QUALITY_SCORE)

            return is_speech
        except Exception:
            return False

    def get_speech_segment(
        self,
        audio_queue: queue.Queue,
        stop_event: Optional["threading.Event"] = None,
    ) -> Optional[bytes]:
        """
        Blocks until a complete speech segment is detected.
        Returns raw PCM bytes or None if the queue signals shutdown (None sentinel)
        or stop_event is set.
        """
        self._speech_buffer.clear()
        self._silent_chunks = 0
        self._in_speech = False

        while True:
            try:
                chunk = audio_queue.get(timeout=1.0)
            except queue.Empty:
                if stop_event is not None and stop_event.is_set():
                    return None
                continue

            if chunk is None:
                return None

            is_speech = self.process_chunk(chunk)

            if is_speech:
                self._speech_buffer.append(chunk)
                self._silent_chunks = 0
                self._in_speech = True
            elif self._in_speech:
                self._speech_buffer.append(chunk)
                self._silent_chunks += 1

                if self._silent_chunks >= _SILENCE_CHUNKS_THRESHOLD:
                    if len(self._speech_buffer) >= _MIN_SPEECH_CHUNKS:
                        result = b"".join(self._speech_buffer)
                        self._speech_buffer.clear()
                        self._silent_chunks = 0
                        self._in_speech = False
                        return result
                    else:
                        # Too short — likely noise, discard
                        self._speech_buffer.clear()
                        self._silent_chunks = 0
                        self._in_speech = False

    def pcm_to_float32(self, pcm_bytes: bytes) -> np.ndarray:
        """Convert 16-bit PCM bytes to float32 numpy array normalized to [-1, 1]."""
        audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
        return audio_int16.astype(np.float32) / 32768.0
