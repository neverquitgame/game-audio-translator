import tkinter as tk
from tkinter import ttk, scrolledtext
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_WIN_WIDTH = 520
_WIN_HEIGHT = 340
_FONT_LABEL = ("Segoe UI", 9, "bold")
_FONT_TEXT = ("Segoe UI", 10)
_FONT_STATUS = ("Segoe UI", 8)
_BG = "#1e1e2e"
_BG_TEXT = "#2a2a3d"
_FG = "#cdd6f4"
_FG_DIM = "#6c7086"
_ACCENT = "#89b4fa"
_BTN_START = "#a6e3a1"
_BTN_STOP = "#f38ba8"


class TranslatorUI:
    def __init__(
        self,
        devices: list[dict],
        on_start: Callable[[Optional[int]], None],
        on_stop: Callable[[], None],
        on_api_key_changed: Optional[Callable[[str], None]] = None,
    ):
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_api_key_changed = on_api_key_changed
        self._running = False

        self.root = tk.Tk()
        self._build(devices)

    def _build(self, devices: list[dict]):
        root = self.root
        root.title("Game Audio Translator")
        root.geometry(f"{_WIN_WIDTH}x{_WIN_HEIGHT}")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg=_BG)

        # ── Control bar ──────────────────────────────────────────────────────
        ctrl_frame = tk.Frame(root, bg=_BG, pady=6, padx=10)
        ctrl_frame.pack(fill=tk.X)

        tk.Label(ctrl_frame, text="Thiết bị âm thanh:", bg=_BG, fg=_FG, font=_FONT_LABEL).pack(side=tk.LEFT)

        self._device_var = tk.StringVar()
        device_names = [d["name"] for d in devices] if devices else ["(Không tìm thấy thiết bị)"]
        self._devices = devices

        self._device_combo = ttk.Combobox(
            ctrl_frame,
            textvariable=self._device_var,
            values=device_names,
            state="readonly",
            width=28,
        )
        if device_names:
            self._device_combo.current(0)
        self._device_combo.pack(side=tk.LEFT, padx=(6, 10))

        self._toggle_btn = tk.Button(
            ctrl_frame,
            text="▶  Bắt đầu",
            bg=_BTN_START,
            fg="#1e1e2e",
            font=_FONT_LABEL,
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._on_toggle,
        )
        self._toggle_btn.pack(side=tk.LEFT)

        # Nút cài đặt API key (góc phải)
        tk.Button(
            ctrl_frame,
            text="⚙",
            bg=_BG,
            fg=_FG_DIM,
            font=("Segoe UI", 12),
            relief=tk.FLAT,
            padx=6,
            pady=1,
            cursor="hand2",
            command=self._open_settings,
        ).pack(side=tk.RIGHT, padx=(0, 2))

        # ── Text display area ────────────────────────────────────────────────
        display_frame = tk.Frame(root, bg=_BG, padx=10)
        display_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(display_frame, text="Gốc:", bg=_BG, fg=_ACCENT, font=_FONT_LABEL, anchor="w").pack(fill=tk.X)
        self._original_box = scrolledtext.ScrolledText(
            display_frame,
            height=4,
            wrap=tk.WORD,
            font=_FONT_TEXT,
            bg=_BG_TEXT,
            fg=_FG,
            insertbackground=_FG,
            relief=tk.FLAT,
            state=tk.DISABLED,
        )
        self._original_box.pack(fill=tk.X, pady=(0, 6))

        tk.Label(display_frame, text="Dịch:", bg=_BG, fg=_ACCENT, font=_FONT_LABEL, anchor="w").pack(fill=tk.X)
        self._translated_box = scrolledtext.ScrolledText(
            display_frame,
            height=4,
            wrap=tk.WORD,
            font=_FONT_TEXT,
            bg=_BG_TEXT,
            fg=_FG,
            insertbackground=_FG,
            relief=tk.FLAT,
            state=tk.DISABLED,
        )
        self._translated_box.pack(fill=tk.X)

        # ── Status bar ───────────────────────────────────────────────────────
        status_frame = tk.Frame(root, bg="#13131f", pady=4)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self._status_var = tk.StringVar(value="⏸  Đang chờ")
        tk.Label(
            status_frame,
            textvariable=self._status_var,
            bg="#13131f",
            fg=_FG_DIM,
            font=_FONT_STATUS,
        ).pack(side=tk.LEFT, padx=10)

        self._style_combobox()

    def _style_combobox(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TCombobox",
            fieldbackground=_BG_TEXT,
            background=_BG_TEXT,
            foreground=_FG,
            selectbackground=_BG_TEXT,
            selectforeground=_FG,
        )

    def _open_settings(self):
        if self._running:
            from tkinter import messagebox
            messagebox.showinfo(
                "Thông báo",
                "Vui lòng dừng dịch trước khi thay đổi API key.",
                parent=self.root,
            )
            return
        from src.ui.api_key_dialog import ApiKeyDialog

        def _after_save(new_key: str):
            if self._on_api_key_changed:
                self._on_api_key_changed(new_key)
            self.update_status("API key đã cập nhật — sẵn sàng.")

        ApiKeyDialog(self.root, on_saved=_after_save, is_first_run=False)

    def _on_toggle(self):
        if not self._running:
            selected_idx = self._device_combo.current()
            device_index = self._devices[selected_idx]["index"] if self._devices else None
            self._running = True
            self._toggle_btn.config(text="■  Dừng", bg=_BTN_STOP)
            self._device_combo.config(state="disabled")
            self.update_status("🎙  Đang nghe...")
            self._on_start(device_index)
        else:
            self._running = False
            self._toggle_btn.config(text="▶  Bắt đầu", bg=_BTN_START)
            self._device_combo.config(state="readonly")
            self.update_status("⏸  Đang chờ")
            self._on_stop()

    def _set_text(self, widget: scrolledtext.ScrolledText, text: str):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.config(state=tk.DISABLED)

    def update_translation(self, original: str, translated: str):
        """Thread-safe update via after()."""
        self.root.after(0, lambda: self._set_text(self._original_box, original))
        self.root.after(0, lambda: self._set_text(self._translated_box, translated))

    def update_status(self, status: str):
        self.root.after(0, lambda: self._status_var.set(status))

    def run(self):
        self.root.mainloop()
