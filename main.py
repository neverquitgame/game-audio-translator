import sys
import queue
import logging
import threading
import tkinter as tk
from typing import Optional

from src.keystore import has_api_key, get_api_key
from src.config import Config
from src.settings_store import load as load_settings
from src.audio.capture import AudioCapture
from src.audio.vad import VoiceActivityDetector
from src.ai.transcriber import Transcriber
from src.ai.translators.gemini import GeminiTranslator
from src.ai.translators.openai_t import OpenAITranslator
from src.ai.translators.anthropic_t import AnthropicTranslator
from src.ai.translators.ollama_t import OllamaTranslator
from src.ai.multi_translator import MultiTranslator
from src.ui.window import TranslatorUI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _build_translator() -> MultiTranslator:
    Config.reload()
    priority = Config.LLM_PRIORITY

    all_translators = {
        "gemini": GeminiTranslator(api_key=Config.GEMINI_API_KEY, model=Config.GEMINI_MODEL),
        "openai": OpenAITranslator(api_key=Config.OPENAI_API_KEY),
        "anthropic": AnthropicTranslator(api_key=Config.ANTHROPIC_API_KEY),
        "ollama": OllamaTranslator(),
    }

    ordered = []
    for name in priority:
        if name in all_translators:
            ordered.append(all_translators[name])
    for name, t in all_translators.items():
        if name not in priority:
            ordered.append(t)

    return MultiTranslator(ordered)


class App:
    def __init__(self):
        Config.reload()

        errors = Config.validate()
        for err in errors:
            logger.warning(f"Config warning: {err}")

        self._audio_queue: queue.Queue[Optional[bytes]] = queue.Queue(maxsize=200)
        self._pipeline_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._capture = AudioCapture()
        self._vad = VoiceActivityDetector()
        self._transcriber = Transcriber(
            model_size=Config.WHISPER_MODEL,
            on_ready=self._on_model_ready,
            on_error=self._on_model_error,
        )
        self._translator = _build_translator()

        devices = self._capture.list_audio_devices()
        if not devices:
            logger.warning("No audio devices found")

        self._ui = TranslatorUI(
            devices=devices,
            on_start=self._start_pipeline,
            on_stop=self._stop_pipeline,
            on_settings_changed=self._on_settings_changed,
        )

        self._ui.update_active_llm(self._translator.active_provider)

        if not self._transcriber.is_ready:
            self._ui.update_status("⏳  Đang tải Whisper model...")

        has_any_key = any(has_api_key(p) for p in ["gemini", "openai", "anthropic"])
        if not has_any_key:
            self._ui.root.after(300, lambda: self._ui._notebook.select(1))
            self._ui.update_status("⚠  Chưa có API key — vui lòng cài đặt trong tab ⚙")

    def _on_model_ready(self):
        logger.info("Whisper model sẵn sàng")
        self._ui.update_status("⏸  Đang chờ")

    def _on_model_error(self, error: str):
        logger.error(f"Không load được Whisper model: {error}")
        self._ui.update_status(f"❌  Lỗi tải model: {error}")

    def _audio_callback(self, audio_chunk: bytes):
        try:
            self._audio_queue.put_nowait(audio_chunk)
        except queue.Full:
            pass

    def _pipeline_worker(self, device_index: Optional[int]):
        logger.info("Pipeline worker started")

        if not self._transcriber.is_ready:
            self._ui.update_status("⏳  Đang tải Whisper model, vui lòng chờ...")
            ready = self._transcriber.wait_until_ready(timeout=120.0)
            if not ready:
                self._ui.update_status("❌  Không tải được Whisper model")
                return

        self._ui.update_status("🎙  Đang nghe...")

        started = self._capture.start_capture(device_index=device_index, callback=self._audio_callback)
        if not started:
            self._ui.update_status("❌  Lỗi khởi động capture")
            return

        try:
            while not self._stop_event.is_set():
                speech_pcm = self._vad.get_speech_segment(self._audio_queue)
                if speech_pcm is None:
                    break

                self._ui.update_status("📝  Đang nhận dạng...")
                audio_float = self._vad.pcm_to_float32(speech_pcm)
                text = self._transcriber.transcribe(audio_float, language=Config.WHISPER_LANGUAGE)

                if not text:
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

    def _stop_pipeline(self):
        self._stop_event.set()
        self._audio_queue.put(None)
        self._capture.stop_capture()
        if self._pipeline_thread and self._pipeline_thread.is_alive():
            self._pipeline_thread.join(timeout=5)
        logger.info("Pipeline stopped")

    def _on_settings_changed(self, new_settings: dict):
        """Rebuild translator sau khi user thay đổi settings trong UI."""
        Config.reload()
        self._translator = _build_translator()
        self._ui.update_active_llm(self._translator.active_provider)
        logger.info("Settings updated, translator rebuilt")

    def run(self):
        self._ui.run()
        self._stop_pipeline()
        self._capture.close()


if __name__ == "__main__":
    app = App()
    app.run()
