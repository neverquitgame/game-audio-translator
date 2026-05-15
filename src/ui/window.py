import tkinter as tk
from tkinter import ttk, scrolledtext
import logging
import threading
from typing import Callable, Optional

from src.settings_store import load as load_settings, save as save_settings
from src.keystore import get_api_key, save_api_key

logger = logging.getLogger(__name__)

_WIN_WIDTH = 560
_WIN_HEIGHT = 500
_FONT_LABEL = ("Segoe UI", 9, "bold")
_FONT_TEXT = ("Segoe UI", 10)
_FONT_STATUS = ("Segoe UI", 8)
_FONT_SMALL = ("Segoe UI", 9)
_BG = "#1e1e2e"
_BG_TEXT = "#2a2a3d"
_BG_INPUT = "#313244"
_FG = "#cdd6f4"
_FG_DIM = "#6c7086"
_FG_HINT = "#9399b2"
_ACCENT = "#89b4fa"
_BTN_START = "#a6e3a1"
_BTN_STOP = "#f38ba8"
_SUCCESS = "#a6e3a1"
_WARNING = "#f9e2af"
_ERROR = "#f38ba8"


class TranslatorUI:
    def __init__(
        self,
        devices: list[dict],
        on_start: Callable[[Optional[int]], None],
        on_stop: Callable[[], None],
        on_settings_changed: Optional[Callable[[dict], None]] = None,
    ):
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_settings_changed = on_settings_changed
        self._running = False
        self._devices = devices
        self._settings = load_settings()

        self.root = tk.Tk()
        self._build()

    # ── Build ────────────────────────────────────────────────────────────────

    def _build(self):
        root = self.root
        root.title("Game Audio Translator")
        root.geometry(f"{_WIN_WIDTH}x{_WIN_HEIGHT}")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg=_BG)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=_BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=_BG_TEXT, foreground=_FG,
                        font=_FONT_LABEL, padding=[12, 5])
        style.map("TNotebook.Tab",
                  background=[("selected", _BG), ("active", _BG_INPUT)],
                  foreground=[("selected", _ACCENT)])
        style.configure("TCombobox", fieldbackground=_BG_INPUT,
                        background=_BG_INPUT, foreground=_FG,
                        selectbackground=_BG_INPUT, selectforeground=_FG)
        style.configure("TScale", background=_BG, troughcolor=_BG_INPUT)
        style.configure("Vertical.TScrollbar", background=_BG_INPUT,
                        troughcolor=_BG, bordercolor=_BG, arrowcolor=_FG_DIM)

        self._notebook = ttk.Notebook(root)
        self._notebook.pack(fill=tk.BOTH, expand=True)

        self._build_translate_tab()
        self._build_settings_tab()

        # Status bar (outside notebook, always visible)
        status_frame = tk.Frame(root, bg="#13131f", pady=4)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self._status_var = tk.StringVar(value="⏸  Đang chờ")
        tk.Label(status_frame, textvariable=self._status_var,
                 bg="#13131f", fg=_FG_DIM, font=_FONT_STATUS).pack(side=tk.LEFT, padx=10)

    def _build_translate_tab(self):
        tab = tk.Frame(self._notebook, bg=_BG)
        self._notebook.add(tab, text="🎙  Dịch")

        # Control bar
        ctrl = tk.Frame(tab, bg=_BG, pady=8, padx=10)
        ctrl.pack(fill=tk.X)

        tk.Label(ctrl, text="Thiết bị âm thanh:", bg=_BG, fg=_FG,
                 font=_FONT_LABEL).pack(side=tk.LEFT)

        device_names = [d["name"] for d in self._devices] if self._devices else ["(Không tìm thấy thiết bị)"]
        self._device_var = tk.StringVar()
        self._device_combo = ttk.Combobox(ctrl, textvariable=self._device_var,
                                           values=device_names, state="readonly", width=26)
        if device_names:
            self._device_combo.current(0)
        self._device_combo.pack(side=tk.LEFT, padx=(6, 10))

        self._toggle_btn = tk.Button(
            ctrl, text="▶  Bắt đầu", bg=_BTN_START, fg="#1e1e2e",
            font=_FONT_LABEL, relief=tk.FLAT, padx=10, pady=3,
            cursor="hand2", command=self._on_toggle,
        )
        self._toggle_btn.pack(side=tk.LEFT)

        # LLM indicator
        self._llm_var = tk.StringVar(value="")
        tk.Label(ctrl, textvariable=self._llm_var, bg=_BG, fg=_FG_DIM,
                 font=_FONT_STATUS).pack(side=tk.RIGHT, padx=8)

        # Text display
        display = tk.Frame(tab, bg=_BG, padx=10)
        display.pack(fill=tk.BOTH, expand=True)

        tk.Label(display, text="Gốc:", bg=_BG, fg=_ACCENT,
                 font=_FONT_LABEL, anchor="w").pack(fill=tk.X)
        self._original_box = scrolledtext.ScrolledText(
            display, height=5, wrap=tk.WORD, font=_FONT_TEXT,
            bg=_BG_TEXT, fg=_FG, insertbackground=_FG,
            relief=tk.FLAT, state=tk.DISABLED,
        )
        self._original_box.pack(fill=tk.X, pady=(0, 6))

        tk.Label(display, text="Dịch:", bg=_BG, fg=_ACCENT,
                 font=_FONT_LABEL, anchor="w").pack(fill=tk.X)
        self._translated_box = scrolledtext.ScrolledText(
            display, height=5, wrap=tk.WORD, font=_FONT_TEXT,
            bg=_BG_TEXT, fg=_FG, insertbackground=_FG,
            relief=tk.FLAT, state=tk.DISABLED,
        )
        self._translated_box.pack(fill=tk.X)

        # Copy button
        copy_row = tk.Frame(tab, bg=_BG, padx=10, pady=4)
        copy_row.pack(fill=tk.X)
        tk.Button(copy_row, text="📋 Copy bản dịch", bg=_BG_INPUT, fg=_FG,
                  font=_FONT_SMALL, relief=tk.FLAT, padx=8, pady=2,
                  cursor="hand2", command=self._copy_translation).pack(side=tk.RIGHT)

    def _build_settings_tab(self):
        tab = tk.Frame(self._notebook, bg=_BG)
        self._notebook.add(tab, text="⚙  Cài đặt")

        canvas = tk.Canvas(tab, bg=_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=_BG)
        canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        inner.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        pad = {"padx": 14, "pady": 4}

        # ── API Keys ─────────────────────────────────────────────────────────
        self._section_header(inner, "🔑  API Keys")

        self._api_key_entries = {}
        for provider, label in [("gemini", "Gemini"), ("openai", "OpenAI"), ("anthropic", "Anthropic")]:
            row = tk.Frame(inner, bg=_BG)
            row.pack(fill=tk.X, **pad)
            tk.Label(row, text=f"{label}:", bg=_BG, fg=_FG, font=_FONT_LABEL,
                     width=10, anchor="w").pack(side=tk.LEFT)

            var = tk.StringVar(value=get_api_key(provider))
            entry = tk.Entry(row, textvariable=var, show="•", font=("Consolas", 9),
                             bg=_BG_INPUT, fg=_FG, insertbackground=_FG,
                             relief=tk.FLAT, width=30)
            entry.pack(side=tk.LEFT, ipady=5, ipadx=4, padx=(0, 4))
            self._api_key_entries[provider] = var

            show_var = tk.BooleanVar(value=False)

            def _toggle(e=entry, sv=show_var):
                sv.set(not sv.get())
                e.config(show="" if sv.get() else "•")

            tk.Button(row, text="👁", bg=_BG_INPUT, fg=_FG_DIM, relief=tk.FLAT,
                      cursor="hand2", font=("Segoe UI", 10), command=_toggle,
                      padx=4, pady=3).pack(side=tk.LEFT, padx=(0, 4))

            status_var = tk.StringVar(value="")
            tk.Label(row, textvariable=status_var, bg=_BG, fg=_FG_DIM,
                     font=_FONT_STATUS).pack(side=tk.LEFT, padx=(4, 0))

            def _verify(p=provider, v=var, sv=status_var):
                key = v.get().strip()
                if not key:
                    sv.set("Chưa nhập key")
                    return
                sv.set("Đang xác minh...")

                def _worker(p=p, key=key, sv=sv):
                    ok = self._verify_key(p, key)
                    self.root.after(0, lambda: sv.set("✓ Hợp lệ" if ok else "✗ Không hợp lệ"))

                threading.Thread(target=_worker, daemon=True).start()

            tk.Button(row, text="Xác minh", bg=_BG_INPUT, fg=_FG, relief=tk.FLAT,
                      cursor="hand2", font=_FONT_SMALL, padx=6, pady=3,
                      command=_verify).pack(side=tk.LEFT, padx=(4, 0))

        # ── LLM Priority ─────────────────────────────────────────────────────
        self._section_header(inner, "🤖  Thứ tự ưu tiên LLM (fallback)")

        priority_row = tk.Frame(inner, bg=_BG)
        priority_row.pack(fill=tk.X, **pad)
        tk.Label(priority_row, text="Ưu tiên:", bg=_BG, fg=_FG,
                 font=_FONT_LABEL, width=10, anchor="w").pack(side=tk.LEFT)

        priority_options = ["gemini", "openai", "anthropic", "ollama"]
        current_priority = self._settings.get("llm_priority", ["gemini"])
        self._llm_priority_var = tk.StringVar(value=current_priority[0] if current_priority else "gemini")
        combo = ttk.Combobox(priority_row, textvariable=self._llm_priority_var,
                             values=priority_options, state="readonly", width=16)
        combo.pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(priority_row, text="(fallback tự động khi bị rate limit)",
                 bg=_BG, fg=_FG_DIM, font=_FONT_STATUS).pack(side=tk.LEFT)

        # ── Whisper ───────────────────────────────────────────────────────────
        self._section_header(inner, "🎙  Nhận dạng giọng nói (Whisper)")

        model_row = tk.Frame(inner, bg=_BG)
        model_row.pack(fill=tk.X, **pad)
        tk.Label(model_row, text="Model:", bg=_BG, fg=_FG, font=_FONT_LABEL,
                 width=10, anchor="w").pack(side=tk.LEFT)
        self._whisper_model_var = tk.StringVar(value=self._settings.get("whisper_model", "base"))
        ttk.Combobox(model_row, textvariable=self._whisper_model_var,
                     values=["tiny", "base", "small", "medium"], state="readonly",
                     width=14).pack(side=tk.LEFT, padx=(0, 16))

        tk.Label(model_row, text="Ngôn ngữ:", bg=_BG, fg=_FG, font=_FONT_LABEL).pack(side=tk.LEFT)
        self._whisper_lang_var = tk.StringVar(value=self._settings.get("whisper_language", "en"))
        ttk.Combobox(model_row, textvariable=self._whisper_lang_var,
                     values=["en", "ja", "ko", "zh", "auto"], state="readonly",
                     width=8).pack(side=tk.LEFT)

        # ── VAD ───────────────────────────────────────────────────────────────
        self._section_header(inner, "🔊  Phát hiện giọng nói (VAD)")

        vad_row = tk.Frame(inner, bg=_BG)
        vad_row.pack(fill=tk.X, **pad)
        tk.Label(vad_row, text="Độ nhạy:", bg=_BG, fg=_FG, font=_FONT_LABEL,
                 width=10, anchor="w").pack(side=tk.LEFT)
        self._vad_var = tk.IntVar(value=self._settings.get("vad_aggressiveness", 2))
        vad_label = tk.Label(vad_row, textvariable=self._vad_var, bg=_BG,
                             fg=_ACCENT, font=_FONT_LABEL, width=2)

        def _update_vad_label(val):
            self._vad_var.set(int(float(val)))

        ttk.Scale(vad_row, from_=0, to=3, orient=tk.HORIZONTAL,
                  variable=self._vad_var, command=_update_vad_label,
                  length=120).pack(side=tk.LEFT, padx=(0, 6))
        vad_label.pack(side=tk.LEFT)
        tk.Label(vad_row, text="(0=ít nhạy, 3=rất nhạy)", bg=_BG, fg=_FG_DIM,
                 font=_FONT_STATUS).pack(side=tk.LEFT, padx=(8, 0))

        # ── Target language ───────────────────────────────────────────────────
        self._section_header(inner, "🌐  Ngôn ngữ đích")

        tl_row = tk.Frame(inner, bg=_BG)
        tl_row.pack(fill=tk.X, **pad)
        tk.Label(tl_row, text="Dịch sang:", bg=_BG, fg=_FG, font=_FONT_LABEL,
                 width=10, anchor="w").pack(side=tk.LEFT)
        self._target_lang_var = tk.StringVar(value=self._settings.get("target_language", "Vietnamese"))
        ttk.Combobox(tl_row, textvariable=self._target_lang_var,
                     values=["Vietnamese", "English", "Japanese", "Korean", "Chinese"],
                     state="readonly", width=16).pack(side=tk.LEFT)

        # ── Save button ───────────────────────────────────────────────────────
        save_frame = tk.Frame(inner, bg=_BG, pady=12)
        save_frame.pack(fill=tk.X, padx=14)
        self._save_status_var = tk.StringVar(value="")
        tk.Label(save_frame, textvariable=self._save_status_var, bg=_BG,
                 fg=_SUCCESS, font=_FONT_SMALL).pack(side=tk.LEFT)
        tk.Button(save_frame, text="💾  Lưu cài đặt", bg=_ACCENT, fg="#1e1e2e",
                  font=_FONT_LABEL, relief=tk.FLAT, padx=14, pady=5,
                  cursor="hand2", command=self._save_settings).pack(side=tk.RIGHT)

    def _section_header(self, parent, text: str):
        f = tk.Frame(parent, bg=_BG, pady=2)
        f.pack(fill=tk.X, padx=14, pady=(10, 2))
        tk.Label(f, text=text, bg=_BG, fg=_ACCENT, font=_FONT_LABEL).pack(side=tk.LEFT)
        tk.Frame(f, bg=_FG_DIM, height=1).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0), pady=6)

    # ── Actions ──────────────────────────────────────────────────────────────

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

    def _copy_translation(self):
        text = self._translated_box.get("1.0", tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.update_status("📋  Đã copy bản dịch")

    def _verify_key(self, provider: str, key: str) -> bool:
        try:
            if provider == "gemini":
                from google import genai
                client = genai.Client(api_key=key)
                client.models.generate_content(model="gemini-2.0-flash", contents="Reply: OK")
                return True
            elif provider == "openai":
                from openai import OpenAI
                client = OpenAI(api_key=key)
                client.models.list()
                return True
            elif provider == "anthropic":
                import anthropic
                client = anthropic.Anthropic(api_key=key)
                client.messages.create(model="claude-haiku-4-5", max_tokens=10,
                                       messages=[{"role": "user", "content": "hi"}])
                return True
        except Exception:
            return False
        return False

    def _save_settings(self):
        for provider, var in self._api_key_entries.items():
            key = var.get().strip()
            if key:
                save_api_key(provider, key)

        new_settings = {
            **self._settings,
            "whisper_model": self._whisper_model_var.get(),
            "whisper_language": self._whisper_lang_var.get(),
            "target_language": self._target_lang_var.get(),
            "vad_aggressiveness": self._vad_var.get(),
            "llm_priority": [self._llm_priority_var.get()],
        }
        if save_settings(new_settings):
            self._settings = new_settings
            self._save_status_var.set("✓ Đã lưu")
            self.root.after(3000, lambda: self._save_status_var.set(""))
            if self._on_settings_changed:
                self._on_settings_changed(new_settings)
        else:
            self._save_status_var.set("✗ Lỗi khi lưu")

    # ── Public API ────────────────────────────────────────────────────────────

    def _set_text(self, widget: scrolledtext.ScrolledText, text: str):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)
        widget.config(state=tk.DISABLED)

    def update_translation(self, original: str, translated: str):
        self.root.after(0, lambda: self._set_text(self._original_box, original))
        self.root.after(0, lambda: self._set_text(self._translated_box, translated))

    def update_status(self, status: str):
        self.root.after(0, lambda: self._status_var.set(status))

    def update_active_llm(self, provider: str):
        self.root.after(0, lambda: self._llm_var.set(f"[{provider}]"))

    def run(self):
        self.root.mainloop()
