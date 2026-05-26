"""Hằng số kích thước và QSS stylesheet cho toàn bộ cửa sổ chính."""

WIN_W = 660
WIN_H = 600
WIN_MIN_W = 560
WIN_MIN_H = 480

STATUS_BASE = (
    "background-color: #13131f; font-size: 11px; "
    "padding: 4px 12px; border-top: 1px solid #2a2a3d;"
)

APP_STYLE = """
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
QListWidget::item { padding: 5px 10px; }
QListWidget::item:selected {
    background-color: #45475a;
    color: #cdd6f4;
}
QListWidget::item:hover:!selected { background-color: #313244; }
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
