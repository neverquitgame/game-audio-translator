"""App — pipeline controller kết nối audio capture → VAD → STT → translate → UI."""

import queue
import logging
import threading
from typing import Optional

from src.config import Config
from src.settings_store import load as load_settings
from src.audio.capture import AudioCapture
from src.audio.vad import VoiceActivityDetector
from src.ai.transcriber import Transcriber
from src.ai.transcription_validator import TranscriptionValidator
from src.ai.multi_translator import MultiTranslator
from src.ui.window import TranslatorUI
from src.app.factory import build_translator

logger = logging.getLogger(__name__)


class App:
    """Pipeline controller — không phụ thuộc vào bất kỳ UI framework cụ thể."""

    def __init__(
        self,
        ui: TranslatorUI,
        capture: AudioCapture,
        transcriber: Transcriber,
        translator: MultiTranslator,
        devices: list[dict],
    ):
        self._ui = ui
        self._capture = capture
        self._vad = VoiceActivityDetector()
        self._transcriber = transcriber
        self._translator = translator
        self._devices = devices

        self._audio_queue: queue.Queue[Optional[bytes]] = queue.Queue(maxsize=200)
        self._pipeline_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._ui._on_start = self._start_pipeline
        self._ui._on_stop = self._stop_pipeline_async
        self._ui._on_settings_changed = self._on_settings_changed

        self._ui.update_active_llm(self._translator.active_provider)
        self._update_start_btn()

        preferred = load_settings().get("preferred_device_index")
        if preferred is not None:
            for i, d in enumerate(devices):
                if d["index"] == preferred:
                    self._ui.select_device_index(i)
                    break

        if not self._transcriber.is_ready:
            self._ui.update_status("⏳  Đang tải Whisper model...")
        else:
            self._ui.update_status("⏸  Đang chờ")

        if self._translator.active_provider == "none":
            self._ui.update_status("❌  Chưa có translator khả dụng. Vui lòng cấu hình API key.")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _update_start_btn(self):
        available = self._translator.active_provider != "none"
        self._ui.set_start_enabled(
            available,
            "Bắt đầu dịch" if available
            else "Cần API key Gemini/OpenAI/Anthropic hoặc Ollama local để bắt đầu",
        )

    def _audio_callback(self, chunk: bytes):
        try:
            self._audio_queue.put_nowait(chunk)
        except queue.Full:
            pass

    def _pipeline_worker(self, device_index: Optional[int]):
        logger.info("Pipeline worker started")
        if not self._transcriber.is_ready:
            self._ui.update_status("⏳  Đang tải Whisper model, vui lòng chờ...")
            if not self._transcriber.wait_until_ready(timeout=120.0):
                self._ui.update_status("❌  Không tải được Whisper model")
                return

        self._ui.update_status("🎙  Đang nghe...")
        if not self._capture.start_capture(device_index=device_index, callback=self._audio_callback):
            self._ui.update_status("❌  Lỗi khởi động capture")
            return

        try:
            while not self._stop_event.is_set():
                speech_pcm = self._vad.get_speech_segment(self._audio_queue, self._stop_event)
                if speech_pcm is None:
                    break

                self._ui.update_status("📝  Đang nhận dạng...")
                text = self._transcriber.transcribe(
                    self._vad.pcm_to_float32(speech_pcm),
                    language=Config.WHISPER_LANGUAGE,
                )
                if not text:
                    self._ui.update_status("🎙  Đang nghe...")
                    continue

                is_valid, _, _ = TranscriptionValidator.validate(
                    text, min_confidence=Config.MIN_TRANSCRIPTION_CONFIDENCE,
                )
                if not is_valid:
                    self._ui.update_status("🎙  Đang nghe...")
                    continue

                self._ui.update_status("🌐  Đang dịch...")
                translation = self._translator.translate(text, target_lang=Config.TARGET_LANGUAGE)
                self._ui.update_active_llm(self._translator.active_provider)
                self._ui.update_translation(
                    original=text,
                    translated=translation or "(Lỗi dịch)",
                )
                self._ui.update_status("🎙  Đang nghe...")
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            self._ui.update_status(f"❌  Lỗi: {e}")
        finally:
            self._capture.stop_capture()
            logger.info("Pipeline worker stopped")

    def _start_pipeline(self, device_index: Optional[int]):
        self._stop_event.clear()
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
        self._pipeline_thread = threading.Thread(
            target=self._pipeline_worker,
            args=(device_index,),
            daemon=True,
            name="pipeline-worker",
        )
        self._pipeline_thread.start()

    def _stop_pipeline_async(self):
        def _do_stop():
            self._stop_event.set()
            try:
                self._audio_queue.put_nowait(None)
            except queue.Full:
                pass
            self._capture.stop_capture()
            if self._pipeline_thread and self._pipeline_thread.is_alive():
                self._pipeline_thread.join(timeout=6)
            logger.info("Pipeline stopped")
        threading.Thread(target=_do_stop, daemon=True, name="stopper").start()

    def _on_settings_changed(self, _new_settings: dict):
        Config.reload_with_keys()
        self._vad = VoiceActivityDetector()
        self._translator = build_translator()
        self._ui.update_active_llm(self._translator.active_provider)
        self._update_start_btn()
        if self._translator.active_provider == "none":
            self._ui.update_status("❌  Chưa có translator khả dụng. Vui lòng cấu hình API key.")
        logger.info("Settings updated — translator & VAD rebuilt")

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def shutdown(self):
        self._stop_event.set()
        try:
            self._audio_queue.put_nowait(None)
        except queue.Full:
            pass
        if self._pipeline_thread and self._pipeline_thread.is_alive():
            self._pipeline_thread.join(timeout=6)
        self._capture.close()
