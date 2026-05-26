from src.settings_store import load as _load_settings, migrate_from_env_if_needed
from src.keystore import get_api_key

migrate_from_env_if_needed()

_s = _load_settings()


class Config:
    # API keys — intentionally empty at import time to avoid triggering OS
    # password dialogs during module loading. Call Config.reload_api_keys()
    # explicitly from the main thread before use.
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # --- Settings (settings.json) ---
    GEMINI_MODEL: str = _s["gemini_model"]
    WHISPER_MODEL: str = _s["whisper_model"]
    WHISPER_LANGUAGE: str = _s["whisper_language"]
    TARGET_LANGUAGE: str = _s["target_language"]
    VAD_AGGRESSIVENESS: int = int(_s["vad_aggressiveness"])
    SAMPLE_RATE: int = int(_s["sample_rate"])
    CHUNK_DURATION_MS: int = int(_s["chunk_duration_ms"])
    LLM_PRIORITY: list[str] = _s["llm_priority"]

    # Noise filtering settings
    ENABLE_NOISE_FILTER: bool = _s.get("enable_noise_filter", True)
    NOISE_FILTER_STRENGTH: float = float(_s.get("noise_filter_strength", 0.3))
    ENERGY_THRESHOLD_DB: float = float(_s.get("energy_threshold_db", -35))
    MIN_TRANSCRIPTION_CONFIDENCE: float = float(_s.get("min_transcription_confidence", 0.4))

    @classmethod
    def reload(cls):
        """Reload settings from disk. Does NOT re-fetch API keys."""
        s = _load_settings()
        cls.GEMINI_MODEL = s["gemini_model"]
        cls.WHISPER_MODEL = s["whisper_model"]
        cls.WHISPER_LANGUAGE = s["whisper_language"]
        cls.TARGET_LANGUAGE = s["target_language"]
        cls.VAD_AGGRESSIVENESS = int(s["vad_aggressiveness"])
        cls.SAMPLE_RATE = int(s["sample_rate"])
        cls.CHUNK_DURATION_MS = int(s["chunk_duration_ms"])
        cls.LLM_PRIORITY = s["llm_priority"]
        cls.ENABLE_NOISE_FILTER = s.get("enable_noise_filter", True)
        cls.NOISE_FILTER_STRENGTH = float(s.get("noise_filter_strength", 0.3))
        cls.ENERGY_THRESHOLD_DB = float(s.get("energy_threshold_db", -35))
        cls.MIN_TRANSCRIPTION_CONFIDENCE = float(s.get("min_transcription_confidence", 0.4))

    @classmethod
    def reload_api_keys(cls, only_priority: bool = False):
        """Đọc API key từ store. Gọi từ main thread.

        only_priority=True: chỉ load các provider trong LLM_PRIORITY (giảm I/O lúc bootstrap).
        only_priority=False: load tất cả (dùng sau khi user đổi settings).
        """
        wanted = set(cls.LLM_PRIORITY) if (only_priority and cls.LLM_PRIORITY) else {
            "gemini", "openai", "anthropic"
        }
        if "gemini" in wanted:
            cls.GEMINI_API_KEY = get_api_key("gemini")
        if "openai" in wanted:
            cls.OPENAI_API_KEY = get_api_key("openai")
        if "anthropic" in wanted:
            cls.ANTHROPIC_API_KEY = get_api_key("anthropic")

    @classmethod
    def reload_with_keys(cls):
        """Backward-compat: reload settings + tất cả API key."""
        cls.reload()
        cls.reload_api_keys(only_priority=False)
