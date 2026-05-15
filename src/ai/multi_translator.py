"""
MultiTranslator: thử lần lượt các translator theo thứ tự ưu tiên.
Tự động chuyển sang translator tiếp theo nếu bị rate limit.
"""
import logging
from typing import Optional
from src.ai.translator_base import BaseTranslator

logger = logging.getLogger(__name__)


class MultiTranslator:
    def __init__(self, translators: list[BaseTranslator]):
        self._translators = [t for t in translators if t.is_available()]
        if not self._translators:
            logger.warning("Không có translator nào khả dụng!")

    @property
    def active_provider(self) -> str:
        return self._translators[0].provider_name if self._translators else "none"

    def translate(
        self,
        text: str,
        source_lang: str = "English",
        target_lang: str = "Vietnamese",
    ) -> Optional[str]:
        for translator in self._translators:
            try:
                result = translator.translate(text, source_lang, target_lang)
                if result is not None:
                    return result
            except Exception as e:
                err_str = str(e).lower()
                if "quota" in err_str or "429" in err_str or "rate" in err_str or "overloaded" in err_str:
                    logger.warning(
                        f"[{translator.provider_name}] Rate limited — chuyển sang provider tiếp theo"
                    )
                    continue
                logger.error(f"[{translator.provider_name}] Lỗi không phải rate limit: {e}")
                return None

        logger.error("Tất cả translator đều thất bại")
        return None

    def rebuild(self, translators: list[BaseTranslator]):
        """Rebuild danh sách translator (sau khi user thay đổi settings)."""
        self._translators = [t for t in translators if t.is_available()]
