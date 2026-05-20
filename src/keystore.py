"""
Lưu trữ API keys trong settings.json (~/Library/Application Support/GameAudioTranslator/).
Không dùng OS Keychain — không bao giờ hiện dialog mật khẩu.
"""
import logging

logger = logging.getLogger(__name__)

_PROVIDERS = {
    "gemini":    "gemini_api_key",
    "openai":    "openai_api_key",
    "anthropic": "anthropic_api_key",
}


def _settings_get(provider: str) -> str:
    from src.settings_store import load
    key_name = _PROVIDERS.get(provider, "")
    if not key_name:
        return ""
    return load().get(key_name, "") or ""


def _settings_set(provider: str, api_key: str) -> bool:
    from src.settings_store import load, save
    key_name = _PROVIDERS.get(provider, "")
    if not key_name:
        return False
    s = load()
    s[key_name] = api_key.strip()
    return save(s)


def get_api_key(provider: str = "gemini") -> str:
    return _settings_get(provider)


def save_api_key(provider: str, api_key: str) -> bool:
    ok = _settings_set(provider, api_key)
    if ok:
        logger.info(f"API key [{provider}] đã lưu vào settings.json")
    return ok


def delete_api_key(provider: str = "gemini") -> bool:
    return _settings_set(provider, "")


def has_api_key(provider: str = "gemini") -> bool:
    return bool(get_api_key(provider))


def list_providers() -> list[str]:
    return list(_PROVIDERS.keys())
