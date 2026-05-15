import sys
import queue
import logging
import threading
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QObject, Signal

from src.config import Config
from src.settings_store import load as load_settings
from src.audio.capture import AudioCapture
from src.audio.vad import VoiceActivityDetector
from src.ai.transcriber import Transcriber
from src.ai.translators.litellm_t import LiteLLMTranslator
from src.ai.multi_translator import MultiTranslator
from src.ui.window import TranslatorUI
from src.ui.loading_screen import LoadingScreen
from src.ui.onboarding import OnboardingWizard

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
        "gemini": LiteLLMTranslator(
            model=f"gemini/{Config.GEMINI_MODEL}",
            api_key=Config.GEMINI_API_KEY,
            name="gemini",
        ),
        "openai": LiteLLMTranslator(
            model="gpt-4o-mini",
            api_key=Config.OPENAI_API_KEY,
            name="openai",
        ),
        "anthropic": LiteLLMTranslator(
            model="anthropic/claude-haiku-4-5",
            api_key=Config.ANTHROPIC_API_KEY,
            name="anthropic",
        ),
        "ollama": LiteLLMTranslator(
            model="ollama/llama3.2",
            name="ollama",
        ),
    }
    ordered = [all_translators[n] for n in priority if n in all_translators]
    ordered += [t for n, t in all_translators.items() if n not in priority]
    return MultiTranslator(ordered)


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

        # Register UI callbacks
        self._ui._on_start = self._start_pipeline
        self._ui._on_stop = self._stop_pipeline_async
        self._ui._on_settings_changed = self._on_settings_changed

        self._ui.update_active_llm(self._translator.active_provider)

        settings = load_settings()
        preferred = settings.get("preferred_device_index")
        if preferred is not None:
            for i, d in enumerate(devices):
                if d["index"] == preferred:
                    self._ui.select_device_index(i)
                    break

        if not self._transcriber.is_ready:
            self._ui.update_status("⏳  Đang tải Whisper model...")
        else:
            self._ui.update_status("⏸  Đang chờ")

    # ── Pipeline ──────────────────────────────────────────────────────────────

    def _audio_callback(self, audio_chunk: bytes):
        try:
            self._audio_queue.put_nowait(audio_chunk)
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
        started = self._capture.start_capture(
            device_index=device_index, callback=self._audio_callback,
        )
        if not started:
            self._ui.update_status("❌  Lỗi khởi động capture")
            return

        try:
            while not self._stop_event.is_set():
                speech_pcm = self._vad.get_speech_segment(self._audio_queue)
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

                self._ui.update_status("🌐  Đang dịch...")
                translation = self._translator.translate(
                    text, target_lang=Config.TARGET_LANGUAGE,
                )
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
        """Dừng pipeline trong thread riêng — không bao giờ block UI."""
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

    def shutdown(self):
        self._stop_event.set()
        try:
            self._audio_queue.put_nowait(None)
        except queue.Full:
            pass
        if self._pipeline_thread and self._pipeline_thread.is_alive():
            self._pipeline_thread.join(timeout=6)
        self._capture.close()

    def _on_settings_changed(self, new_settings: dict):
        Config.reload()
        self._translator = _build_translator()
        self._ui.update_active_llm(self._translator.active_provider)
        logger.info("Settings updated, translator rebuilt")


class _BootstrapSignals(QObject):
    """Signals dùng để giao tiếp an toàn từ background thread → main thread."""
    init_complete = Signal()
    init_failed = Signal(str)
    status_changed = Signal(str)


