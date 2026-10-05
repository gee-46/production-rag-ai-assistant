from __future__ import annotations

import time
from collections.abc import Iterator

from app.core.errors import UpstreamProviderError
from app.core.logging import get_logger
from app.services.llm.base import LLMProvider

logger = get_logger(__name__)


def _with_retries(fn, *, max_retries: int, provider_name: str):
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - re-raised as a typed error below
            last_exc = exc
            if attempt < max_retries:
                backoff = 0.5 * (2**attempt)
                logger.warning(
                    "llm_call_retry provider=%s attempt=%s error=%s backoff=%.1fs",
                    provider_name, attempt + 1, exc, backoff,
                )
                time.sleep(backoff)
    raise UpstreamProviderError(f"{provider_name} call failed after {max_retries + 1} attempts: {last_exc}")


class GroqProvider(LLMProvider):
    """Primary provider for this deployment. OpenAI-compatible chat API, Groq-hosted inference."""

    def __init__(self, api_key: str, model: str, timeout_s: float, max_retries: int):
        from groq import Groq

        self._client = Groq(api_key=api_key, timeout=timeout_s)
        self.model = model
        self.max_retries = max_retries

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        def call():
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return resp.choices[0].message.content or ""

        return _with_retries(call, max_retries=self.max_retries, provider_name="groq")

    def stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        stream = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
        )
        for event in stream:
            delta = event.choices[0].delta.content
            if delta:
                yield delta


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, timeout_s: float, max_retries: int):
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key, timeout=timeout_s)
        self.model = model
        self.max_retries = max_retries

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        def call():
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return resp.choices[0].message.content or ""

        return _with_retries(call, max_retries=self.max_retries, provider_name="openai")

    def stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        stream = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
        )
        for event in stream:
            delta = event.choices[0].delta.content
            if delta:
                yield delta


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, timeout_s: float, max_retries: int):
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key, timeout=timeout_s)
        self.model = model
        self.max_retries = max_retries

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        def call():
            resp = self._client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return "".join(block.text for block in resp.content if block.type == "text")

        return _with_retries(call, max_retries=self.max_retries, provider_name="anthropic")

    def stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        with self._client.messages.stream(
            model=self.model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            yield from stream.text_stream


class OllamaProvider(LLMProvider):
    """Local, fully offline inference via an Ollama server."""

    def __init__(self, base_url: str, model: str, timeout_s: float, max_retries: int):
        import httpx

        self._client = httpx.Client(base_url=base_url, timeout=timeout_s)
        self.model = model
        self.max_retries = max_retries

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        def call():
            resp = self._client.post(
                "/api/chat",
                json={
                    "model": self.model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]

        return _with_retries(call, max_retries=self.max_retries, provider_name="ollama")

    def stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        import json

        with self._client.stream(
            "POST",
            "/api/chat",
            json={
                "model": self.model,
                "stream": True,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        ) as resp:
            for line in resp.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                content = chunk.get("message", {}).get("content")
                if content:
                    yield content


class FakeLLMProvider(LLMProvider):
    """
    Deterministic provider for tests: echoes back a templated answer that
    references the context it was given, with no network call. Lets the
    RAG orchestrator, citation verification, and API layer be tested
    without an API key or a live model.
    """

    def __init__(self, canned_answer: str | None = None):
        self.canned_answer = canned_answer
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return self.canned_answer or "This is a test answer based on the provided context."

    def stream(self, system_prompt: str, user_prompt: str) -> Iterator[str]:
        for word in self.generate(system_prompt, user_prompt).split(" "):
            yield word + " "
