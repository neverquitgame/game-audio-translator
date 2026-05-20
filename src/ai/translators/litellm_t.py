"""
LiteLLMTranslator — wrapper thống nhất cho mọi LLM (Gemini, OpenAI, Anthropic, Ollama, ...).
Thay thế các translator riêng lẻ, chỉ cần một thư viện litellm duy nhất.
"""
import time
import logging
from typing import Optional

from src.ai.translator_base import BaseTranslator

logger = logging.getLogger(__name__)
_RETRY_DELAY = 2.0


class LiteLLMTranslator(BaseTranslator):
    """
    Translator dùng LiteLLM — hỗ trợ 100+ model qua một API thống nhất.

    Định dạng model string:
      - Gemini:    "gemini/gemini-2.5-flash"
      - OpenAI:    "gpt-4o-mini"
      - Anthropic: "anthropic/claude-haiku-4-5"
      - Ollama:    "ollama/llama3.2"
    """

    def __init__(self, model: str, api_key: str = "", name: str = ""):
        self._model = model
        self._api_key = api_key
        self._name = name or model.split("/")[0]

    @property
    def provider_name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        if self._name == "ollama":
            try:
                import urllib.request
                urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
                return True
            except Exception:
                return False
        return bool(self._api_key)

    def translate(
        self,
        text: str,
        source_lang: str = "English",
        target_lang: str = "Vietnamese",
    ) -> Optional[str]:
        if not text or not text.strip():
            return None

        messages = [
            {
                "role": "system",
                "content": (
                    f"You are a game translator. Translate {source_lang} text to {target_lang}. "
                    "Keep proper nouns and character names unchanged. Return only the translation."
                ),
            },
            {"role": "user", "content": text},
        ]

        kwargs: dict = {
            "model": self._model,
            "messages": messages,
            "max_tokens": 1500,
            "temperature": 0.3,
        }
        if self._api_key:
            kwargs["api_key"] = self._api_key

        for attempt in range(2):
            try:
                import litellm
                litellm.suppress_debug_info = True
                response = litellm.completion(**kwargs)
                result = response.choices[0].message.content.strip()
                logger.info(f"[{self._name}] Translated: '{text[:50]}' → '{result[:50]}'")
                return result
            except Exception as e:
                err_str = str(e).lower()
                logger.warning(f"[{self._name}] Attempt {attempt + 1} failed: {e}")
                if "quota" in err_str or "429" in err_str or "rate" in err_str or "overloaded" in err_str:
                    raise
                if attempt == 0:
                    time.sleep(_RETRY_DELAY)

        return None
