import time
import logging
from typing import Optional
from src.ai.translator_base import BaseTranslator

logger = logging.getLogger(__name__)
_RETRY_DELAY = 2.0


class GeminiTranslator(BaseTranslator):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self._api_key = api_key
        self._model = model
        self._client = None
        self._init_client()

    @property
    def provider_name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        return bool(self._api_key) and self._client is not None

    def _init_client(self):
        if not self._api_key:
            return
        try:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
            logger.info("Gemini client initialized")
        except Exception as e:
            logger.error(f"Không khởi tạo được Gemini client: {e}")
            self._client = None

    def translate(self, text: str, source_lang: str = "English", target_lang: str = "Vietnamese") -> Optional[str]:
        if not text or not text.strip() or not self._client:
            return None

        prompt = (
            f"Translate the following {source_lang} game text to {target_lang}. "
            f"Keep proper nouns and character names unchanged. "
            f"Return only the translation with no explanation:\n\n{text}"
        )

        for attempt in range(2):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=prompt,
                )
                result = response.text.strip()
                logger.info(f"[Gemini] Translated: '{text[:50]}' → '{result[:50]}'")
                return result
            except Exception as e:
                err_str = str(e).lower()
                logger.warning(f"[Gemini] Attempt {attempt + 1} failed: {e}")
                if "quota" in err_str or "429" in err_str or "rate" in err_str:
                    raise
                if attempt == 0:
                    time.sleep(_RETRY_DELAY)

        return None
