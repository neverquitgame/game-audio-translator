import sys
import queue
import logging
import threading
import tkinter as tk
from typing import Optional

from src.keystore import has_api_key, get_api_key
from src.config import Config
from src.audio.capture import AudioCapture
from src.audio.vad import VoiceActivityDetector
from src.ai.transcriber import Transcriber
from src.ai.translator import Translator
from src.ui.window import TranslatorUI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _ensure_api_key() -> bool:
    """
    Nếu chưa có API key, hiện dialog nhập key trước khi mở app chính.
    Trả về True nếu đã có key (hoặc vừa được nhập), False nếu người dùng đóng dialog.
    """
    if has_api_key():
        return True

    # Tạo cửa sổ ẩn làm parent cho dialog
    root = tk.Tk()
    root.withdraw()

    key_saved = [False]

    def on_saved(key: str):
        Config.GEMINI_API_KEY = key
        key_saved[0] = True

    from src.ui.api_key_dialog import ApiKeyDialog
    dlg = ApiKeyDialog(root, on_saved=on_saved, is_first_run=True)
    root.wait_window(dlg)
    root.destroy()

    return key_saved[0]


class App:
    def __init__(self):
        # Reload key từ keyring vào Config (tránh cache cũ từ lúc import)
        Config.GEMINI_API_KEY = get_api_key() or Config.GEMINI_API_KEY

        errors = Config.validate()
        if errors:
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
        self._translator = Translator(api_key=Config.GEMINI_API_KEY, model=Config.GEMINI_MODEL)

        devices = self._capture.list_audio_devices()
        if not devices:
            logger.warning("No audio devices found — check permissions or drivers")

        self._ui = TranslatorUI(
            devices=devices,
            on_start=self._start_pipeline,
            on_stop=self._stop_pipeline,
            on_api_key_changed=self._on_api_key_changed,
        )

        # Thông báo đang load model ngay khi UI xuất hiện
        if not self._transcriber.is_ready:
            self._ui.update_status("⏳  Đang tải Whisper model...")

    def _on_model_ready(self):
        """Callback từ background thread khi Whisper model load xong."""
        logger.info("Whisper model sẵn sàng")
        self._ui.update_status("⏸  Đang chờ")

    def _on_model_error(self, error: str):
        """Callback khi load model thất bại."""
        logger.error(f"Không load được Whisper model: {error}")
        self._ui.update_status(f"❌  Lỗi tải model: {error}")

    def _audio_callback(self, audio_chunk: bytes):
        try:
            self._audio_queue.put_nowait(audio_chunk)
        except queue.Full:
            pass  # Drop oldest implicitly by skipping — avoids unbounded lag

    def _pipeline_worker(self, device_index: Optional[int]):
        """Background thread: VAD → Transcribe → Translate → UI."""
        logger.info("Pipeline worker started")

        # Chờ Whisper model load xong nếu chưa sẵn sàng
        if not self._transcriber.is_ready:
            self._ui.update_status("⏳  Đang tải Whisper model, vui lòng chờ...")
            ready = self._transcriber.wait_until_ready(timeout=120.0)
            if not ready:
                self._ui.update_status("❌  Không tải được Whisper model")
                return

        self._ui.update_status("🎙  Đang nghe...")

        started = self._capture.start_capture(device_index=device_index, callback=self._audio_callback)
        if not started:
            logger.error("Failed to start audio capture")
            self._ui.update_status("❌  Lỗi khởi động capture")
            return

        try:
            while not self._stop_event.is_set():
                speech_pcm = self._vad.get_speech_segment(self._audio_queue)

                if speech_pcm is None:
                    # None sentinel — shutdown requested
                    break

                self._ui.update_status("📝  Đang nhận dạng...")
                audio_float = self._vad.pcm_to_float32(speech_pcm)
                text = self._transcriber.transcribe(audio_float)

                if not text:
                    self._ui.update_status("🎙  Đang nghe...")
                    continue

                self._ui.update_status("🌐  Đang dịch...")
                translation = self._translator.translate(
                    text,
                    target_lang=Config.TARGET_LANGUAGE,
                )

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
        # Drain leftover chunks from a previous run
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

    def _on_api_key_changed(self, new_key: str):
        """Cập nhật key vào Config và khởi tạo lại Translator."""
        Config.GEMINI_API_KEY = new_key
        self._translator = Translator(api_key=new_key, model=Config.GEMINI_MODEL)
        logger.info("Translator đã được khởi tạo lại với key mới")

    def _stop_pipeline(self):
        self._stop_event.set()
        # Unblock the VAD's get_speech_segment queue wait
        self._audio_queue.put(None)
        self._capture.stop_capture()
        if self._pipeline_thread and self._pipeline_thread.is_alive():
            self._pipeline_thread.join(timeout=5)
        logger.info("Pipeline stopped")

    def run(self):
        self._ui.run()
        # Explicit teardown after UI closes — prevents double-free in pa.terminate()
        # during Python GC on macOS CoreAudio AUHAL backend
        self._stop_pipeline()
        self._capture.close()


if __name__ == "__main__":
    if not _ensure_api_key():
        logger.warning("Không có API key — thoát ứng dụng")
        sys.exit(0)

    app = App()
    app.run()
