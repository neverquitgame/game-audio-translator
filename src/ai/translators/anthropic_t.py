import logging
from typing import Optional
from src.ai.translator_base import BaseTranslator

logger = logging.getLogger(__name__)


class AnthropicTranslator(BaseTranslator):
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5"):
        self._api_key = api_key
        self._model = model
        self._client = None
        self._init_client()

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def is_available(self) -> bool:
        return bool(self._api_key) and self._client is not None

    def _init_client(self):
        if not self._api_key:
            return
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self._api_key)
            logger.info("Anthropic client initialized")
        except ImportError:
            logger.warning("anthropic package chưa được cài đặt")
        except Exception as e:
            logger.error(f"Không khởi tạo được Anthropic client: {e}")

    def translate(self, text: str, source_lang: str = "English", target_lang: str = "Vietnamese") -> Optional[str]:
        if not text or not text.strip() or not self._client:
            return None

        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Translate the following {source_lang} game text to {target_lang}. "
                            f"Keep proper nouns and character names unchanged. "
                            f"Return only the translation with no explanation:\n\n{text}"
                        ),
                    }
                ],
            )
            result = message.content[0].text.strip()
            logger.info(f"[Anthropic] Translated: '{text[:50]}' → '{result[:50]}'")
            return result
        except Exception as e:
            err_str = str(e).lower()
            logger.warning(f"[Anthropic] Translation failed: {e}")
            if "quota" in err_str or "429" in err_str or "rate" in err_str or "overloaded" in err_str:
                raise
            return None
