"""Translator factory — cache instance theo (name, model, api_key)."""

from src.config import Config
from src.ai.translators.litellm_t import LiteLLMTranslator
from src.ai.multi_translator import MultiTranslator

_CACHE: dict[tuple[str, str, str], LiteLLMTranslator] = {}


def _get(name: str, model: str, api_key: str = "") -> LiteLLMTranslator:
    key = (name, model, api_key)
    if key not in _CACHE:
        _CACHE[key] = LiteLLMTranslator(model=model, api_key=api_key, name=name)
    return _CACHE[key]


def build_translator() -> MultiTranslator:
    """Tạo MultiTranslator theo LLM_PRIORITY hiện tại trong Config."""
    priority = Config.LLM_PRIORITY
    all_t = {
        "gemini":    _get("gemini",    f"gemini/{Config.GEMINI_MODEL}", Config.GEMINI_API_KEY),
        "openai":    _get("openai",    "gpt-4o-mini",                   Config.OPENAI_API_KEY),
        "anthropic": _get("anthropic", "anthropic/claude-haiku-4-5",    Config.ANTHROPIC_API_KEY),
        "ollama":    _get("ollama",    "ollama/llama3.2"),
    }
    ordered = [all_t[n] for n in priority if n in all_t]
    ordered += [t for n, t in all_t.items() if n not in priority]
    return MultiTranslator(ordered)
