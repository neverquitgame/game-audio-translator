"""
Lưu cài đặt ứng dụng vào OS config directory (không dùng .env).
    Windows: %APPDATA%\\GameAudioTranslator\\settings.json
    macOS:   ~/Library/Application Support/GameAudioTranslator/settings.json
    Linux:   ~/.config/GameAudioTranslator/settings.json
"""
from platformdirs import user_config_dir
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

_APP_NAME = "GameAudioTranslator"
_APP_AUTHOR = None

DEFAULTS: dict = {
    "whisper_model": "base",
    "whisper_language": "en",
    "target_language": "Vietnamese",
    "vad_aggressiveness": 2,
    "sample_rate": 16000,
    "chunk_duration_ms": 30,
    "gemini_model": "gemini-2.5-flash",
    "llm_priority": ["gemini"],
    "onboarding_completed": False,
    "preferred_device_index": None,
    # API keys stored here instead of OS Keychain to avoid password dialogs
    "gemini_api_key": "",
    "openai_api_key": "",
    "anthropic_api_key": "",
    # Noise filtering settings
    "enable_noise_filter": True,
    "noise_filter_strength": 0.3,  # 0.0-1.0, higher = more aggressive
    "energy_threshold_db": -35,     # Minimum energy level in dB
    "min_transcription_confidence": 0.4,  # 0.0-1.0, minimum confidence to send to LLM
    # UI
    "always_on_top": True,
}


def config_path() -> Path:
    d = Path(user_config_dir(_APP_NAME, _APP_AUTHOR))
    d.mkdir(parents=True, exist_ok=True)
    return d / "settings.json"


def load() -> dict:
    path = config_path()
    if path.exists():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            merged = {**DEFAULTS, **saved}
            # Người dùng cũ (trước onboarding): bỏ qua wizard lần đầu nâng cấp
            if "onboarding_completed" not in saved:
                merged["onboarding_completed"] = True
            return merged
        except Exception as e:
            logger.warning(f"Không đọc được settings.json, dùng defaults: {e}")
    return DEFAULTS.copy()


def save(settings: dict) -> bool:
    try:
        config_path().write_text(
            json.dumps(settings, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return True
    except Exception as e:
        logger.error(f"Không lưu được settings: {e}")
        return False


def migrate_from_env_if_needed():
    """
    Nếu lần đầu chạy Phase 2 mà vẫn còn .env cũ, migrate sang settings.json.
    Chạy 1 lần rồi thôi.
    """
    import sys
    from pathlib import Path as _Path

    if getattr(sys, "frozen", False):
        env_path = _Path(sys.executable).parent / ".env"
    else:
        env_path = _Path(__file__).parent.parent / ".env"

    if not env_path.exists() or config_path().exists():
        return

    try:
        from dotenv import dotenv_values
        values = dotenv_values(env_path)
    except ImportError:
        values = {}
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                values[k.strip()] = v.strip()

    mapping = {
        "WHISPER_MODEL": "whisper_model",
        "TARGET_LANGUAGE": "target_language",
        "VAD_AGGRESSIVENESS": "vad_aggressiveness",
        "SAMPLE_RATE": "sample_rate",
        "CHUNK_DURATION_MS": "chunk_duration_ms",
        "GEMINI_MODEL": "gemini_model",
    }
    settings = DEFAULTS.copy()
    for env_key, cfg_key in mapping.items():
        if env_key in values and values[env_key]:
            val = values[env_key]
            if cfg_key in ("vad_aggressiveness", "sample_rate", "chunk_duration_ms"):
                try:
                    val = int(val)
                except ValueError:
                    pass
            settings[cfg_key] = val

    save(settings)
    logger.info(f"Đã migrate settings từ {env_path} sang {config_path()}")
