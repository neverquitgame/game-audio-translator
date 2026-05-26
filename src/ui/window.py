"""Cửa sổ chính — wires header bar + 3 tabs lại với nhau."""

import logging
from typing import Callable, Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTabWidget, QApplication,
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer
from PySide6.QtGui import QShortcut, QKeySequence

from src.settings_store import load as load_settings
from src.ui.styles import APP_STYLE, STATUS_BASE, WIN_W, WIN_H, WIN_MIN_W, WIN_MIN_H
from src.ui.tabs.translate_tab import TranslateTab
from src.ui.tabs.history_tab import HistoryTab
from src.ui.tabs.settings_tab import SettingsTab

logger = logging.getLogger(__name__)


class _Signals(QObject):
    """Cross-thread signals để update UI an toàn từ worker thread."""
    status_changed = Signal(str)
    translation_ready = Signal(str, str)
    llm_changed = Signal(str)


class TranslatorUI(QMainWindow):
    def __init__(
        self,
        devices: list[dict],
        on_start: Callable[[Optional[int]], None],
        on_stop: Callable[[], None],
        on_settings_changed: Optional[Callable[[dict], None]] = None,
    ):
        super().__init__()
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_settings_changed = on_settings_changed
        self._running = False
        self._devices = devices
        self._settings = load_settings()
        self._signals = _Signals()

        self._signals.status_changed.connect(self._apply_status)
        self._signals.translation_ready.connect(self._apply_translation)
        self._signals.llm_changed.connect(self._apply_llm)

        self.setWindowTitle("Game Audio Translator")
        self.setMinimumSize(WIN_MIN_W, WIN_MIN_H)
        self.resize(WIN_W, WIN_H)
        self.setStyleSheet(APP_STYLE)

        if self._settings.get("always_on_top", True):
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.tabBar().setElideMode(Qt.ElideNone)
        self._tabs.tabBar().setExpanding(False)
        root.addWidget(self._tabs)

        self._status_label = QLabel("⏸  Đang chờ")
        self._status_label.setObjectName("statusBar")
        self._status_label.setFixedHeight(28)
        root.addWidget(self._status_label)

        self._translate_tab = TranslateTab(on_status_update=self.update_status)
        self._history_tab = HistoryTab()
        self._settings_tab = SettingsTab(
            settings=self._settings,
            on_save=self._on_settings_saved,
            on_always_on_top=self._on_always_on_top_toggled,
        )
        self._tabs.addTab(self._translate_tab, "🎙 Dịch")
        self._tabs.addTab(self._history_tab, "📜 Lịch sử")
        self._tabs.addTab(self._settings_tab, "⚙ Cài đặt")

        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(self._on_toggle)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self).activated.connect(
            self._translate_tab._copy_translation
        )
        QShortcut(QKeySequence("Ctrl+H"), self).activated.connect(
            lambda: self._tabs.setCurrentIndex(1)
        )

        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - WIN_W) // 2,
            (screen.height() - WIN_H) // 2,
        )

    # ── Header bar ────────────────────────────────────────────────────────────

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("headerBar")
        header.setFixedHeight(52)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(8)

        device_label = QLabel("Thiết bị:")
        device_label.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: bold;")

        self._device_combo = QComboBox()
        names = (
            [
                f"{d['name']} ({d['default_sample_rate']} Hz)" if d.get("default_sample_rate") else d["name"]
                for d in self._devices
            ]
            if self._devices
            else ["(Không có thiết bị)"]
        )
        self._device_combo.addItems(names)
        self._device_combo.setMinimumWidth(220)
        self._device_combo.setFixedHeight(34)

        self._toggle_btn = QPushButton("▶  Bắt đầu")
        self._toggle_btn.setObjectName("btnStart")
        self._toggle_btn.setFixedHeight(34)
        self._toggle_btn.setMinimumWidth(120)
        self._toggle_btn.setToolTip("Bắt đầu / Dừng  (Ctrl+Enter)")
        self._toggle_btn.clicked.connect(self._on_toggle)
        if not self._devices:
            self._toggle_btn.setEnabled(False)
            self._toggle_btn.setToolTip("Không tìm thấy thiết bị âm thanh")

        self._llm_label = QLabel("⚪  Chưa kết nối")
        self._llm_label.setObjectName("llmBadgeEmpty")

        layout.addWidget(device_label, 0, Qt.AlignVCenter)
        layout.addWidget(self._device_combo, 0, Qt.AlignVCenter)
        layout.addWidget(self._toggle_btn, 0, Qt.AlignVCenter)
        layout.addStretch()
        layout.addWidget(self._llm_label, 0, Qt.AlignVCenter)
        return header

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_toggle(self):
        if not self._toggle_btn.isEnabled() and not self._running:
            return
        if not self._running:
            idx = self._device_combo.currentIndex()
            device_index = (
                self._devices[idx]["index"]
                if self._devices and 0 <= idx < len(self._devices)
                else None
            )
            self._running = True
            self._toggle_btn.setObjectName("btnStop")
            self._toggle_btn.setText("■  Dừng")
            self._toggle_btn.style().unpolish(self._toggle_btn)
            self._toggle_btn.style().polish(self._toggle_btn)
            self._device_combo.setEnabled(False)
            self._translate_tab.clear_processing()
            self.update_status("🎙  Đang nghe...")
            self._on_start(device_index)
        else:
            self._running = False
            self._toggle_btn.setObjectName("btnStart")
            self._toggle_btn.setText("▶  Bắt đầu")
            self._toggle_btn.style().unpolish(self._toggle_btn)
            self._toggle_btn.style().polish(self._toggle_btn)
            self._device_combo.setEnabled(True)
            self._translate_tab.clear_processing()
            self.update_status("⏸  Đang chờ")
            self._on_stop()

    def _on_settings_saved(self, new_settings: dict):
        self._settings = new_settings
        if self._on_settings_changed:
            self._on_settings_changed(new_settings)

    def _on_always_on_top_toggled(self, checked: bool):
        flags = self.windowFlags()
        if checked:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()

    # ── Public API (thread-safe via signals) ──────────────────────────────────

    def update_status(self, status: str):
        self._signals.status_changed.emit(status)

    def update_translation(self, original: str, translated: str):
        self._signals.translation_ready.emit(original, translated)

    def update_active_llm(self, provider: str):
        self._signals.llm_changed.emit(provider)

    def select_device_index(self, combo_index: int):
        if self._devices and 0 <= combo_index < len(self._devices):
            self._device_combo.setCurrentIndex(combo_index)

    def set_start_enabled(self, enabled: bool, tooltip: str | None = None):
        self._toggle_btn.setEnabled(enabled)
        if tooltip is not None:
            self._toggle_btn.setToolTip(tooltip)
        elif not enabled:
            self._toggle_btn.setToolTip("Cần API key hoặc Ollama local để bắt đầu")

    # ── Signal slots (main thread) ────────────────────────────────────────────

    def _apply_status(self, status: str):
        if not status:
            return
        self._status_label.setText(status)

        if "❌" in status:
            color = "#f38ba8"
        elif "🎙" in status:
            color = "#a6e3a1"
        elif "📝" in status or "🌐" in status or "⏳" in status:
            color = "#f9e2af"
            if "🌐" in status:
                self._translate_tab.set_processing("⏳ Đang dịch...")
            elif "📝" in status:
                self._translate_tab.set_processing("🎤 Đang nhận dạng...")
        elif "📋" in status:
            color = "#89b4fa"
        else:
            color = "#6c7086"

        if "⏸" in status or "🎙" in status:
            self._translate_tab.clear_processing()

        self._status_label.setStyleSheet(f"{STATUS_BASE}color: {color};")

    def _apply_translation(self, original: str, translated: str):
        self._translate_tab.set_texts(original, translated)
        self._history_tab.add_entry(original, translated)

    def _apply_llm(self, provider: str):
        if provider and provider.lower() != "none":
            self._llm_label.setText(f"🟢  {provider}")
            self._llm_label.setObjectName("llmBadge")
        else:
            self._llm_label.setText("⚪  Chưa kết nối")
            self._llm_label.setObjectName("llmBadgeEmpty")
        self._llm_label.style().unpolish(self._llm_label)
        self._llm_label.style().polish(self._llm_label)
