"""Providers declarativos OpenAI-compatible."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from k_zero_core.core.config import PROVIDERS_FILE
from k_zero_core.core.exceptions import OllamaConnectionError
from k_zero_core.services.providers.base_provider import AIProvider


@dataclass(frozen=True)
class DeclarativeProviderConfig:
    key: str
    display_name: str
    base_url: str
    api_key_env: str = ""
    models: tuple[str, ...] = ()
    default_model: str = ""
    supports_streaming: bool = True

    @property
    def chat_completions_url(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"


def _coerce_provider_config(raw: Dict[str, Any]) -> DeclarativeProviderConfig | None:
    key = str(raw.get("key", "")).strip()
    display_name = str(raw.get("display_name", key)).strip()
    base_url = str(raw.get("base_url", "")).strip()
    if not key or not display_name or not base_url:
        return None
    models = tuple(str(model).strip() for model in raw.get("models", []) if str(model).strip())
    default_model = str(raw.get("default_model", "")).strip() or (models[0] if models else "")
    return DeclarativeProviderConfig(
        key=key,
        display_name=display_name,
        base_url=base_url,
        api_key_env=str(raw.get("api_key_env", "")).strip(),
        models=models,
        default_model=default_model,
        supports_streaming=bool(raw.get("supports_streaming", True)),
    )


def load_declarative_provider_configs(path: Path = PROVIDERS_FILE) -> list[DeclarativeProviderConfig]:
    """Carga providers declarativos desde providers.json."""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    providers = data.get("providers", []) if isinstance(data, dict) else []
    configs: list[DeclarativeProviderConfig] = []
    for raw in providers:
        if isinstance(raw, dict):
            config = _coerce_provider_config(raw)
            if config:
                configs.append(config)
    return configs


def parse_sse_chat_chunks(chunks: Iterable[bytes]) -> Generator[str, None, None]:
    """Parsea chunks SSE de OpenAI-compatible chat completions."""
    for chunk in chunks:
        text = chunk.decode("utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue
            for choice in data.get("choices", []):
                content = choice.get("delta", {}).get("content")
                if content:
                    yield str(content)


class DeclarativeOpenAIProvider(AIProvider):
    """Provider OpenAI-compatible configurado por JSON."""

    def __init__(self, config: DeclarativeProviderConfig):
        self.config = config
        self.key = config.key

    def get_display_name(self) -> str:
        return self.config.display_name

    def get_available_models(self) -> List[str]:
        return list(self.config.models or ((self.config.default_model,) if self.config.default_model else ()))

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key_env:
            api_key = os.getenv(self.config.api_key_env)
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List] = None,
    ) -> Generator[str, None, None]:
        if tools:
            raise OllamaConnectionError("Los providers declarativos v1 no soportan tool calling.")
        payload = {
            "model": model or self.config.default_model,
            "messages": messages,
            "stream": self.config.supports_streaming,
        }
        request = urllib.request.Request(
            self.config.chat_completions_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                if self.config.supports_streaming:
                    yield from parse_sse_chat_chunks(response)
                    return
                data = json.loads(response.read().decode("utf-8"))
                for choice in data.get("choices", []):
                    content = choice.get("message", {}).get("content")
                    if content:
                        yield str(content)
        except urllib.error.URLError as e:
            raise OllamaConnectionError(f"Error conectando con provider '{self.key}': {e}") from e


def get_declarative_provider(key: str) -> DeclarativeOpenAIProvider | None:
    for config in load_declarative_provider_configs():
        if config.key == key:
            return DeclarativeOpenAIProvider(config)
    return None
