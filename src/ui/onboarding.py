"""Wizard thiết lập lần đầu dùng PySide6 QWizard."""

import logging
from typing import Callable

from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QMessageBox, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.keystore import get_api_key, save_api_key, has_api_key
from src.settings_store import load as load_settings, save as save_settings

logger = logging.getLogger(__name__)

_STYLE = """
QWizard, QWizardPage, QWizard::page, QWizard QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
}
QWizardPage {
    background-color: #1e1e2e;
}
QWizardPage QWidget {
    background-color: transparent;
}
QWizard QFrame, QWizard QStackedWidget, QWizardPage QFrame {
    background-color: #1e1e2e;
}
QWizard QAbstractButton {
    background-color: #313244;
    color: #cdd6f4;
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: bold;
}
QWizard QAbstractButton:hover {
    background-color: #45475a;
}
QWizard QAbstractButton#qt_wizard_finish,
QWizard QAbstractButton#qt_wizard_next {
    background-color: #89b4fa;
    color: #1e1e2e;
}
QWizard QAbstractButton#qt_wizard_finish:hover,
QWizard QAbstractButton#qt_wizard_next:hover {
    background-color: #74c7ec;
}
QLabel {
    color: #cdd6f4;
    background: transparent;
}
QLabel.dim {
    color: #6c7086;
}
QLabel.hint {
    color: #9399b2;
    font-size: 10px;
}
QLineEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    font-family: "Consolas", monospace;
    font-size: 11px;
}
QLineEdit:focus {
    border: 1px solid #89b4fa;
}
QComboBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 5px 10px;
    min-width: 140px;
}
QComboBox:focus {
    border: 1px solid #89b4fa;
}
QComboBox QAbstractItemView {
    background-color: #313244;
    color: #cdd6f4;
    selection-background-color: #45475a;
    border: 1px solid #45475a;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
"""


def _h(text: str, size: int = 13, bold: bool = True) -> QLabel:
    lbl = QLabel(text)
    f = lbl.font()
    f.setPointSize(size)
    f.setBold(bold)
    lbl.setFont(f)
    return lbl


def _p(text: str, dim: bool = False) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    if dim:
        lbl.setStyleSheet("color: #9399b2; font-size: 10px;")
    else:
        lbl.setStyleSheet("color: #cdd6f4;")
    return lbl


def _style_wizard_page(page: QWizardPage):
    page.setAutoFillBackground(True)
    page.setStyleSheet("background-color: #1e1e2e;")


class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        _style_wizard_page(self)
        self.setTitle("Chào mừng đến Game Audio Translator")
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addWidget(_p(
            "Ứng dụng dịch âm thanh game sang tiếng Việt theo thời gian thực.\n\n"
            "Trình hướng dẫn này giúp bạn thiết lập nhanh:\n"
            "  • API key để dịch văn bản\n"
            "  • Ngôn ngữ đích và model nhận dạng giọng nói\n"
            "  • Thiết bị âm thanh đầu vào\n\n"
            "Bạn có thể thay đổi mọi thứ sau trong tab Cài đặt."
        ))
        layout.addStretch()


class ApiKeyPage(QWizardPage):
    def __init__(self):
        super().__init__()
        _style_wizard_page(self)
        self.setTitle("API Key dịch thuật")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(_p(
            "Nhập ít nhất một API key. Gemini miễn phí tại aistudio.google.com.",
            dim=True,
        ))

        for field_id, label_text, provider, hint in [
            ("gemini_key", "Gemini:", "gemini", "Miễn phí tại aistudio.google.com"),
            ("openai_key", "OpenAI:", "openai", ""),
            ("anthropic_key", "Anthropic:", "anthropic", ""),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setFixedWidth(78)
            f = lbl.font(); f.setBold(True); lbl.setFont(f)
            entry = QLineEdit()
            entry.setEchoMode(QLineEdit.Password)
            placeholder = f"API key {label_text.rstrip(':')}"
            if hint:
                placeholder += f"  ({hint})"
            entry.setPlaceholderText(placeholder)
            entry.setText(get_api_key(provider))
            row.addWidget(lbl)
            row.addWidget(entry)
            layout.addLayout(row)
            self.registerField(field_id, entry)

        layout.addStretch()

    def validatePage(self) -> bool:
        g = self.field("gemini_key").strip()
        o = self.field("openai_key").strip()
        a = self.field("anthropic_key").strip()
        if not g and not o and not a and not any(
            has_api_key(p) for p in ("gemini", "openai", "anthropic")
        ):
            r = QMessageBox.question(
                self,
                "Chưa có API key",
                "Bạn chưa nhập API key. Tiếp tục mà không có key sẽ không dịch được.\n\n"
                "Bạn có muốn tiếp tục không?",
            )
            return r == QMessageBox.Yes
        return True


class PreferencesPage(QWizardPage):
    def __init__(self):
        super().__init__()
        _style_wizard_page(self)
        self.setTitle("Tùy chọn dịch & nhận dạng")
        settings = load_settings()
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # Target language
        row1 = QHBoxLayout()
        lbl1 = QLabel("Dịch sang:")
        lbl1.setFixedWidth(110)
        f = lbl1.font(); f.setBold(True); lbl1.setFont(f)
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["Vietnamese", "English", "Japanese", "Korean", "Chinese"])
        current_lang = settings.get("target_language", "Vietnamese")
        idx = self._lang_combo.findText(current_lang)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        row1.addWidget(lbl1)
        row1.addWidget(self._lang_combo)
        row1.addStretch()
        layout.addLayout(row1)

        # Whisper model
        row2 = QHBoxLayout()
        lbl2 = QLabel("Whisper model:")
        lbl2.setFixedWidth(110)
        f = lbl2.font(); f.setBold(True); lbl2.setFont(f)
        self._model_combo = QComboBox()
        self._model_combo.addItems(["tiny", "base", "small", "medium"])
        current_model = settings.get("whisper_model", "base")
        idx2 = self._model_combo.findText(current_model)
        if idx2 >= 0:
            self._model_combo.setCurrentIndex(idx2)
        hint = QLabel("(tiny = nhanh nhất, medium = chính xác hơn)")
        hint.setStyleSheet("color: #6c7086; font-size: 10px;")
        row2.addWidget(lbl2)
        row2.addWidget(self._model_combo)
        row2.addWidget(hint)
        row2.addStretch()
        layout.addLayout(row2)

        layout.addStretch()

    def target_language(self) -> str:
        return self._lang_combo.currentText()

    def whisper_model(self) -> str:
        return self._model_combo.currentText()