class Bootstrap:
    """Hiển thị loading → onboarding (lần đầu) → cửa sổ chính."""

    def __init__(self, qt_app: QApplication):
        self._qt = qt_app
        self._loading: Optional[LoadingScreen] = None
        self._init_result: Optional[dict] = None
        self._app: Optional[App] = None
        self._ui: Optional[TranslatorUI] = None

        # QObject phải được tạo trên main thread — wire signals ở đây
        self._signals = _BootstrapSignals()
        self._signals.init_complete.connect(self._on_init_complete)
        self._signals.init_failed.connect(self._on_init_failed)
        self._signals.status_changed.connect(self._apply_status)

    def run(self):
        self._loading = LoadingScreen()
        self._loading.show()
        QTimer.singleShot(80, self._start_init)
        self._qt.exec()

    def _start_init(self):
        threading.Thread(target=self._init_worker, daemon=True, name="bootstrap").start()

    def _set_status(self, msg: str):
        self._signals.status_changed.emit(msg)

    def _apply_status(self, msg: str):
        if self._loading:
            self._loading.set_status(msg)

    def _init_worker(self):
        try:
            self._set_status("Đang tải cấu hình...")
            Config.reload()

            self._set_status("Đang quét thiết bị âm thanh...")
            capture = AudioCapture()
            devices = capture.list_audio_devices()
            if not devices:
                logger.warning("No audio devices found")

            self._set_status("Đang tải Whisper model (lần đầu có thể mất vài phút)...")
            transcriber = Transcriber(
                model_size=Config.WHISPER_MODEL,
                on_ready=lambda: None,
                on_error=lambda e: logger.error(f"Whisper error: {e}"),
            )
            transcriber.wait_until_ready(timeout=300.0)

            self._set_status("Đang chuẩn bị bộ dịch...")
            translator = _build_translator()

            self._init_result = {
                "capture": capture,
                "devices": devices,
                "transcriber": transcriber,
                "translator": translator,
            }
            self._signals.init_complete.emit()
        except Exception as e:
            logger.exception("Bootstrap init failed")
            self._signals.init_failed.emit(str(e))

    def _on_init_failed(self, error: str):
        if self._loading:
            self._loading.set_status(f"❌ Lỗi: {error}")

    def _on_init_complete(self):
        if self._loading:
            self._loading.close_loading()

        settings = load_settings()
        if not settings.get("onboarding_completed"):
            wizard = OnboardingWizard(
                devices=self._init_result["devices"],
                on_complete=self._launch_main_app,
            )
            wizard.show()
            wizard.raise_()
            wizard.activateWindow()
        else:
            self._launch_main_app()

    def _launch_main_app(self):
        try:
            self._launch_main_app_inner()
        except Exception as e:
            logger.exception(f"_launch_main_app failed: {e}")

    def _launch_main_app_inner(self):
        r = self._init_result
        Config.reload()

        transcriber = r["transcriber"]
        if transcriber.model_size != Config.WHISPER_MODEL:
            logger.info("Whisper model thay đổi sau thiết lập — đang tải lại...")
            loading2 = LoadingScreen()
            loading2.show()
            loading2.set_status(f"Đang tải Whisper ({Config.WHISPER_MODEL})...")
            new_t = Transcriber(model_size=Config.WHISPER_MODEL)
            ready = new_t.wait_until_ready(timeout=300.0)
            loading2.close_loading()
            if not ready:
                logger.error(
                    f"Không tải được Whisper model '{Config.WHISPER_MODEL}' — "
                    f"tiếp tục với model cũ '{transcriber.model_size}'"
                )
            else:
                r["transcriber"] = new_t
                transcriber = new_t

        self._ui = TranslatorUI(
            devices=r["devices"],
            on_start=lambda idx: None,  # overridden by App.__init__
            on_stop=lambda: None,
            on_settings_changed=None,
        )
        self._app = App(
            ui=self._ui,
            capture=r["capture"],
            transcriber=transcriber,
            translator=_build_translator(),
            devices=r["devices"],
        )
        self._ui.show()
        self._ui.raise_()
        self._ui.activateWindow()
        self._qt.setQuitOnLastWindowClosed(True)
        self._qt.aboutToQuit.connect(self._on_quit)

    def _on_quit(self):
        if self._app:
            self._app.shutdown()


def main():
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("GameAudioTranslator")
    qt_app.setOrganizationName("Silotech")
    qt_app.setQuitOnLastWindowClosed(False)
    Bootstrap(qt_app).run()


if __name__ == "__main__":
    main()
