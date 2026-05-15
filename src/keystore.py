"""
Lưu trữ API keys bảo mật thông qua OS keyring:
  - Windows  → Windows Credential Manager
  - macOS    → Keychain
  - Linux    → GNOME Keyring / KWallet
"""
import logging

logger = logging.getLogger(__name__)

_SERVICE = "GameAudioTranslator"

_PROVIDERS = {
    "gemini":    "gemini_api_key",
    "openai":    "openai_api_key",
    "anthropic": "anthropic_api_key",
}


def _get_keyring():
    try:
        import keyring
        return keyring
    except ImportError:
        return None


def get_api_key(provider: str = "gemini") -> str:
    kr = _get_keyring()
    key_name = _PROVIDERS.get(provider, "")
    if kr and key_name:
        try:
            return kr.get_password(_SERVICE, key_name) or ""
        except Exception as e:
            logger.error(f"Không đọc được keyring [{provider}]: {e}")
    return ""


def save_api_key(provider: str, api_key: str) -> bool:
    kr = _get_keyring()
    key_name = _PROVIDERS.get(provider, "")
    if not kr or not key_name:
        logger.error(f"Keyring không khả dụng hoặc provider không hợp lệ: {provider}")
        return False
    try:
        kr.set_password(_SERVICE, key_name, api_key.strip())
        logger.info(f"API key [{provider}] đã lưu vào OS keyring")
        return True
    except Exception as e:
        logger.error(f"Không lưu được keyring [{provider}]: {e}")
        return False


def delete_api_key(provider: str = "gemini") -> bool:
    kr = _get_keyring()
    key_name = _PROVIDERS.get(provider, "")
    if not kr or not key_name:
        return False
    try:
        kr.delete_password(_SERVICE, key_name)
        return True
    except Exception:
        return False


def has_api_key(provider: str = "gemini") -> bool:
    return bool(get_api_key(provider))


def list_providers() -> list[str]:
    return list(_PROVIDERS.keys())
