"""Tab Lịch sử — ghi lại tất cả các câu đã dịch."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
)
from PySide6.QtCore import QDateTime


class HistoryTab(QWidget):
    """Tab hiển thị lịch sử dịch với timestamp."""

    def __init__(self):
        super().__init__()
        self._count = 0
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 10)
        layout.setSpacing(6)

        header_row = QHBoxLayout()
        hist_lbl = QLabel("Lịch sử dịch")
        hist_lbl.setStyleSheet("color: #89b4fa; font-weight: bold; font-size: 10px;")
        self._count_lbl = QLabel("0 mục")
        self._count_lbl.setStyleSheet("color: #6c7086; font-size: 10px;")
        clear_btn = QPushButton("🗑  Xóa lịch sử")
        clear_btn.setFixedHeight(26)
        clear_btn.clicked.connect(self.clear)
        header_row.addWidget(hist_lbl)
        header_row.addWidget(self._count_lbl)
        header_row.addStretch()
        header_row.addWidget(clear_btn)
        layout.addLayout(header_row)

        self._box = QTextEdit()
        self._box.setReadOnly(True)
        self._box.setPlaceholderText(
            "Chưa có lịch sử dịch. Bắt đầu dịch để xem lịch sử tại đây..."
        )
        layout.addWidget(self._box, 1)

    # ── Public API ────────────────────────────────────────────────────────────

    def add_entry(self, original: str, translated: str):
        ts = QDateTime.currentDateTime().toString("HH:mm:ss")
        self._box.append(f'<span style="color:#6c7086;font-size:9px;">── {ts} ──</span>')
        self._box.append(
            f'<span style="color:#89b4fa;">📝</span> '
            f'<span style="color:#cdd6f4;">{original}</span>'
        )
        self._box.append(
            f'<span style="color:#a6e3a1;">🌐</span> '
            f'<span style="color:#cdd6f4;">{translated}</span>'
        )
        self._box.append("")
        self._count += 1
        self._count_lbl.setText(f"{self._count} mục")

    def clear(self):
        self._box.clear()
        self._count = 0
        self._count_lbl.setText("0 mục")
