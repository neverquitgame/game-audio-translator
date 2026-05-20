from src.settings_store import load as _load_settings, migrate_from_env_if_needed
from src.keystore import get_api_key

# Migrate .env → settings.json nếu lần đầu chạy Phase 2
migrate_from_env_if_needed()

_s = _load_settings()


class Config:
    # API keys — intentionally empty at import time to avoid triggering macOS
    # Keychain dialogs during module loading. Call Config.reload() or
    # Config.load_api_keys() explicitly from the main thread before use.
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
    def load_api_keys(cls):
        """Fetch API keys from OS keychain. Call ONCE from the main thread.
        Only fetches keys for providers actually in LLM_PRIORITY to minimise
        the number of macOS Keychain permission dialogs shown to the user."""
        needed = set(cls.LLM_PRIORITY) if cls.LLM_PRIORITY else {"gemini"}
        if "gemini" in needed:
            cls.GEMINI_API_KEY = get_api_key("gemini")
        if "openai" in needed:
            cls.OPENAI_API_KEY = get_api_key("openai")
        if "anthropic" in needed:
            cls.ANTHROPIC_API_KEY = get_api_key("anthropic")

    @classmethod
    def reload(cls):
        """Reload settings from disk. Does NOT re-fetch keychain keys."""
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
    def reload_with_keys(cls):
        """Reload settings AND re-fetch ALL API keys (call from main thread only,
        e.g. after user changes LLM_PRIORITY in Settings)."""
        cls.reload()
        cls.GEMINI_API_KEY = get_api_key("gemini")
        cls.OPENAI_API_KEY = get_api_key("openai")
        cls.ANTHROPIC_API_KEY = get_api_key("anthropic")

    @classmethod
    def validate(cls) -> list[str]:
        errors = []
        active = cls.LLM_PRIORITY[0] if cls.LLM_PRIORITY else "gemini"
        if active == "gemini" and not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY chưa được cài đặt")
        if active == "openai" and not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY chưa được cài đặt")
        if active == "anthropic" and not cls.ANTHROPIC_API_KEY:
            errors.append("ANTHROPIC_API_KEY chưa được cài đặt")
        if cls.VAD_AGGRESSIVENESS not in range(4):
            errors.append("VAD_AGGRESSIVENESS phải từ 0-3")
        if cls.SAMPLE_RATE not in (8000, 16000, 32000, 48000):
            errors.append("SAMPLE_RATE phải là 8000/16000/32000/48000")
        if cls.CHUNK_DURATION_MS not in (10, 20, 30):
            errors.append("CHUNK_DURATION_MS phải là 10/20/30")
        return errors
