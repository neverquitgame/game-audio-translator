import queue
import logging
import numpy as np
from typing import Optional

import webrtcvad

from src.config import Config

logger = logging.getLogger(__name__)

# Silence threshold: number of silent chunks before cutting the segment
_SILENCE_CHUNKS_THRESHOLD = int(700 / Config.CHUNK_DURATION_MS)  # ~700ms of silence
_MIN_SPEECH_CHUNKS = int(200 / Config.CHUNK_DURATION_MS)          # at least 200ms of speech


class VoiceActivityDetector:
    def __init__(self, aggressiveness: int = None):
        level = aggressiveness if aggressiveness is not None else Config.VAD_AGGRESSIVENESS
        self._vad = webrtcvad.Vad(level)
        self._speech_buffer: list[bytes] = []
        self._silent_chunks = 0
        self._in_speech = False

    def process_chunk(self, audio_chunk: bytes) -> bool:
        try:
            is_speech = self._vad.is_speech(audio_chunk, Config.SAMPLE_RATE)
            return is_speech
        except Exception as e:
            logger.debug(f"VAD error on chunk: {e}")
            return False

    def get_speech_segment(self, audio_queue: queue.Queue) -> Optional[bytes]:
        """
        Blocks until a complete speech segment is detected.
        Returns raw PCM bytes or None if the queue signals shutdown (None sentinel).
        """
        self._speech_buffer.clear()
        self._silent_chunks = 0
        self._in_speech = False

        while True:
            try:
                chunk = audio_queue.get(timeout=1.0)
            except queue.Empty:
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
