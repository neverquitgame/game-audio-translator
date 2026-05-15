"""
Lưu trữ API key bảo mật thông qua OS keyring:
  - Windows  → Windows Credential Manager
  - macOS    → Keychain
  - Linux    → Secret Service (GNOME Keyring / KWallet)

Fallback: khi keyring không khả dụng, đọc/ghi từ file .env trong thư mục gốc dự án.
"""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_SERVICE = "GameAudioTranslator"
_KEY_GEMINI = "gemini_api_key"

if getattr(sys, "frozen", False):
    _ENV_PATH = Path(sys.executable).parent / ".env"
else:
    _ENV_PATH = Path(__file__).parent.parent / ".env"


def _get_keyring():
    """Import keyring lazily — tránh lỗi import khi chưa cài."""
    try:
        import keyring
        return keyring
    except ImportError:
        return None


def _env_get_key() -> str:
    """Đọc GEMINI_API_KEY từ biến môi trường (bao gồm .env đã load)."""
    return os.getenv("GEMINI_API_KEY", "")


def _env_save_key(api_key: str) -> bool:
    """Ghi GEMINI_API_KEY vào file .env (fallback khi keyring không có)."""
    try:
        lines: list[str] = []
        if _ENV_PATH.exists():
            lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()

        key_line = f"GEMINI_API_KEY={api_key.strip()}"
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("GEMINI_API_KEY="):
                lines[i] = key_line
                updated = True
                break
        if not updated:
            lines.append(key_line)

        _ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        # Cập nhật luôn vào biến môi trường hiện tại
        os.environ["GEMINI_API_KEY"] = api_key.strip()
        logger.info("API key đã lưu vào .env (fallback — keyring không khả dụng)")
        return True
    except Exception as e:
        logger.error(f"Không ghi được .env: {e}")
        return False


def get_api_key() -> str:
    """Lấy Gemini API key. Ưu tiên: keyring → biến môi trường / .env."""
    kr = _get_keyring()
    if kr is not None:
        try:
            value = kr.get_password(_SERVICE, _KEY_GEMINI)
            if value:
                return value
        except Exception as e:
            logger.error(f"Không đọc được keyring: {e}")
    return _env_get_key()


def save_api_key(api_key: str) -> bool:
    """Lưu Gemini API key. Ưu tiên keyring, fallback về .env."""
    kr = _get_keyring()
    if kr is not None:
        try:
            kr.set_password(_SERVICE, _KEY_GEMINI, api_key.strip())
            logger.info("API key đã lưu vào OS keyring")
            return True
        except Exception as e:
            logger.error(f"Không lưu được vào keyring: {e}")
    return _env_save_key(api_key)


def delete_api_key() -> bool:
    """Xóa API key khỏi OS keyring và file .env (nếu có)."""
    deleted = False

    kr = _get_keyring()
    if kr is not None:
        try:
            kr.delete_password(_SERVICE, _KEY_GEMINI)
            deleted = True
        except Exception:
            pass

    # Xóa luôn khỏi .env (fallback)
    try:
        if _ENV_PATH.exists():
            lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()
            new_lines = [l for l in lines if not l.startswith("GEMINI_API_KEY=")]
            if len(new_lines) != len(lines):
                _ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                deleted = True
        os.environ.pop("GEMINI_API_KEY", None)
    except Exception as e:
        logger.error(f"Không xóa được GEMINI_API_KEY khỏi .env: {e}")

    return deleted


def has_api_key() -> bool:
    """Kiểm tra xem đã có API key chưa."""
    return bool(get_api_key())
