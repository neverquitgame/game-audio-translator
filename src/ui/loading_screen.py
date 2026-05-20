"""Màn hình loading dùng PySide6 — hiển thị ngay khi khởi động."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

_STYLE = """
QWidget#loadingRoot {
    background-color: #1e1e2e;
}
QLabel#title {
    color: #cdd6f4;
    font-size: 15px;
    font-weight: bold;
}
QLabel#subtitle {
    color: #6c7086;
    font-size: 10px;
}
QLabel#status {
    color: #cdd6f4;
    font-size: 11px;
}
QProgressBar {
    background-color: #313244;
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #89b4fa;
    border-radius: 4px;
}
"""

_WIDTH = 420
_HEIGHT = 200


class LoadingScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("loadingRoot")
        self.setFixedSize(_WIDTH, _HEIGHT)
        self.setWindowTitle("Game Audio Translator")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(_STYLE)
        self._build()
        self._center()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 32, 36, 28)
        layout.setSpacing(6)

        title = QLabel("🎮  Game Audio Translator")
        title.setObjectName("title")

        subtitle = QLabel("Đang chuẩn bị ứng dụng...")
        subtitle.setObjectName("subtitle")

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)

        self._status_label = QLabel("Đang khởi động...")
        self._status_label.setObjectName("status")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(18)
        layout.addWidget(self._progress)
        layout.addSpacing(10)
        layout.addWidget(self._status_label)
        layout.addStretch()

    def _center(self):
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - _WIDTH) // 2,
            (screen.height() - _HEIGHT) // 2,
        )

    def set_status(self, message: str):
        self._status_label.setText(message)
        QApplication.processEvents()

    def close_loading(self):
        self._progress.setRange(0, 1)
        self._progress.setValue(1)
        QTimer.singleShot(120, self.hide)
