"""Seguimiento simple de fuentes consultadas por tools web."""
from __future__ import annotations

import re
from dataclasses import dataclass


URL_RE = re.compile(r"https?://[^\s\])>\"']+")
WEB_SOURCE_ROLES = {"investigador", "fuentes"}


@dataclass(frozen=True)
class SourceReference:
    url: str
    title: str = ""
    provider: str = ""


def extract_sources(text: str) -> list[SourceReference]:
    """Extrae URLs citables de texto devuelto por tools o especialistas."""
    seen: set[str] = set()
    sources: list[SourceReference] = []
    for match in URL_RE.finditer(text):
        url = match.group(0).rstrip(".,;")
        if url in seen:
            continue
        seen.add(url)
        sources.append(SourceReference(url=url))
    return sources


def requires_sources(roles: list[str] | tuple[str, ...] | None) -> bool:
    """Indica si una síntesis requiere fuentes por los roles usados."""
    return bool(set(roles or ()).intersection(WEB_SOURCE_ROLES))


def format_sources_block(text: str) -> str:
    """Agrega un bloque normalizado de fuentes si el texto contiene URLs."""
    if "FUENTES CONSULTADAS" in text:
        return text
    sources = extract_sources(text)
    if not sources:
        return text
    lines = ["", "FUENTES CONSULTADAS:"]
    for index, source in enumerate(sources, start=1):
        lines.append(f"{index}. {source.url}")
    return text.rstrip() + "\n" + "\n".join(lines)


def missing_sources_message() -> str:
    return (
        "FUENTES REQUERIDAS: se usó investigación web, pero los especialistas no "
        "entregaron URLs citables suficientes. Reintenta la búsqueda o pide fuentes explícitas."
    )
