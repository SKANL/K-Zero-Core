"""Composición ligera de prompts compartidos."""
from __future__ import annotations

from pathlib import Path

from k_zero_core.core.config import SHARED_INSTRUCTIONS_FILE


def sanitize_prompt_text(text: str) -> str:
    """Elimina caracteres invisibles usados para ocultar instrucciones."""
    sanitized_chars: list[str] = []
    for char in text:
        codepoint = ord(char)
        if 0xE0000 <= codepoint <= 0xE007F:
            continue
        if 0xE000 <= codepoint <= 0xF8FF:
            continue
        sanitized_chars.append(char)
    return "".join(sanitized_chars)


def compose_system_prompt(
    base_prompt: str,
    *,
    shared_instructions_file: Path = SHARED_INSTRUCTIONS_FILE,
) -> str:
    """Combina prompt base con instrucciones compartidas opcionales."""
    base = sanitize_prompt_text(base_prompt.strip())
    if not shared_instructions_file.exists():
        return base

    shared = sanitize_prompt_text(shared_instructions_file.read_text(encoding="utf-8").strip())
    if not shared:
        return base
    if not base:
        return shared
    return f"{base}\n\n# Instrucciones compartidas\n\n{shared}"
