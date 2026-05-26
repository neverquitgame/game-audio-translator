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
_MIN_QUALITY_SCORE = 0.3  # Minimum audio quality score to consider as speech


class VoiceActivityDetector:
    def __init__(self, aggressiveness: Optional[int] = None):
        level = aggressiveness if aggressiveness is not None else Config.VAD_AGGRESSIVENESS
        self._vad = webrtcvad.Vad(level)
        self._speech_buffer: list[bytes] = []
        self._silent_chunks = 0
        self._in_speech = False

        # Cấu hình lấy từ Config (đọc 1 lần khi khởi tạo — UI rebuild VAD khi user save)
        self._enable_denoise: bool = bool(Config.ENABLE_NOISE_FILTER)
        self._denoise_strength: float = float(Config.NOISE_FILTER_STRENGTH)
        self._energy_threshold_db: float = float(Config.ENERGY_THRESHOLD_DB)

        self._noise_filter = NoiseFilter(Config.SAMPLE_RATE) if self._enable_denoise else None
        self._noise_profile_init = not self._enable_denoise
        self._noise_chunks_seen = 0
        self._noise_chunks_needed = max(1, int(1000 / Config.CHUNK_DURATION_MS))

    def _init_noise_profile(self, audio_float: np.ndarray):
        """Initialize noise profile from first ~1s of audio."""
        if self._noise_filter is None:
            return
        self._noise_filter.update_noise_profile(audio_float)
        self._noise_chunks_seen += 1
        if self._noise_chunks_seen >= self._noise_chunks_needed:
            self._noise_profile_init = True
            logger.info("Noise profile initialized")

    def process_chunk(self, audio_chunk: bytes) -> bool:
        """
        VAD nhẹ: WebRTC-VAD + noise gate theo dB.
        Spectral denoise / quality scoring chỉ chạy nếu user bật noise filter.
        """
        try:
            # webrtcvad là rẻ nhất — chạy trước, fail-fast khi rõ ràng là silence
            sample_rate = Config.SAMPLE_RATE
            is_speech_vad = self._vad.is_speech(audio_chunk, sample_rate)

            audio_float = self.pcm_to_float32(audio_chunk)

            # Energy gate trên tín hiệu gốc — rẻ, đủ cho phần lớn trường hợp
            rms = float(np.sqrt(np.mean(audio_float * audio_float)))
            if rms < 1e-10:
                return False
            energy_db = 20.0 * np.log10(rms)
            if energy_db < self._energy_threshold_db:
                return False

            if not self._enable_denoise:
                return is_speech_vad

            # Heavy path: spectral analysis chỉ khi user bật
            if not self._noise_profile_init:
                self._init_noise_profile(audio_float)
                return is_speech_vad

            audio_denoised = self._noise_filter.denoise(audio_float, strength=self._denoise_strength)
            quality_score = self._noise_filter.get_signal_quality_score(audio_denoised)
            return is_speech_vad and (quality_score >= _MIN_QUALITY_SCORE)
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

    @staticmethod
    def pcm_to_float32(pcm_bytes: bytes) -> np.ndarray:
        """Convert 16-bit PCM bytes to float32 numpy array normalized to [-1, 1]."""
        audio_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
        return audio_int16.astype(np.float32) / 32768.0
