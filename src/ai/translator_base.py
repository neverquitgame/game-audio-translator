from abc import ABC, abstractmethod
from typing import Optional


class BaseTranslator(ABC):
    @abstractmethod
    def translate(
        self,
        text: str,
        source_lang: str = "English",
        target_lang: str = "Vietnamese",
    ) -> Optional[str]: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    def is_available(self) -> bool:
        """Trả về True nếu translator có đủ config để chạy."""
        return True