class DevicePage(QWizardPage):
    def __init__(self, devices: list[dict]):
        super().__init__()
        _style_wizard_page(self)
        self.setTitle("Thiết bị âm thanh")
        self._devices = devices
        settings = load_settings()
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        if devices:
            layout.addWidget(_p("Chọn thiết bị để bắt âm thanh game / micro:", dim=True))
            self._device_combo = QComboBox()
            self._device_combo.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Fixed,
            )
            for d in devices:
                self._device_combo.addItem(d["name"], d["index"])
            saved_idx = settings.get("preferred_device_index")
            if saved_idx is not None:
                for i, d in enumerate(devices):
                    if d["index"] == saved_idx:
                        self._device_combo.setCurrentIndex(i)
                        break
            layout.addWidget(self._device_combo)
        else:
            self._device_combo = None
            layout.addWidget(_p(
                "Không tìm thấy thiết bị âm thanh.\n"
                "Bạn có thể chọn lại trong tab Dịch sau khi kết nối thiết bị."
            ))

        layout.addStretch()

    def selected_device_index(self):
        if self._device_combo is None:
            return None
        return self._device_combo.currentData()


class FinishPage(QWizardPage):
    def __init__(self):
        super().__init__()
        _style_wizard_page(self)
        self.setTitle("Sẵn sàng!")
        self._layout = QVBoxLayout(self)

    def initializePage(self):
        for i in reversed(range(self._layout.count())):
            item = self._layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        has_key = any(has_api_key(p) for p in ("gemini", "openai", "anthropic"))
        msg = (
            "Thiết lập hoàn tất. Nhấn \"Hoàn tất\" để vào ứng dụng.\n\n"
            "Trên tab Dịch, chọn thiết bị và nhấn ▶ Bắt đầu để dịch âm thanh game."
        )
        if not has_key:
            warn = QLabel("⚠  Bạn chưa nhập API key — ứng dụng sẽ không dịch được.\nVào tab Cài đặt để thêm key sau.\n")
            warn.setStyleSheet("color: #f9e2af;")
            warn.setWordWrap(True)
            self._layout.addWidget(warn)
        self._layout.addWidget(_p(msg))
        self._layout.addStretch()


class OnboardingWizard(QWizard):
    def __init__(self, devices: list[dict], on_complete: Callable[[], None]):
        super().__init__()
        self._devices = devices
        self._on_complete = on_complete
        self._settings = load_settings()

        self.setWindowTitle("Thiết lập Game Audio Translator")
        self.setFixedSize(560, 440)
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setButtonText(QWizard.NextButton, "Tiếp theo →")
        self.setButtonText(QWizard.BackButton, "← Quay lại")
        self.setButtonText(QWizard.FinishButton, "Bắt đầu sử dụng")
        self.setButtonText(QWizard.CancelButton, "Bỏ qua")

        self._pref_page = PreferencesPage()
        self._device_page = DevicePage(devices)
        self._api_page = ApiKeyPage()

        self.addPage(WelcomePage())
        self.addPage(self._api_page)
        self.addPage(self._pref_page)
        self.addPage(self._device_page)
        self.addPage(FinishPage())

        self.setStyleSheet(_STYLE)
        self.finished.connect(self._on_finished)

        screen = self.screen().geometry()
        self.move(
            (screen.width() - 560) // 2,
            (screen.height() - 440) // 2,
        )

    def _on_finished(self, result: int):
        if result == QWizard.Accepted:
            self._save_and_complete()
        else:
            self._on_complete()

    def _save_and_complete(self):
        g = self._api_page.field("gemini_key").strip()
        o = self._api_page.field("openai_key").strip()
        a = self._api_page.field("anthropic_key").strip()
        if g:
            save_api_key("gemini", g)
        if o:
            save_api_key("openai", o)
        if a:
            save_api_key("anthropic", a)

        new_settings = {
            **self._settings,
            "target_language": self._pref_page.target_language(),
            "whisper_model": self._pref_page.whisper_model(),
            "preferred_device_index": self._device_page.selected_device_index(),
            "onboarding_completed": True,
        }
        save_settings(new_settings)
        self._on_complete()
