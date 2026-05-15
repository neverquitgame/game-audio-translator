import logging
from typing import Optional
from src.ai.translator_base import BaseTranslator

logger = logging.getLogger(__name__)


class OllamaTranslator(BaseTranslator):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self._base_url = base_url.rstrip("/")
        self._model = model

    @property
    def provider_name(self) -> str:
        return "ollama"

    def is_available(self) -> bool:
        try:
            import urllib.request
            urllib.request.urlopen(f"{self._base_url}/api/tags", timeout=2)
            return True
        except Exception:
            return False

    def translate(self, text: str, source_lang: str = "English", target_lang: str = "Vietnamese") -> Optional[str]:
        if not text or not text.strip():
            return None

        prompt = (
            f"Translate the following {source_lang} game text to {target_lang}. "
            f"Keep proper nouns and character names unchanged. "
            f"Return only the translation with no explanation:\n\n{text}"
        )

        try:
            import json
            import urllib.request

            payload = json.dumps({
                "model": self._model,
                "prompt": prompt,
                "stream": False,
            }).encode()

            req = urllib.request.Request(
                f"{self._base_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                result = data.get("response", "").strip()
                logger.info(f"[Ollama] Translated: '{text[:50]}' → '{result[:50]}'")
                return result or None
        except Exception as e:
            logger.warning(f"[Ollama] Translation failed: {e}")
            return None
