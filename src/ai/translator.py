import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_RETRY_DELAY = 2.0


class Translator:
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self._api_key = api_key
        self._model = model
        self._client = None
        self._init_client()

    def _init_client(self):
        try:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
            logger.info("Gemini client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self._client = None

    def translate(
        self,
        text: str,
        source_lang: str = "English",
        target_lang: str = "Vietnamese",
    ) -> Optional[str]:
        if not text or not text.strip():
            return None

        if self._client is None:
            logger.error("Gemini client not initialized")
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
                logger.info(f"Translated: '{text[:50]}...' → '{result[:50]}...'")
                return result
            except Exception as e:
                logger.warning(f"Translation attempt {attempt + 1} failed: {e}")
                if attempt == 0:
                    time.sleep(_RETRY_DELAY)

        logger.error("Translation failed after retry")
        return None
