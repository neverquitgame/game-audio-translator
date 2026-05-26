"""Tab Cài đặt — API keys, LLM priority, Whisper, VAD, ngôn ngữ, giao diện."""

import threading
import logging
from typing import Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QScrollArea, QSlider, QLineEdit, QListWidget, QCheckBox, QFrame,
)
from PySide6.QtCore import Qt, QTimer

from src.settings_store import save as save_settings
from src.keystore import get_api_key, save_api_key

logger = logging.getLogger(__name__)

_ALL_PROVIDERS = ["gemini", "openai", "anthropic", "ollama"]
_KEY_PROVIDERS = [("gemini", "Gemini"), ("openai", "OpenAI"), ("anthropic", "Anthropic")]


class SettingsTab(QWidget):
    """Tab cài đặt toàn bộ ứng dụng."""

    def __init__(
        self,
        settings: dict,
        on_save: Callable[[dict], None],
        on_always_on_top: Callable[[bool], None],
    ):
        super().__init__()
        self._settings = settings
        self._on_save = on_save
        self._on_always_on_top = on_always_on_top
        self._api_keys_cache: dict[str, str] = {}
        self._build()

        threading.Thread(target=self._prefetch_api_keys, daemon=True).start()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container.setStyleSheet("background-color: #1e1e2e;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(4)

        self._api_key_entries: dict[str, QLineEdit] = {}
        self._api_key_status: dict[str, QLabel] = {}

        # ── API Keys ──────────────────────────────────────────────────────────
        self._add_section_header(layout, "🔑  API Keys")
        for provider, label_text in _KEY_PROVIDERS:
            row = QHBoxLayout()
            row.setSpacing(8)

            lbl = QLabel(f"{label_text}:")
            lbl.setFixedWidth(75)
            f = lbl.font(); f.setBold(True); lbl.setFont(f)

            entry = QLineEdit()
            entry.setEchoMode(QLineEdit.Password)
            entry.setPlaceholderText(f"API key {label_text}")
            self._api_key_entries[provider] = entry

            show_btn = QPushButton("👁")
            show_btn.setFixedSize(34, 30)
            show_btn.setToolTip("Hiện/ẩn key")
            show_btn.clicked.connect(lambda _, e=entry: self._toggle_echo(e))

            status_lbl = QLabel("")
            status_lbl.setStyleSheet("color: #6c7086; font-size: 10px;")
            status_lbl.setMinimumWidth(80)
            self._api_key_status[provider] = status_lbl

            verify_btn = QPushButton("Xác minh")
            verify_btn.setFixedSize(80, 30)
            verify_btn.clicked.connect(
                lambda _, p=provider, e=entry: self._verify_key_async(p, e)
            )

            row.addWidget(lbl)
            row.addWidget(entry, 1)
            row.addWidget(show_btn)
            row.addWidget(verify_btn)
            row.addWidget(status_lbl)
            layout.addLayout(row)

        layout.addSpacing(4)

        # ── LLM Priority ──────────────────────────────────────────────────────
        self._add_section_header(layout, "🤖  Thứ tự ưu tiên LLM")
        hint_llm = QLabel("Kéo hoặc dùng ↑↓ để sắp xếp thứ tự fallback tự động khi bị rate limit")
        hint_llm.setStyleSheet("color: #6c7086; font-size: 10px;")
        layout.addWidget(hint_llm)

        llm_row = QHBoxLayout()
        llm_row.setSpacing(8)

        self._llm_list = QListWidget()
        self._llm_list.setMaximumHeight(108)
        self._llm_list.setDragDropMode(QListWidget.InternalMove)
        current_p = self._settings.get("llm_priority", ["gemini"])
        ordered = list(current_p) + [p for p in _ALL_PROVIDERS if p not in current_p]
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
        f2 = lbl_wm.font(); f2.setBold(True); lbl_wm.setFont(f2)
        self._whisper_model_combo = QComboBox()
        self._whisper_model_combo.addItems(["tiny", "base", "small", "medium"])
        idx = self._whisper_model_combo.findText(self._settings.get("whisper_model", "base"))
        if idx >= 0:
            self._whisper_model_combo.setCurrentIndex(idx)

        lbl_wl = QLabel("Ngôn ngữ:")
        f3 = lbl_wl.font(); f3.setBold(True); lbl_wl.setFont(f3)
        self._whisper_lang_combo = QComboBox()
        self._whisper_lang_combo.addItems(["en", "ja", "ko", "zh", "auto"])
        idx2 = self._whisper_lang_combo.findText(self._settings.get("whisper_language", "en"))
        if idx2 >= 0:
            self._whisper_lang_combo.setCurrentIndex(idx2)

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

        lbl_vad = QLabel("Độ nhạy:")
        lbl_vad.setFixedWidth(75)
        f4 = lbl_vad.font(); f4.setBold(True); lbl_vad.setFont(f4)

        lbl_vad_low = QLabel("Ít nhạy")
        lbl_vad_low.setStyleSheet("color: #6c7086; font-size: 10px;")

        self._vad_slider = QSlider(Qt.Horizontal)
        self._vad_slider.setRange(0, 3)
        self._vad_slider.setValue(int(self._settings.get("vad_aggressiveness", 2)))
        self._vad_slider.setFixedWidth(130)
        self._vad_slider.setTickPosition(QSlider.TicksBelow)
        self._vad_slider.setTickInterval(1)

        self._vad_val_label = QLabel(str(self._vad_slider.value()))
        self._vad_val_label.setStyleSheet("color: #89b4fa; font-weight: bold;")
        self._vad_val_label.setFixedWidth(16)
        self._vad_slider.valueChanged.connect(lambda v: self._vad_val_label.setText(str(v)))

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
        f5 = lbl_tl.font(); f5.setBold(True); lbl_tl.setFont(f5)
        self._target_lang_combo = QComboBox()
        self._target_lang_combo.addItems(["Vietnamese", "English", "Japanese", "Korean", "Chinese"])
        idx3 = self._target_lang_combo.findText(self._settings.get("target_language", "Vietnamese"))
        if idx3 >= 0:
            self._target_lang_combo.setCurrentIndex(idx3)
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
        f6 = lbl_top.font(); f6.setBold(True); lbl_top.setFont(f6)
        self._always_on_top_cb = QCheckBox()
        self._always_on_top_cb.setChecked(self._settings.get("always_on_top", True))
        self._always_on_top_cb.toggled.connect(self._on_always_on_top)
        hint_top = QLabel("Cửa sổ luôn hiển thị trên game")
        hint_top.setStyleSheet("color: #6c7086; font-size: 10px;")
        row_top.addWidget(lbl_top)
        row_top.addWidget(self._always_on_top_cb)
        row_top.addWidget(hint_top)
        row_top.addStretch()
        layout.addLayout(row_top)
        layout.addSpacing(12)

        # ── Save ──────────────────────────────────────────────────────────────
        save_row = QHBoxLayout()
        self._save_status_lbl = QLabel("")
        self._save_status_lbl.setStyleSheet("color: #a6e3a1; font-size: 10px;")
        save_btn = QPushButton("💾  Lưu cài đặt")
        save_btn.setObjectName("btnSave")
        save_btn.setFixedHeight(34)
        save_btn.clicked.connect(self._save)
        save_row.addWidget(self._save_status_lbl)
        save_row.addStretch()
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)

        layout.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ── Helpers ───────────────────────────────────────────────────────────────

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

    @staticmethod
    def _toggle_echo(entry: QLineEdit):
        if entry.echoMode() == QLineEdit.Password:
            entry.setEchoMode(QLineEdit.Normal)
        else:
            entry.setEchoMode(QLineEdit.Password)

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

    # ── API key verify ────────────────────────────────────────────────────────

    def _verify_key_async(self, provider: str, entry: QLineEdit):
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
            color = "#a6e3a1" if ok else "#f38ba8"
            text = "✓ Hợp lệ" if ok else "✗ Lỗi key"
            QTimer.singleShot(0, lambda: (
                status_lbl.setText(text),
                status_lbl.setStyleSheet(f"color: {color}; font-size: 10px;"),
            ))

        threading.Thread(target=_worker, daemon=True).start()

    @staticmethod
    def _do_verify_key(provider: str, key: str) -> bool:
        models = {
            "gemini":    "gemini/gemini-2.5-flash",
            "openai":    "gpt-4o-mini",
            "anthropic": "anthropic/claude-haiku-4-5",
        }
        model = models.get(provider)
        if not model:
            return False
        try:
            import litellm
            litellm.suppress_debug_info = True
            litellm.completion(
                model=model,
                api_key=key,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
            return True
        except Exception:
            return False

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save(self):
        for provider, entry in self._api_key_entries.items():
            key = entry.text().strip()
            if key:
                save_api_key(provider, key)
            self._api_keys_cache[provider] = key
            self._settings[f"{provider}_api_key"] = key

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
            self._save_status_lbl.setText("✓ Đã lưu")
            QTimer.singleShot(3000, lambda: self._save_status_lbl.setText(""))
            self._on_save(new_settings)
        else:
            self._save_status_lbl.setText("✗ Lỗi khi lưu")

    # ── API key prefetch ──────────────────────────────────────────────────────

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
