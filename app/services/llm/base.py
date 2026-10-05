from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Return the full generated answer (blocking)."""

    @abstractmethod
    def stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        """Yield answer text incrementally as it's generated."""
