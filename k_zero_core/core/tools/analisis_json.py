import json
import statistics

from k_zero_core.core.tool_safety import resolve_safe_path


def _extraer_numeros(datos: dict | list | int | float | str | bool) -> list[float]:
    """
    Recorre recursivamente una estructura de datos y extrae todos los valores numéricos.
    """
    if isinstance(datos, dict):
        return [numero for valor in datos.values() for numero in _extraer_numeros(valor)]
    if isinstance(datos, list):
        return [numero for valor in datos for numero in _extraer_numeros(valor)]
    if isinstance(datos, (int, float)) and not isinstance(datos, bool):
        return [float(datos)]
    return []

def analizar_valores_json(ruta_archivo: str) -> str:
    """Extrae todos los números de un archivo JSON (sin importar su estructura) y calcula el valor máximo, mínimo y la mediana.

    Args:
        ruta_archivo: Ruta absoluta o relativa al archivo JSON a analizar.

    Returns:
        Un string con el valor máximo, la mediana y el valor mínimo encontrados, o un mensaje de error si el archivo no existe o el JSON es inválido.
    """
    try:
        path = resolve_safe_path(ruta_archivo)
    except ValueError as e:
        return f"Error: {e}"

    try:
        datos = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return f"Error: No se encontró el archivo en la ruta '{path}'."
    except json.JSONDecodeError as e:
        return f"Error: El formato JSON en el archivo no es válido. {str(e)}"
    except Exception as e:
        return f"Error al procesar el archivo: {str(e)}"
    
    numeros = _extraer_numeros(datos)
    
    if not numeros:
        return "No se encontraron valores numéricos en el JSON proporcionado."
        
    val_max = max(numeros)
    val_min = min(numeros)
    val_mediana = statistics.median(numeros)
    
    return f"Resultados del análisis JSON:\n- Máximo: {val_max}\n- Mediana: {val_mediana}\n- Mínimo: {val_min}"
