"""
Herramientas de búsqueda web para los agentes.
"""
import os
import json
import urllib.request
import urllib.parse
from typing import List

from k_zero_core.core.exceptions import WebToolError


def buscar_en_internet(query: str, max_resultados: int = 5) -> str:
    """
    Busca información en internet usando DuckDuckGo (gratuito) y devuelve un resumen.
    
    Args:
        query: Lo que quieres buscar en internet.
        max_resultados: Cantidad de resultados a devolver (por defecto 5).
        
    Returns:
        Un texto con los resultados de la búsqueda.
    """
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            # Si la palabra noticia o news está en la query, usa búsqueda de noticias
            if "noticia" in query.lower() or "news" in query.lower():
                resultados = list(ddgs.news(query, max_results=max_resultados))
            else:
                resultados = list(ddgs.text(query, max_results=max_resultados))
            
        if not resultados:
            return "No se encontraron resultados para la búsqueda."
            
        salida = [f"Resultados de búsqueda para '{query}':\n"]
        for i, res in enumerate(resultados):
            salida.append(f"{i+1}. {res.get('title', 'Sin título')}")
            salida.append(f"   URL: {res.get('href', 'Sin URL')}")
            salida.append(f"   Resumen: {res.get('body', 'Sin descripción')}\n")
            
        return "\n".join(salida)
    except ImportError:
        return "Error: La librería 'ddgs' no está instalada. Por favor añádela a requirements.txt"
    except Exception as e:
        # Fallback a DuckDuckGo Instant Answer si falla la librería
        return _buscar_duckduckgo_api(query)


def _buscar_duckduckgo_api(query: str) -> str:
    """Fallback usando la API instantánea de DuckDuckGo."""
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        if data.get("AbstractText"):
            return f"Resumen de DuckDuckGo:\n{data['AbstractText']}\nFuente: {data.get('AbstractURL')}"
        elif data.get("RelatedTopics"):
            salida = ["Temas relacionados:\n"]
            for i, topic in enumerate(data["RelatedTopics"][:5]):
                if "Text" in topic:
                    salida.append(f"- {topic['Text']}")
            return "\n".join(salida)
        return "No se encontraron respuestas directas. Intenta usar palabras clave diferentes."
    except Exception as e:
        raise WebToolError(f"Fallo al contactar el buscador web: {str(e)}")


def buscar_tavily(query: str, max_resultados: int = 5) -> str:
    """
    Busca información avanzada en internet usando Tavily Search API.
    Si la API key no está configurada, hace un fallback automático a DuckDuckGo.
    
    Args:
        query: Lo que quieres buscar en internet.
        max_resultados: Cantidad de resultados a devolver.
        
    Returns:
        Resultados de búsqueda estructurados.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return buscar_en_internet(query, max_resultados)
        
    try:
        url = "https://api.tavily.com/search"
        data = {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": max_resultados,
            "include_answer": True
        }
        
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            
        salida = [f"Resultados de Tavily para '{query}':\n"]
        if result.get("answer"):
            salida.append(f"Respuesta directa:\n{result['answer']}\n")
            
        for i, res in enumerate(result.get("results", [])):
            salida.append(f"{i+1}. {res.get('title')}")
            salida.append(f"   URL: {res.get('url')}")
            salida.append(f"   Contenido: {res.get('content')}\n")
            
        return "\n".join(salida)
    except Exception as e:
        print(f"Aviso: Falló Tavily ({e}), haciendo fallback a DuckDuckGo...")
        return buscar_en_internet(query, max_resultados)
