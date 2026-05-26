"""Bootstrap — loading screen → onboarding (lần đầu) → cửa sổ chính."""

import logging
import threading
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QObject, Signal

from src.config import Config
from src.settings_store import load as load_settings
from src.audio.capture import AudioCapture
from src.ai.transcriber import Transcriber
from src.ui.window import TranslatorUI
from src.ui.loading_screen import LoadingScreen
from src.ui.onboarding import OnboardingWizard
from src.app.factory import build_translator
from src.app.pipeline import App

logger = logging.getLogger(__name__)


class _Signals(QObject):
    init_complete = Signal()
    init_failed = Signal(str)
    status_changed = Signal(str)


class Bootstrap:
    """Orchestrates startup: loading → onboarding → Whisper load → main window."""

    def __init__(self, qt_app: QApplication):
        self._qt = qt_app
        self._loading: Optional[LoadingScreen] = None
        self._init_result: Optional[dict] = None
        self._app: Optional[App] = None
        self._ui: Optional[TranslatorUI] = None
        self._wizard: Optional[OnboardingWizard] = None

        self._sig = _Signals()
        self._sig.init_complete.connect(self._on_init_complete)
        self._sig.init_failed.connect(self._on_init_failed)
        self._sig.status_changed.connect(self._apply_status)

    def run(self):
        self._loading = LoadingScreen()
        self._loading.show()
        QTimer.singleShot(80, self._start_init)
        self._qt.exec()

    # ── Phase 1: quét device + API key (nhanh) ────────────────────────────────

    def _start_init(self):
        threading.Thread(target=self._init_worker, daemon=True, name="bootstrap").start()

    def _apply_status(self, msg: str):
        if self._loading:
            self._loading.set_status(msg)

    def _init_worker(self):
        try:
            self._sig.status_changed.emit("Đang tải cấu hình...")
            Config.reload()
            Config.reload_api_keys(only_priority=True)

            self._sig.status_changed.emit("Đang quét thiết bị âm thanh...")
            capture = AudioCapture()
            devices = capture.list_audio_devices()
            if not devices:
                logger.warning("No audio devices found")

            self._init_result = {"capture": capture, "devices": devices, "transcriber": None}
            self._sig.init_complete.emit()
        except Exception as e:
            logger.exception("Bootstrap init failed")
            self._sig.init_failed.emit(str(e))

    def _on_init_failed(self, error: str):
        if self._loading:
            self._loading.set_status(f"❌ Lỗi: {error}")

    # ── Phase 2: onboarding (tuỳ chọn) ───────────────────────────────────────

    def _on_init_complete(self):
        settings = load_settings()
        if not settings.get("onboarding_completed"):
            if self._loading:
                self._loading.close_loading()
            self._wizard = OnboardingWizard(
                devices=self._init_result["devices"],
                on_complete=self._after_onboarding,
            )
            self._wizard.show()
            self._wizard.raise_()
            self._wizard.activateWindow()
        else:
            self._after_onboarding()

    # ── Phase 3: load Whisper (dùng model user thật sự chọn) ──────────────────

    def _after_onboarding(self):
        Config.reload()
        Config.reload_api_keys(only_priority=False)

        if not self._loading or not self._loading.isVisible():
            self._loading = LoadingScreen()
            self._loading.show()
        self._loading.set_status(f"Đang tải Whisper ({Config.WHISPER_MODEL})...")

        def _load():
            t = Transcriber(
                model_size=Config.WHISPER_MODEL,
                on_error=lambda e: logger.error(f"Whisper error: {e}"),
            )
            t.wait_until_ready(timeout=300.0)
            self._init_result["transcriber"] = t
            QTimer.singleShot(0, self._launch)

        threading.Thread(target=_load, daemon=True, name="whisper-loader").start()

    # ── Phase 4: mở cửa sổ chính ─────────────────────────────────────────────

    def _launch(self):
        try:
            self._launch_inner()
        except Exception:
            logger.exception("_launch failed")

    def _launch_inner(self):
        if self._loading:
            self._loading.close_loading()

        r = self._init_result
        self._ui = TranslatorUI(
            devices=r["devices"],
            on_start=lambda idx: None,
            on_stop=lambda: None,
            on_settings_changed=None,
        )
        self._app = App(
            ui=self._ui,
            capture=r["capture"],
            transcriber=r["transcriber"],
            translator=build_translator(),
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
