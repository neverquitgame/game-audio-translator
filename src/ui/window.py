"""Cửa sổ chính dùng PySide6."""

import logging
import threading
from typing import Callable, Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit,
    QTabWidget, QFrame, QScrollArea, QSlider,
    QLineEdit, QApplication, QMessageBox, QListWidget, QCheckBox,
)
from PySide6.QtCore import Qt, Signal, QObject, QTimer, QDateTime
from PySide6.QtGui import QFont, QTextCursor, QShortcut, QKeySequence

from src.settings_store import load as load_settings, save as save_settings
from src.keystore import get_api_key, save_api_key

logger = logging.getLogger(__name__)

_WIN_W = 660
_WIN_H = 600
_WIN_MIN_W = 560
_WIN_MIN_H = 480

_STATUS_BASE = "background-color: #13131f; font-size: 11px; padding: 4px 12px; border-top: 1px solid #2a2a3d;"

_STYLE = """
QMainWindow, QWidget#central {
    background-color: #1e1e2e;
}
/* ── Tabs ── */
QTabWidget::pane {
    border: none;
    background-color: #1e1e2e;
}
QTabBar::tab {
    background-color: transparent;
    color: #9399b2;
    padding: 9px 20px;
    font-weight: bold;
    font-size: 12px;
    border: none;
    margin: 0;
    min-width: 80px;
}
QTabBar::tab:selected {
    background-color: transparent;
    color: #cdd6f4;
    border-bottom: 2px solid #89b4fa;
}
QTabBar::tab:hover:!selected {
    background-color: #252537;
    color: #cdd6f4;
}
/* ── Header bar ── */
QWidget#headerBar {
    background-color: #181826;
    border-bottom: 1px solid #2a2a3d;
}
QLabel#llmBadge {
    color: #a6e3a1;
    font-size: 10px;
    font-weight: bold;
    background-color: #1e3a2e;
    border: 1px solid #2d5a3d;
    border-radius: 4px;
    padding: 3px 10px;
}
QLabel#llmBadgeEmpty {
    color: #6c7086;
    font-size: 10px;
    background-color: transparent;
    padding: 3px 10px;
}
QFrame#tabBarStrip {
    background-color: #181826;
    border-bottom: 1px solid #2a2a3d;
}
/* ── Labels ── */
QLabel {
    color: #cdd6f4;
    background: transparent;
}
/* ── Buttons ── */
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: bold;
    font-size: 11px;
}
QPushButton:hover { background-color: #45475a; }
QPushButton:pressed { background-color: #585b70; }
QPushButton#btnStart {
    background-color: #a6e3a1;
    color: #1e1e2e;
}
QPushButton#btnStart:hover { background-color: #94e2d5; }
QPushButton#btnStop {
    background-color: #f38ba8;
    color: #1e1e2e;
}
QPushButton#btnStop:hover { background-color: #eba0ac; }
QPushButton#btnSave {
    background-color: #89b4fa;
    color: #1e1e2e;
}
QPushButton#btnSave:hover { background-color: #74c7ec; }
/* ── ComboBox ── */
QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 5px 10px;
    min-width: 120px;
}
QComboBox:focus { border: 1px solid #89b4fa; }
QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    selection-background-color: #45475a;
    border: 1px solid #45475a;
    outline: none;
}
QComboBox::drop-down { border: none; width: 20px; }
/* ── Text box ── */
QTextEdit {
    background-color: #2a2a3d;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 8px;
    font-size: 12px;
    selection-background-color: #45475a;
}
/* ── Line edit (API keys) ── */
QLineEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 5px 10px;
    font-family: "Consolas", monospace;
    font-size: 11px;
}
QLineEdit:focus { border: 1px solid #89b4fa; }
/* ── Slider ── */
QSlider::groove:horizontal {
    background-color: #313244;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: #89b4fa;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::sub-page:horizontal {
    background-color: #89b4fa;
    border-radius: 2px;
}
/* ── List widget (LLM priority) ── */
QListWidget {
    background-color: #2a2a3d;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    font-size: 11px;
    outline: none;
}
QListWidget::item {
    padding: 5px 10px;
}
QListWidget::item:selected {
    background-color: #45475a;
    color: #cdd6f4;
}
QListWidget::item:hover:!selected {
    background-color: #313244;
}
/* ── Checkbox ── */
QCheckBox {
    color: #cdd6f4;
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #45475a;
    background-color: #313244;
}
QCheckBox::indicator:checked {
    background-color: #89b4fa;
    border: 1px solid #89b4fa;
}
/* ── Scroll ── */
QScrollArea { border: none; background-color: #1e1e2e; }
QScrollBar:vertical {
    background-color: #1e1e2e;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #45475a;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
/* ── Status bar ── */
QLabel#statusBar {
    background-color: #13131f;
    color: #6c7086;
    font-size: 11px;
    padding: 4px 12px;
    border-top: 1px solid #2a2a3d;
}
"""


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
        self._api_keys_cache: dict[str, str] = {}
        self._signals = _Signals()

        # Wire cross-thread signals
        self._signals.status_changed.connect(self._apply_status)
        self._signals.translation_ready.connect(self._apply_translation)
        self._signals.llm_changed.connect(self._apply_llm)

        self.setWindowTitle("Game Audio Translator")
        self.setMinimumSize(_WIN_MIN_W, _WIN_MIN_H)
        self.resize(_WIN_W, _WIN_H)

        # Apply always-on-top from settings (default True)
        if self._settings.get("always_on_top", True):
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self.setStyleSheet(_STYLE)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Header bar ─────────────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("headerBar")
        header.setFixedHeight(52)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(14, 0, 14, 0)
        header_layout.setSpacing(8)

        device_label = QLabel("Thiết bị:")
        device_label.setStyleSheet("color: #6c7086; font-size: 11px; font-weight: bold;")

        self._device_combo = QComboBox()
        names = [d["name"] for d in self._devices] if self._devices else ["(Không có thiết bị)"]
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

        header_layout.addWidget(device_label, 0, Qt.AlignVCenter)
        header_layout.addWidget(self._device_combo, 0, Qt.AlignVCenter)
        header_layout.addWidget(self._toggle_btn, 0, Qt.AlignVCenter)
        header_layout.addStretch()
        header_layout.addWidget(self._llm_label, 0, Qt.AlignVCenter)
        root_layout.addWidget(header)

        # ── Tabs ──────────────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.tabBar().setElideMode(Qt.ElideNone)
        self._tabs.tabBar().setExpanding(False)
        root_layout.addWidget(self._tabs)

        self._status_label = QLabel("⏸  Đang chờ")
        self._status_label.setObjectName("statusBar")
        self._status_label.setFixedHeight(28)
        root_layout.addWidget(self._status_label)

        self._build_translate_tab()
        self._build_history_tab()
        self._build_settings_tab()

        # Keyboard shortcuts
        QShortcut(QKeySequence("Ctrl+Return"), self).activated.connect(self._on_toggle)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self).activated.connect(self._copy_translation)
        QShortcut(QKeySequence("Ctrl+H"), self).activated.connect(
            lambda: self._tabs.setCurrentIndex(1)
        )

        # Pre-fetch API keys in background so settings tab opens instantly
        threading.Thread(target=self._prefetch_api_keys, daemon=True).start()

        # Center window
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - _WIN_W) // 2,
            (screen.height() - _WIN_H) // 2,
        )

    # ── Tab: Dịch ─────────────────────────────────────────────────────────────

    def _build_translate_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(0)

        # ── Nhận dạng (gốc) ──────────────────────────────────────────────────
        orig_header = QHBoxLayout()
        orig_lbl = QLabel("VĂN BẢN GỐC")
        orig_lbl.setStyleSheet("color: #6c7086; font-weight: bold; font-size: 10px; letter-spacing: 1px;")
        orig_header.addWidget(orig_lbl)
        orig_header.addStretch()
        layout.addLayout(orig_header)
        layout.addSpacing(6)

        self._original_box = QTextEdit()
        self._original_box.setReadOnly(True)
        self._original_box.setMinimumHeight(130)
        self._original_box.setPlaceholderText("Nhấn ▶ Bắt đầu rồi nói để xem văn bản nhận dạng tại đây...")
        self._original_box.setStyleSheet(
            "QTextEdit { background-color: #252537; border-radius: 8px; padding: 10px; "
            "font-size: 13px; color: #cdd6f4; border: 1px solid #2a2a3d; }"
        )
        layout.addWidget(self._original_box, 1)

        layout.addSpacing(12)

        # ── Bản dịch ─────────────────────────────────────────────────────────
        trans_header = QHBoxLayout()
        trans_lbl = QLabel("BẢN DỊCH")
        trans_lbl.setStyleSheet("color: #6c7086; font-weight: bold; font-size: 10px; letter-spacing: 1px;")
        self._processing_label = QLabel("")
        self._processing_label.setStyleSheet("color: #f9e2af; font-size: 10px;")
        trans_header.addWidget(trans_lbl)
        trans_header.addWidget(self._processing_label)
        trans_header.addStretch()
        layout.addLayout(trans_header)
        layout.addSpacing(6)

        self._translated_box = QTextEdit()
        self._translated_box.setReadOnly(True)
        self._translated_box.setMinimumHeight(130)
        self._translated_box.setPlaceholderText("Bản dịch sẽ xuất hiện ở đây sau khi nhận dạng xong...")
        self._translated_box.setStyleSheet(
            "QTextEdit { background-color: #1a2a1a; border-radius: 8px; padding: 10px; "
            "font-size: 13px; color: #cdd6f4; border: 1px solid #2d3d2d; }"
        )
        layout.addWidget(self._translated_box, 1)

        layout.addSpacing(10)

        # ── Toolbar dưới ─────────────────────────────────────────────────────
        copy_row = QHBoxLayout()
        shortcut_hint = QLabel("Ctrl+Enter  Bắt đầu/Dừng     Ctrl+Shift+C  Copy")
        shortcut_hint.setStyleSheet("color: #585b70; font-size: 10px;")
        copy_row.addWidget(shortcut_hint, 1)
        self._copy_btn = QPushButton("📋  Copy bản dịch")
        self._copy_btn.setFixedHeight(32)
        self._copy_btn.setMinimumWidth(140)
        self._copy_btn.setToolTip("Copy bản dịch  (Ctrl+Shift+C)")
        self._copy_btn.clicked.connect(self._copy_translation)
        copy_row.addWidget(self._copy_btn)
        layout.addLayout(copy_row)

        self._tabs.addTab(tab, "🎙 Dịch")

    # ── Tab: Lịch sử ──────────────────────────────────────────────────────────

    def _build_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(6)

        header_row = QHBoxLayout()
        hist_lbl = QLabel("Lịch sử dịch")
        hist_lbl.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 10px;")
        self._history_count_lbl = QLabel("0 mục")
        self._history_count_lbl.setStyleSheet("color: #6c7086; font-size: 10px;")
        clear_btn = QPushButton("🗑  Xóa lịch sử")
        clear_btn.setFixedHeight(26)
        clear_btn.clicked.connect(self._clear_history)
        header_row.addWidget(hist_lbl)
        header_row.addWidget(self._history_count_lbl)
        header_row.addStretch()
        header_row.addWidget(clear_btn)
        layout.addLayout(header_row)

        self._history_box = QTextEdit()
        self._history_box.setReadOnly(True)
        self._history_box.setPlaceholderText("Chưa có lịch sử dịch. Bắt đầu dịch để xem lịch sử tại đây...")
        layout.addWidget(self._history_box, 1)

        self._tabs.addTab(tab, "📜 Lịch sử")

    # ── Tab: Cài đặt ──────────────────────────────────────────────────────────

    def _build_settings_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setStyleSheet("background-color: #1e1e2e;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(4)

        # ── API Keys ─────────────────────────────────────────────────────────
        self._add_section_header(layout, "🔑  API Keys")
        self._api_key_entries: dict[str, QLineEdit] = {}
        self._api_key_status: dict[str, QLabel] = {}

        for provider, label_text in [("gemini", "Gemini"), ("openai", "OpenAI"), ("anthropic", "Anthropic")]:
            row = QHBoxLayout()
            row.setSpacing(8)

            lbl = QLabel(f"{label_text}:")
            lbl.setFixedWidth(75)
            f = lbl.font(); f.setBold(True); lbl.setFont(f)

            entry = QLineEdit()
            entry.setEchoMode(QLineEdit.Password)
            entry.setPlaceholderText(f"API key {label_text}")
            entry.setText(self._api_keys_cache.get(provider, ""))
            self._api_key_entries[provider] = entry

            show_btn = QPushButton("👁")
            show_btn.setFixedSize(34, 30)
            show_btn.setToolTip("Hiện/ẩn key")
            show_btn.clicked.connect(lambda _, e=entry: self._toggle_echo(e))

            verify_btn = QPushButton("Xác minh")
            verify_btn.setFixedSize(80, 30)
            verify_btn.clicked.connect(
                lambda _, p=provider, e=entry, s=None: self._verify_key_async(
                    p, e, self._api_key_status[p]
                )
            )

            status_lbl = QLabel("")
            status_lbl.setStyleSheet("color: #6c7086; font-size: 10px;")
            status_lbl.setMinimumWidth(80)
            self._api_key_status[provider] = status_lbl

            row.addWidget(lbl)
            row.addWidget(entry, 1)
            row.addWidget(show_btn)
            row.addWidget(verify_btn)
            row.addWidget(status_lbl)
            layout.addLayout(row)

        layout.addSpacing(4)

        # ── LLM Priority ─────────────────────────────────────────────────────
        self._add_section_header(layout, "🤖  Thứ tự ưu tiên LLM")

        hint_llm = QLabel("Kéo hoặc dùng ↑↓ để sắp xếp thứ tự fallback tự động khi bị rate limit")
        hint_llm.setStyleSheet("color: #6c7086; font-size: 10px;")
        layout.addWidget(hint_llm)

        llm_row = QHBoxLayout()
        llm_row.setSpacing(8)

        self._llm_list = QListWidget()
        self._llm_list.setMaximumHeight(108)
        self._llm_list.setDragDropMode(QListWidget.InternalMove)
        all_providers = ["gemini", "openai", "anthropic", "ollama"]
        current_p = self._settings.get("llm_priority", ["gemini"])
        ordered = list(current_p) + [p for p in all_providers if p not in current_p]
        for p in ordered:
            self._llm_list.addItem(p)

        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)
        up_btn = QPushButton("↑")
        up_btn.setFixedSize(30, 30)
        up_btn.setToolTip("Tăng ưu tiên")
        up_btn.clicked.connect(self._llm_move_up)
        down_btn = QPushButton("↓")
        down_btn.setFixedSize(30, 30)
        down_btn.setToolTip("Giảm ưu tiên")
        down_btn.clicked.connect(self._llm_move_down)
        btn_col.addWidget(up_btn)
        btn_col.addWidget(down_btn)
        btn_col.addStretch()

        llm_row.addWidget(self._llm_list, 1)
        llm_row.addLayout(btn_col)
        layout.addLayout(llm_row)
        layout.addSpacing(4)

        # ── Whisper ───────────────────────────────────────────────────────────
        self._add_section_header(layout, "🎙  Nhận dạng giọng nói (Whisper)")
        row_w = QHBoxLayout()
        lbl_wm = QLabel("Model:")
        lbl_wm.setFixedWidth(75)
        f = lbl_wm.font(); f.setBold(True); lbl_wm.setFont(f)
        self._whisper_model_combo = QComboBox()
        self._whisper_model_combo.addItems(["tiny", "base", "small", "medium"])
        wm_idx = self._whisper_model_combo.findText(self._settings.get("whisper_model", "base"))
        if wm_idx >= 0:
            self._whisper_model_combo.setCurrentIndex(wm_idx)

        lbl_wl = QLabel("Ngôn ngữ:")
        f2 = lbl_wl.font(); f2.setBold(True); lbl_wl.setFont(f2)
        self._whisper_lang_combo = QComboBox()
        self._whisper_lang_combo.addItems(["en", "ja", "ko", "zh", "auto"])
        wl_idx = self._whisper_lang_combo.findText(self._settings.get("whisper_language", "en"))
        if wl_idx >= 0:
            self._whisper_lang_combo.setCurrentIndex(wl_idx)

        hint_wm = QLabel("(tiny=nhanh, medium=chính xác)")
        hint_wm.setStyleSheet("color: #6c7086; font-size: 10px;")

        row_w.addWidget(lbl_wm)
        row_w.addWidget(self._whisper_model_combo)
        row_w.addSpacing(16)
        row_w.addWidget(lbl_wl)
        row_w.addWidget(self._whisper_lang_combo)
        row_w.addSpacing(8)
        row_w.addWidget(hint_wm)
        row_w.addStretch()
        layout.addLayout(row_w)
        layout.addSpacing(4)

        # ── VAD ───────────────────────────────────────────────────────────────
        self._add_section_header(layout, "🔊  Phát hiện giọng nói (VAD)")
        row_vad = QHBoxLayout()
        lbl_vad_low = QLabel("Ít nhạy")
        lbl_vad_low.setStyleSheet("color: #6c7086; font-size: 10px;")
        lbl_vad = QLabel("Độ nhạy:")
        lbl_vad.setFixedWidth(75)
        f = lbl_vad.font(); f.setBold(True); lbl_vad.setFont(f)
        self._vad_slider = QSlider(Qt.Horizontal)
        self._vad_slider.setRange(0, 3)
        self._vad_slider.setValue(int(self._settings.get("vad_aggressiveness", 2)))
        self._vad_slider.setFixedWidth(130)
        self._vad_slider.setTickPosition(QSlider.TicksBelow)
        self._vad_slider.setTickInterval(1)
        self._vad_val_label = QLabel(str(self._vad_slider.value()))
        self._vad_val_label.setStyleSheet("color: #89b4fa; font-weight: bold;")
        self._vad_val_label.setFixedWidth(16)
        self._vad_slider.valueChanged.connect(
            lambda v: self._vad_val_label.setText(str(v))
        )
        lbl_vad_high = QLabel("Rất nhạy")
        lbl_vad_high.setStyleSheet("color: #6c7086; font-size: 10px;")

        row_vad.addWidget(lbl_vad)
        row_vad.addWidget(lbl_vad_low)
        row_vad.addWidget(self._vad_slider)
        row_vad.addWidget(lbl_vad_high)
        row_vad.addWidget(self._vad_val_label)
        row_vad.addStretch()
        layout.addLayout(row_vad)
        layout.addSpacing(4)

        # ── Target language ───────────────────────────────────────────────────
        self._add_section_header(layout, "🌐  Ngôn ngữ đích")
        row_tl = QHBoxLayout()
        lbl_tl = QLabel("Dịch sang:")
        lbl_tl.setFixedWidth(75)
        f = lbl_tl.font(); f.setBold(True); lbl_tl.setFont(f)
        self._target_lang_combo = QComboBox()
        self._target_lang_combo.addItems(["Vietnamese", "English", "Japanese", "Korean", "Chinese"])
        tl_idx = self._target_lang_combo.findText(self._settings.get("target_language", "Vietnamese"))
        if tl_idx >= 0:
            self._target_lang_combo.setCurrentIndex(tl_idx)
        row_tl.addWidget(lbl_tl)
        row_tl.addWidget(self._target_lang_combo)
        row_tl.addStretch()
        layout.addLayout(row_tl)
        layout.addSpacing(4)

        # ── Giao diện ─────────────────────────────────────────────────────────
        self._add_section_header(layout, "🖥  Giao diện")
        row_top = QHBoxLayout()
        lbl_top = QLabel("Luôn nằm trên:")
        lbl_top.setFixedWidth(110)
        f = lbl_top.font(); f.setBold(True); lbl_top.setFont(f)
        self._always_on_top_cb = QCheckBox()
        self._always_on_top_cb.setChecked(self._settings.get("always_on_top", True))
        self._always_on_top_cb.toggled.connect(self._on_always_on_top_toggled)
        hint_top = QLabel("Cửa sổ luôn hiển thị trên game")
        hint_top.setStyleSheet("color: #6c7086; font-size: 10px;")
        row_top.addWidget(lbl_top)
        row_top.addWidget(self._always_on_top_cb)
        row_top.addWidget(hint_top)
        row_top.addStretch()
        layout.addLayout(row_top)

        layout.addSpacing(12)

        # ── Save button ───────────────────────────────────────────────────────
        save_row = QHBoxLayout()
        self._save_status_label = QLabel("")
        self._save_status_label.setStyleSheet("color: #a6e3a1; font-size: 10px;")
        save_btn = QPushButton("💾  Lưu cài đặt")
        save_btn.setObjectName("btnSave")
        save_btn.setFixedHeight(34)
        save_btn.clicked.connect(self._save_settings)
        save_row.addWidget(self._save_status_label)
        save_row.addStretch()
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)

        layout.addStretch()
        scroll.setWidget(container)
        self._tabs.addTab(scroll, "⚙ Cài đặt")

    @staticmethod
    def _add_section_header(layout: QVBoxLayout, text: str):
        layout.addSpacing(10)
        row = QHBoxLayout()
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 10px;")
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #45475a;")
        row.addWidget(lbl)
        row.addWidget(line, 1)
        layout.addLayout(row)
        layout.addSpacing(4)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_toggle(self):
        if not self._running:
            idx = self._device_combo.currentIndex()
            device_index = self._devices[idx]["index"] if self._devices and 0 <= idx < len(self._devices) else None
            self._running = True
            self._toggle_btn.setObjectName("btnStop")
            self._toggle_btn.setText("■  Dừng")
            self._toggle_btn.style().unpolish(self._toggle_btn)
            self._toggle_btn.style().polish(self._toggle_btn)
            self._device_combo.setEnabled(False)
            self.update_status("🎙  Đang nghe...")
            self._on_start(device_index)
        else:
            self._running = False
            self._toggle_btn.setObjectName("btnStart")
            self._toggle_btn.setText("▶  Bắt đầu")
            self._toggle_btn.style().unpolish(self._toggle_btn)
            self._toggle_btn.style().polish(self._toggle_btn)
            self._device_combo.setEnabled(True)
            self._processing_label.setText("")
            self.update_status("⏸  Đang chờ")
            self._on_stop()

    def _copy_translation(self):
        text = self._translated_box.toPlainText().strip()
        if text:
            QApplication.clipboard().setText(text)
            self._copy_btn.setText("✓  Đã copy!")
            self._copy_btn.setEnabled(False)
            QTimer.singleShot(2000, lambda: (
                self._copy_btn.setText("📋  Copy bản dịch"),
                self._copy_btn.setEnabled(True),
            ))
            self.update_status("📋  Đã copy bản dịch")

    def _clear_history(self):
        self._history_box.clear()
        self._history_count_lbl.setText("0 mục")

    def _llm_move_up(self):
        row = self._llm_list.currentRow()
        if row > 0:
            item = self._llm_list.takeItem(row)
            self._llm_list.insertItem(row - 1, item)
            self._llm_list.setCurrentRow(row - 1)

    def _llm_move_down(self):
        row = self._llm_list.currentRow()
        if row < self._llm_list.count() - 1:
            item = self._llm_list.takeItem(row)
            self._llm_list.insertItem(row + 1, item)
            self._llm_list.setCurrentRow(row + 1)

    def _on_always_on_top_toggled(self, checked: bool):
        flags = self.windowFlags()
        if checked:
            self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
        self.show()

    @staticmethod
    def _toggle_echo(entry: QLineEdit):
        if entry.echoMode() == QLineEdit.Password:
            entry.setEchoMode(QLineEdit.Normal)
        else:
            entry.setEchoMode(QLineEdit.Password)

    def _verify_key_async(self, provider: str, entry: QLineEdit, status_lbl: Optional[QLabel] = None):
        if status_lbl is None:
            status_lbl = self._api_key_status.get(provider)
        if status_lbl is None:
            return
        key = entry.text().strip()
        if not key:
            status_lbl.setText("Chưa nhập key")
            return
        status_lbl.setText("Đang xác minh...")

        def _worker():
            ok = self._do_verify_key(provider, key)
            self._signals.status_changed.emit("")
            color = "#a6e3a1" if ok else "#f38ba8"
            text = "✓ Hợp lệ" if ok else "✗ Lỗi key"
            QTimer.singleShot(0, lambda: (
                status_lbl.setText(text),
                status_lbl.setStyleSheet(f"color: {color}; font-size: 10px;"),
            ))

        threading.Thread(target=_worker, daemon=True).start()

    @staticmethod
    def _do_verify_key(provider: str, key: str) -> bool:
        try:
            if provider == "gemini":
                from google import genai
                genai.Client(api_key=key).models.generate_content(
                    model="gemini-2.5-flash", contents="Reply: OK",
                )
                return True
            elif provider == "openai":
                from openai import OpenAI
                OpenAI(api_key=key).models.list()
                return True
            elif provider == "anthropic":
                import anthropic
                anthropic.Anthropic(api_key=key).messages.create(
                    model="claude-haiku-4-5", max_tokens=10,
                    messages=[{"role": "user", "content": "hi"}],
                )
                return True
        except Exception:
            return False
        return False

    def _save_settings(self):
        for provider, entry in self._api_key_entries.items():
            key = entry.text().strip()
            if key:
                save_api_key(provider, key)
                self._api_keys_cache[provider] = key

        llm_priority = [
            self._llm_list.item(i).text()
            for i in range(self._llm_list.count())
        ]

        new_settings = {
            **self._settings,
            "whisper_model": self._whisper_model_combo.currentText(),
            "whisper_language": self._whisper_lang_combo.currentText(),
            "target_language": self._target_lang_combo.currentText(),
            "vad_aggressiveness": self._vad_slider.value(),
            "llm_priority": llm_priority,
            "always_on_top": self._always_on_top_cb.isChecked(),
        }
        if save_settings(new_settings):
            self._settings = new_settings
            self._save_status_label.setText("✓ Đã lưu")
            QTimer.singleShot(3000, lambda: self._save_status_label.setText(""))
            if self._on_settings_changed:
                self._on_settings_changed(new_settings)
        else:
            self._save_status_label.setText("✗ Lỗi khi lưu")

    def _prefetch_api_keys(self):
        for p in ("gemini", "openai", "anthropic"):
            try:
                self._api_keys_cache[p] = get_api_key(p)
            except Exception:
                self._api_keys_cache[p] = ""
        QTimer.singleShot(0, self._fill_api_key_entries)

    def _fill_api_key_entries(self):
        for provider, entry in self._api_key_entries.items():
            if not entry.text():
                entry.setText(self._api_keys_cache.get(provider, ""))

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

    # ── Signal slots (always on main thread) ─────────────────────────────────

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
                self._processing_label.setText("⏳ Đang dịch...")
            elif "📝" in status:
                self._processing_label.setText("🎤 Đang nhận dạng...")
        elif "📋" in status:
            color = "#89b4fa"
        else:
            color = "#6c7086"

        if "⏸" in status or "🎙" in status:
            self._processing_label.setText("")

        self._status_label.setStyleSheet(
            f"{_STATUS_BASE}color: {color};"
        )

    def _apply_translation(self, original: str, translated: str):
        self._original_box.setPlainText(original)
        cursor = self._original_box.textCursor()
        cursor.movePosition(QTextCursor.Start)
        self._original_box.setTextCursor(cursor)

        self._translated_box.setPlainText(translated)
        cursor2 = self._translated_box.textCursor()
        cursor2.movePosition(QTextCursor.Start)
        self._translated_box.setTextCursor(cursor2)

        self._processing_label.setText("")

        # Append to history
        ts = QDateTime.currentDateTime().toString("HH:mm:ss")
        self._history_box.append(
            f'<span style="color:#6c7086;font-size:9px;">── {ts} ──</span>'
        )
        self._history_box.append(
            f'<span style="color:#89b4fa;">📝</span> '
            f'<span style="color:#cdd6f4;">{original}</span>'
        )
        self._history_box.append(
            f'<span style="color:#a6e3a1;">🌐</span> '
            f'<span style="color:#cdd6f4;">{translated}</span>'
        )
        self._history_box.append("")

        # Update count
        count_text = self._history_count_lbl.text()
        try:
            count = int(count_text.split()[0]) + 1
        except (ValueError, IndexError):
            count = 1
        self._history_count_lbl.setText(f"{count} mục")

    def _apply_llm(self, provider: str):
        if provider and provider.lower() != "none":
            self._llm_label.setText(f"🟢  {provider}")
            self._llm_label.setObjectName("llmBadge")
        else:
            self._llm_label.setText("⚪  Chưa kết nối")
            self._llm_label.setObjectName("llmBadgeEmpty")
        self._llm_label.style().unpolish(self._llm_label)
        self._llm_label.style().polish(self._llm_label)
