"""Tab Dịch — hiển thị văn bản gốc và bản dịch."""

from typing import Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QApplication,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor


class TranslateTab(QWidget):
    """Tab chứa hai text box (văn bản gốc / bản dịch) và nút Copy."""

    def __init__(self, on_status_update: Callable[[str], None]):
        super().__init__()
        self._on_status_update = on_status_update
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 12)
        layout.setSpacing(0)

        # ── Văn bản gốc ───────────────────────────────────────────────────────
        orig_header = QHBoxLayout()
        orig_lbl = QLabel("VĂN BẢN GỐC")
        orig_lbl.setStyleSheet(
            "color: #6c7086; font-weight: bold; font-size: 10px; letter-spacing: 1px;"
        )
        orig_header.addWidget(orig_lbl)
        orig_header.addStretch()
        layout.addLayout(orig_header)
        layout.addSpacing(6)

        self._original_box = QTextEdit()
        self._original_box.setReadOnly(True)
        self._original_box.setMinimumHeight(130)
        self._original_box.setPlaceholderText(
            "Nhấn ▶ Bắt đầu rồi nói để xem văn bản nhận dạng tại đây..."
        )
        self._original_box.setStyleSheet(
            "QTextEdit { background-color: #252537; border-radius: 8px; padding: 10px; "
            "font-size: 13px; color: #cdd6f4; border: 1px solid #2a2a3d; }"
        )
        layout.addWidget(self._original_box, 1)
        layout.addSpacing(12)

        # ── Bản dịch ──────────────────────────────────────────────────────────
        trans_header = QHBoxLayout()
        trans_lbl = QLabel("BẢN DỊCH")
        trans_lbl.setStyleSheet(
            "color: #6c7086; font-weight: bold; font-size: 10px; letter-spacing: 1px;"
        )
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
        self._translated_box.setPlaceholderText(
            "Bản dịch sẽ xuất hiện ở đây sau khi nhận dạng xong..."
        )
        self._translated_box.setStyleSheet(
            "QTextEdit { background-color: #1a2a1a; border-radius: 8px; padding: 10px; "
            "font-size: 13px; color: #cdd6f4; border: 1px solid #2d3d2d; }"
        )
        layout.addWidget(self._translated_box, 1)
        layout.addSpacing(10)

        # ── Toolbar dưới ──────────────────────────────────────────────────────
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

    # ── Public API ────────────────────────────────────────────────────────────

    def set_texts(self, original: str, translated: str):
        """Cập nhật cả hai text box (gọi từ main thread)."""
        self._original_box.setPlainText(original)
        c = self._original_box.textCursor()
        c.movePosition(QTextCursor.Start)
        self._original_box.setTextCursor(c)

        self._translated_box.setPlainText(translated)
        c2 = self._translated_box.textCursor()
        c2.movePosition(QTextCursor.Start)
        self._translated_box.setTextCursor(c2)

        self.clear_processing()

    def set_processing(self, text: str):
        self._processing_label.setText(text)

    def clear_processing(self):
        self._processing_label.setText("")

    def get_translated_text(self) -> str:
        return self._translated_box.toPlainText().strip()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _copy_translation(self):
        text = self.get_translated_text()
        if not text:
            return
        QApplication.clipboard().setText(text)
        self._copy_btn.setText("✓  Đã copy!")
        self._copy_btn.setEnabled(False)
        QTimer.singleShot(2000, lambda: (
            self._copy_btn.setText("📋  Copy bản dịch"),
            self._copy_btn.setEnabled(True),
        ))
        self._on_status_update("📋  Đã copy bản dịch")
