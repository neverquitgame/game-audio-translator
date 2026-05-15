"""
Dialog nhập và lưu Gemini API key.
Hiển thị khi lần đầu chạy ứng dụng (chưa có key) hoặc khi người dùng muốn đổi key.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import threading
from typing import Callable, Optional

from src.keystore import save_api_key, get_api_key

logger = logging.getLogger(__name__)

_BG = "#1e1e2e"
_BG_CARD = "#2a2a3d"
_BG_INPUT = "#313244"
_FG = "#cdd6f4"
_FG_DIM = "#6c7086"
_FG_HINT = "#9399b2"
_ACCENT = "#89b4fa"
_BTN_PRIMARY = "#89b4fa"
_BTN_DANGER = "#f38ba8"
_SUCCESS = "#a6e3a1"
_WARNING = "#f9e2af"
_ERROR = "#f38ba8"
_FONT = ("Segoe UI", 9)
_FONT_BOLD = ("Segoe UI", 9, "bold")
_FONT_TITLE = ("Segoe UI", 12, "bold")
_FONT_MONO = ("Consolas", 9)


class ApiKeyDialog(tk.Toplevel):
    """
    Modal dialog để nhập / cập nhật Gemini API key.

    Tham số:
        parent          - Cửa sổ cha (có thể None khi chạy standalone)
        on_saved        - Callback được gọi sau khi key lưu thành công
        is_first_run    - True: hiển thị thông báo "lần đầu cài đặt"
    """

    def __init__(
        self,
        parent: Optional[tk.Misc],
        on_saved: Optional[Callable[[str], None]] = None,
        is_first_run: bool = False,
    ):
        super().__init__(parent)
        self._on_saved = on_saved
        self._is_first_run = is_first_run
        self._verify_thread: Optional[threading.Thread] = None

        self.title("Cài đặt API Key — Game Audio Translator")
        self.resizable(False, False)
        self.configure(bg=_BG)
        self.grab_set()  # Modal

        if parent:
            self.transient(parent)
            self.deiconify()  # macOS: transient to withdrawn parent hides Toplevel

        self._build()
        self._center()

        # Nếu đã có key, điền sẵn vào ô (che một phần)
        existing = get_api_key()
        if existing:
            self._key_var.set(existing)

    # ── Build UI ─────────────────────────────────────────────────────────────

    def _build(self):
        # Tiêu đề
        header = tk.Frame(self, bg=_BG, pady=16, padx=20)
        header.pack(fill=tk.X)

        tk.Label(
            header,
            text="Gemini API Key",
            bg=_BG,
            fg=_FG,
            font=_FONT_TITLE,
        ).pack(anchor="w")

        if self._is_first_run:
            tk.Label(
                header,
                text="Lần đầu sử dụng — vui lòng nhập API key để tiếp tục.",
                bg=_BG,
                fg=_FG_HINT,
                font=_FONT,
                wraplength=380,
                justify="left",
            ).pack(anchor="w", pady=(4, 0))
        else:
            tk.Label(
                header,
                text="Thay đổi Gemini API key. Key được lưu bảo mật trong\n"
                     "OS Keyring (Windows Credential Manager / macOS Keychain / Linux Secret Service).",
                bg=_BG,
                fg=_FG_HINT,
                font=_FONT,
                wraplength=380,
                justify="left",
            ).pack(anchor="w", pady=(4, 0))

        # Card chứa input
        card = tk.Frame(self, bg=_BG_CARD, padx=16, pady=14)
        card.pack(fill=tk.X, padx=20, pady=(0, 8))

        tk.Label(
            card,
            text="API Key",
            bg=_BG_CARD,
            fg=_FG,
            font=_FONT_BOLD,
        ).pack(anchor="w", pady=(0, 4))

        # Ô nhập key
        input_row = tk.Frame(card, bg=_BG_CARD)
        input_row.pack(fill=tk.X)

        self._key_var = tk.StringVar()
        self._show_key = tk.BooleanVar(value=False)

        self._key_entry = tk.Entry(
            input_row,
            textvariable=self._key_var,
            show="•",
            font=_FONT_MONO,
            bg=_BG_INPUT,
            fg=_FG,
            insertbackground=_FG,
            relief=tk.FLAT,
            width=38,
        )
        self._key_entry.pack(side=tk.LEFT, ipady=6, ipadx=4)
        self._key_entry.bind("<Return>", lambda _: self._on_save())

        # Nút hiện/ẩn key
        self._eye_btn = tk.Button(
            input_row,
            text="👁",
            bg=_BG_INPUT,
            fg=_FG_DIM,
            relief=tk.FLAT,
            cursor="hand2",
            font=("Segoe UI", 10),
            command=self._toggle_visibility,
        )
        self._eye_btn.pack(side=tk.LEFT, padx=(2, 0), ipady=4, ipadx=4)

        # Hint lấy API key
        hint_frame = tk.Frame(card, bg=_BG_CARD)
        hint_frame.pack(fill=tk.X, pady=(6, 0))
        tk.Label(
            hint_frame,
            text="Lấy miễn phí tại:",
            bg=_BG_CARD,
            fg=_FG_DIM,
            font=_FONT,
        ).pack(side=tk.LEFT)
        link = tk.Label(
            hint_frame,
            text="aistudio.google.com",
            bg=_BG_CARD,
            fg=_ACCENT,
            font=_FONT,
            cursor="hand2",
        )
        link.pack(side=tk.LEFT, padx=(4, 0))
        link.bind("<Button-1>", lambda _: self._open_link("https://aistudio.google.com"))

        # Thanh trạng thái verify
        self._status_var = tk.StringVar(value="")
        self._status_label = tk.Label(
            self,
            textvariable=self._status_var,
            bg=_BG,
            fg=_FG_DIM,
            font=_FONT,
            wraplength=400,
            justify="left",
        )
        self._status_label.pack(fill=tk.X, padx=20, pady=(0, 4))

        # Nút hành động
        btn_row = tk.Frame(self, bg=_BG)
        btn_row.pack(fill=tk.X, padx=20, pady=(4, 16))

        self._verify_btn = tk.Button(
            btn_row,
            text="Xác minh",
            bg=_BG_CARD,
            fg=_FG,
            font=_FONT_BOLD,
            relief=tk.FLAT,
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._on_verify,
        )
        self._verify_btn.pack(side=tk.LEFT, padx=(0, 8))

        self._save_btn = tk.Button(
            btn_row,
            text="Lưu và tiếp tục" if self._is_first_run else "Lưu",
            bg=_BTN_PRIMARY,
            fg="#1e1e2e",
            font=_FONT_BOLD,
            relief=tk.FLAT,
            padx=14,
            pady=5,
            cursor="hand2",
            command=self._on_save,
        )
        self._save_btn.pack(side=tk.LEFT)

        if not self._is_first_run:
            tk.Button(
                btn_row,
                text="Hủy",
                bg=_BG_CARD,
                fg=_FG_DIM,
                font=_FONT,
                relief=tk.FLAT,
                padx=12,
                pady=5,
                cursor="hand2",
                command=self.destroy,
            ).pack(side=tk.RIGHT)

        self._key_entry.focus_set()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _toggle_visibility(self):
        showing = self._show_key.get()
        self._show_key.set(not showing)
        self._key_entry.config(show="" if not showing else "•")
        self._eye_btn.config(fg=_ACCENT if not showing else _FG_DIM)

    def _set_status(self, text: str, color: str = _FG_DIM):
        self._status_var.set(text)
        self._status_label.config(fg=color)

    def _on_verify(self):
        key = self._key_var.get().strip()
        if not key:
            self._set_status("Vui lòng nhập API key trước.", _WARNING)
            return

        self._set_status("Đang xác minh...", _FG_DIM)
        self._verify_btn.config(state=tk.DISABLED)
        self._save_btn.config(state=tk.DISABLED)

        def verify_worker():
            ok, msg = self._test_api_key(key)
            self.after(0, lambda: self._on_verify_done(ok, msg))

        self._verify_thread = threading.Thread(target=verify_worker, daemon=True)
        self._verify_thread.start()

    def _on_verify_done(self, ok: bool, msg: str):
        self._verify_btn.config(state=tk.NORMAL)
        self._save_btn.config(state=tk.NORMAL)
        if ok:
            self._set_status(f"Key hợp lệ — {msg}", _SUCCESS)
        else:
            self._set_status(f"Key không hợp lệ: {msg}", _ERROR)

    def _test_api_key(self, key: str) -> tuple[bool, str]:
        """Gọi Gemini API với key để kiểm tra tính hợp lệ."""
        try:
            from google import genai
            client = genai.Client(api_key=key)
            resp = client.models.generate_content(
                model="gemini-1.5-flash",
                contents="Reply with just the word: OK",
            )
            return True, resp.text.strip()[:60]
        except Exception as e:
            err = str(e)
            if "API_KEY_INVALID" in err or "invalid" in err.lower():
                return False, "API key không hợp lệ"
            if "quota" in err.lower():
                return False, "Hết quota (nhưng key hợp lệ)"
            return False, err[:80]

    def _on_save(self):
        key = self._key_var.get().strip()
        if not key:
            self._set_status("Vui lòng nhập API key.", _WARNING)
            return
        if not key.startswith("AIza"):
            self._set_status(
                "API key Gemini thường bắt đầu bằng 'AIza'. Kiểm tra lại?",
                _WARNING,
            )

        ok = save_api_key(key)
        if not ok:
            messagebox.showerror(
                "Lỗi",
                "Không thể lưu key vào OS keyring.\n"
                "Thử chạy ứng dụng với quyền Admin.",
                parent=self,
            )
            return

        self._set_status("Đã lưu thành công!", _SUCCESS)

        if self._on_saved:
            self._on_saved(key)

        self.after(600, self.destroy)

    @staticmethod
    def _open_link(url: str):
        import webbrowser
        webbrowser.open(url)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _center(self):
        self.update_idletasks()
        w = self.winfo_width() or 440
        h = self.winfo_height() or 300
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"+{x}+{y}")


def prompt_api_key(
    parent: Optional[tk.Misc] = None,
    on_saved: Optional[Callable[[str], None]] = None,
    is_first_run: bool = False,
) -> None:
    """Mở dialog API key. Dùng khi chưa có parent window."""
    dlg = ApiKeyDialog(parent, on_saved=on_saved, is_first_run=is_first_run)
    if parent:
        parent.wait_window(dlg)
    else:
        dlg.mainloop()
