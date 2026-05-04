"""
Herramientas para leer y extraer contenido de páginas web y Wikipedia.
"""
import json
import urllib.request
import urllib.parse
from k_zero_core.core.exceptions import WebToolError

def leer_pagina_web(url: str, max_chars: int = 15000) -> str:
    """
    Extrae el contenido de cualquier página web usando Jina Reader (gratuito) y lo devuelve en Markdown.
    
    Args:
        url: La URL completa de la página a leer (ej. https://ejemplo.com).
        max_chars: Número máximo de caracteres a devolver para no saturar al LLM.
        
    Returns:
        El contenido de la página en formato texto/Markdown.
    """
    if not url.startswith("http"):
        url = "https://" + url
        
    jina_url = f"https://r.jina.ai/{url}"
    
    try:
        # Añadir header requerido o recomendado por Jina si fuera necesario, 
        # pero funciona bien sin key para la versión gratuita.
        req = urllib.request.Request(jina_url, headers={
            'User-Agent': 'Mozilla/5.0 K-Zero-Core Bot',
            'Accept': 'text/plain'
        })
        
        with urllib.request.urlopen(req, timeout=15) as response:
            contenido = response.read().decode('utf-8')
            
        if len(contenido) > max_chars:
            return contenido[:max_chars] + f"\n\n[...contenido truncado a {max_chars} caracteres...]"
            
        return contenido
    except Exception as e:
        raise WebToolError(f"Error al extraer la página web '{url}': {str(e)}")


def extraer_wikipedia(tema: str, idioma: str = "es") -> str:
    """
    Busca y extrae el resumen de un artículo de Wikipedia.
    
    Args:
        tema: El concepto, persona o cosa que quieres buscar.
        idioma: Código de idioma (ej. 'es', 'en').
        
    Returns:
        Resumen del artículo de Wikipedia.
    """
    try:
        # 1. Buscar el título correcto
        search_url = f"https://{idioma}.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(tema)}&utf8=&format=json"
        req = urllib.request.Request(search_url, headers={'User-Agent': 'K-Zero-Core Bot'})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            search_data = json.loads(response.read().decode('utf-8'))
            
        if not search_data.get("query", {}).get("search"):
            return f"No se encontró ningún artículo de Wikipedia sobre '{tema}' en el idioma '{idioma}'."
            
        # Tomar el primer resultado
        titulo = search_data["query"]["search"][0]["title"]
        
        # 2. Extraer el resumen
        extract_url = f"https://{idioma}.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&explaintext&redirects=1&titles={urllib.parse.quote(titulo)}&format=json"
        req2 = urllib.request.Request(extract_url, headers={'User-Agent': 'K-Zero-Core Bot'})
        
        with urllib.request.urlopen(req2, timeout=10) as response2:
            extract_data = json.loads(response2.read().decode('utf-8'))
            
        pages = extract_data.get("query", {}).get("pages", {})
        for page_id, page_info in pages.items():
            if page_id != "-1":
                extract = page_info.get("extract", "No hay extracto disponible.")
                return f"Resumen de Wikipedia para '{titulo}':\n\n{extract}"
                
        return f"No se pudo extraer contenido para '{titulo}'."
    except Exception as e:
        raise WebToolError(f"Error al consultar Wikipedia: {str(e)}")
