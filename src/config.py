import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Khi đóng gói bằng PyInstaller, .env phải nằm cạnh file .exe
if getattr(sys, "frozen", False):
    _base_dir = Path(sys.executable).parent
else:
    _base_dir = Path(__file__).parent.parent

load_dotenv(_base_dir / ".env")


def _resolve_api_key() -> str:
    """Ưu tiên: OS keyring → biến môi trường / .env → chuỗi rỗng."""
    from src.keystore import get_api_key as _keyring_get
    key = _keyring_get()
    if key:
        return key
    return os.getenv("GEMINI_API_KEY", "")


class Config:
    GEMINI_API_KEY: str = _resolve_api_key()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    TARGET_LANGUAGE: str = os.getenv("TARGET_LANGUAGE", "Vietnamese")
    VAD_AGGRESSIVENESS: int = int(os.getenv("VAD_AGGRESSIVENESS", "2"))
    SAMPLE_RATE: int = int(os.getenv("SAMPLE_RATE", "16000"))
    CHUNK_DURATION_MS: int = int(os.getenv("CHUNK_DURATION_MS", "30"))

    @classmethod
    def validate(cls) -> list[str]:
        errors = []
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is not set")
        if cls.VAD_AGGRESSIVENESS not in range(4):
            errors.append("VAD_AGGRESSIVENESS must be 0-3")
        if cls.SAMPLE_RATE not in (8000, 16000, 32000, 48000):
            errors.append("SAMPLE_RATE must be 8000, 16000, 32000, or 48000")
        if cls.CHUNK_DURATION_MS not in (10, 20, 30):
            errors.append("CHUNK_DURATION_MS must be 10, 20, or 30 (webrtcvad requirement)")
        return errors
