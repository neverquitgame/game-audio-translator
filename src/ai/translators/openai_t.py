import logging
from typing import Optional
from src.ai.translator_base import BaseTranslator

logger = logging.getLogger(__name__)


class OpenAITranslator(BaseTranslator):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._api_key = api_key
        self._model = model
        self._client = None
        self._init_client()

    @property
    def provider_name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return bool(self._api_key) and self._client is not None

    def _init_client(self):
        if not self._api_key:
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
            logger.info("OpenAI client initialized")
        except ImportError:
            logger.warning("openai package chưa được cài đặt")
        except Exception as e:
            logger.error(f"Không khởi tạo được OpenAI client: {e}")

    def translate(self, text: str, source_lang: str = "English", target_lang: str = "Vietnamese") -> Optional[str]:
        if not text or not text.strip() or not self._client:
            return None

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are a game translator. Translate {source_lang} text to {target_lang}. "
                            "Keep proper nouns and character names unchanged. Return only the translation."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                max_tokens=500,
                temperature=0.3,
            )
            result = response.choices[0].message.content.strip()
            logger.info(f"[OpenAI] Translated: '{text[:50]}' → '{result[:50]}'")
            return result
        except Exception as e:
            err_str = str(e).lower()
            logger.warning(f"[OpenAI] Translation failed: {e}")
            if "quota" in err_str or "429" in err_str or "rate" in err_str:
                raise
            return None
