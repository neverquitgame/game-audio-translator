import time
import logging
import threading
import numpy as np
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class Transcriber:
    def __init__(
        self,
        model_size: str = "base",
        on_ready: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self._model_size = model_size
        self._model = None
        self._model_ready = threading.Event()
        self._on_ready = on_ready
        self._on_error = on_error

        thread = threading.Thread(
            target=self._load_model,
            daemon=True,
            name="whisper-loader",
        )
        thread.start()

    def _load_model(self):
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading Whisper model: {self._model_size}")
            start = time.time()
            self._model = WhisperModel(self._model_size, device="cpu", compute_type="int8")
            logger.info(f"Model loaded in {time.time() - start:.2f}s")
            self._model_ready.set()
            if self._on_ready:
                self._on_ready()
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            self._model = None
            self._model_ready.set()  # Unblock waiters even on failure
            if self._on_error:
                self._on_error(str(e))

    @property
    def model_size(self) -> str:
        return self._model_size

    @property
    def is_ready(self) -> bool:
        return self._model_ready.is_set() and self._model is not None

    def wait_until_ready(self, timeout: float = 120.0) -> bool:
        """Chờ model load xong. Trả về True nếu model đã sẵn sàng."""
        self._model_ready.wait(timeout=timeout)
        return self._model is not None

    def transcribe(self, audio_data: np.ndarray, language: str = "en") -> Optional[str]:
        if not self._model_ready.is_set():
            logger.warning("Whisper model chưa load xong — bỏ qua chunk này")
            return None

        if self._model is None:
            logger.error("Whisper model không load được")
            return None

        if audio_data is None or len(audio_data) == 0:
            return None

        try:
            start = time.time()
            segments, info = self._model.transcribe(
                audio_data,
                language=language,
                beam_size=5,
                vad_filter=False,  # VAD is handled upstream
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            elapsed = time.time() - start
            logger.info(f"Transcribed in {elapsed:.2f}s: '{text[:80]}{'...' if len(text) > 80 else ''}'")
            return text if text else None
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
