"""Herramientas de búsqueda web para los agentes."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any

from k_zero_core.core.source_tracking import format_sources_block


def _format_results(source: str, query: str, results: list[dict[str, str]]) -> str:
    if not results:
        return f"{source}: no se encontraron resultados para '{query}'."

    salida = [f"Resultados de {source} para '{query}':\n"]
    for i, res in enumerate(results, start=1):
        salida.append(f"{i}. {res.get('title', 'Sin título')}")
        salida.append(f"   URL: {res.get('url') or res.get('href', 'Sin URL')}")
        salida.append(f"   Resumen: {res.get('description') or res.get('body', 'Sin descripción')}\n")
    return "\n".join(salida)


def _search_ddgs(query: str, max_resultados: int = 5) -> str:
    """Busca con DuckDuckGo vía ddgs, sin API key."""
    from ddgs import DDGS

    with DDGS() as ddgs:
        if "noticia" in query.lower() or "news" in query.lower():
            raw_results = list(ddgs.news(query, max_results=max_resultados))
        else:
            raw_results = list(ddgs.text(query, max_results=max_resultados))

    results = [
        {
            "title": str(res.get("title", "Sin título")),
            "url": str(res.get("href") or res.get("url") or "Sin URL"),
            "description": str(res.get("body") or res.get("description") or "Sin descripción"),
        }
        for res in raw_results
    ]
    return _format_results("DuckDuckGo", query, results)


def _search_searxng(query: str, max_resultados: int = 5) -> str:
    """Busca en una instancia SearXNG configurada por K_ZERO_SEARXNG_URL."""
    base_url = os.getenv("K_ZERO_SEARXNG_URL", "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError("K_ZERO_SEARXNG_URL no está configurado")

    params = urllib.parse.urlencode({"q": query, "format": "json"})
    req = urllib.request.Request(f"{base_url}/search?{params}", headers={"User-Agent": "K-Zero/1.0"})
    with urllib.request.urlopen(req, timeout=12) as response:
        data = json.loads(response.read().decode("utf-8"))

    raw_results = data.get("results", [])[:max_resultados]
    results = [
        {
            "title": str(res.get("title", "Sin título")),
            "url": str(res.get("url", "Sin URL")),
            "description": str(res.get("content", "Sin descripción")),
        }
        for res in raw_results
    ]
    return _format_results("SearXNG", query, results)


def _search_brave_free(query: str, max_resultados: int = 5) -> str:
    """Busca con Brave Search free tier cuando BRAVE_SEARCH_API_KEY existe."""
    api_key = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("BRAVE_SEARCH_API_KEY no está configurado")

    params = urllib.parse.urlencode({"q": query, "count": max(1, min(max_resultados, 20))})
    req = urllib.request.Request(
        f"https://api.search.brave.com/res/v1/web/search?{params}",
        headers={"Accept": "application/json", "X-Subscription-Token": api_key},
    )
    with urllib.request.urlopen(req, timeout=12) as response:
        data = json.loads(response.read().decode("utf-8"))

    raw_results = data.get("web", {}).get("results", [])[:max_resultados]
    results = [
        {
            "title": str(res.get("title", "Sin título")),
            "url": str(res.get("url", "Sin URL")),
            "description": str(res.get("description", "Sin descripción")),
        }
        for res in raw_results
    ]
    return _format_results("Brave Search", query, results)


def _search_tavily(query: str, max_resultados: int = 5) -> str:
    """Busca con Tavily si TAVILY_API_KEY está configurado."""
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("TAVILY_API_KEY no está configurado")

    payload: dict[str, Any] = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_resultados,
        "include_answer": True,
    }
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))

    salida = [f"Resultados de Tavily para '{query}':\n"]
    if data.get("answer"):
        salida.append(f"Respuesta directa:\n{data['answer']}\n")
    for i, res in enumerate(data.get("results", []), start=1):
        salida.append(f"{i}. {res.get('title', 'Sin título')}")
        salida.append(f"   URL: {res.get('url', 'Sin URL')}")
        salida.append(f"   Contenido: {res.get('content', 'Sin contenido')}\n")
    return "\n".join(salida)


def _buscar_duckduckgo_api(query: str, _max_resultados: int = 5) -> str:
    """Fallback gratuito usando la API instantánea de DuckDuckGo."""
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("AbstractText"):
            return f"Resumen de DuckDuckGo:\n{data['AbstractText']}\nFuente: {data.get('AbstractURL')}"
        if data.get("RelatedTopics"):
            salida = ["Temas relacionados:\n"]
            for topic in data["RelatedTopics"][:5]:
                if "Text" in topic:
                    salida.append(f"- {topic['Text']}")
            return "\n".join(salida)
        return "No se encontraron respuestas directas. Intenta usar palabras clave diferentes."
    except Exception as exc:
        return f"Error al buscar '{query}' en DuckDuckGo: {exc}"


def buscar_en_internet(query: str, max_resultados: int = 5) -> str:
    """
    Busca información en internet priorizando opciones gratuitas.

    Orden: DDGS, SearXNG configurado, Brave free configurado, Tavily configurado,
    y DuckDuckGo instant answer como último fallback gratuito.
    """
    providers = [_search_ddgs]
    if os.getenv("K_ZERO_SEARXNG_URL", "").strip():
        providers.append(_search_searxng)
    if os.getenv("BRAVE_SEARCH_API_KEY", "").strip():
        providers.append(_search_brave_free)
    if os.getenv("TAVILY_API_KEY", "").strip():
        providers.append(_search_tavily)
    providers.append(_buscar_duckduckgo_api)

    errors: list[str] = []
    for provider in providers:
        try:
            return format_sources_block(provider(query, max_resultados))
        except Exception as exc:
            provider_name = "_search_duckduckgo_instant" if provider is _buscar_duckduckgo_api else getattr(provider, "__name__", provider.__class__.__name__)
            errors.append(f"{provider_name}: {exc}")

    return f"No se pudo buscar '{query}'. Fallos: " + " | ".join(errors)


def buscar_tavily(query: str, max_resultados: int = 5) -> str:
    """
    Busca información avanzada con Tavily si hay API key; si no, usa búsqueda gratis.
    """
    try:
        return format_sources_block(_search_tavily(query, max_resultados))
    except Exception:
        return buscar_en_internet(query, max_resultados)
