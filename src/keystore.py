"""
Lưu trữ API keys trong settings.json (~/Library/Application Support/GameAudioTranslator/).
Không dùng OS Keychain — không bao giờ hiện dialog mật khẩu.
"""
import logging

from src.settings_store import load, save

logger = logging.getLogger(__name__)

_PROVIDERS = {
    "gemini":    "gemini_api_key",
    "openai":    "openai_api_key",
    "anthropic": "anthropic_api_key",
}


def get_api_key(provider: str = "gemini") -> str:
    key_name = _PROVIDERS.get(provider)
    if not key_name:
        return ""
    return load().get(key_name, "") or ""


def has_api_key(provider: str = "gemini") -> bool:
    return bool(get_api_key(provider))


def save_api_key(provider: str, api_key: str) -> bool:
    key_name = _PROVIDERS.get(provider)
    if not key_name:
        return False
    s = load()
    s[key_name] = api_key.strip()
    if save(s):
        logger.info(f"API key [{provider}] đã lưu vào settings.json")
        return True
    return False
