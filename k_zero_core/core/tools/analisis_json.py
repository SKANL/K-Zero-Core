import json
import statistics
from typing import Union, List

def _extraer_numeros(datos: Union[dict, list, int, float, str, bool]) -> List[float]:
    """
    Recorre recursivamente una estructura de datos y extrae todos los valores numéricos.
    """
    numeros = []
    if isinstance(datos, dict):
        for valor in datos.values():
            numeros.extend(_extraer_numeros(valor))
    elif isinstance(datos, list):
        for valor in datos:
            numeros.extend(_extraer_numeros(valor))
    elif isinstance(datos, (int, float)) and not isinstance(datos, bool):
        numeros.append(float(datos))
    return numeros

def analizar_valores_json(ruta_archivo: str) -> str:
    """Extrae todos los números de un archivo JSON (sin importar su estructura) y calcula el valor máximo, mínimo y la mediana.

    Args:
        ruta_archivo: Ruta absoluta o relativa al archivo JSON a analizar.

    Returns:
        Un string con el valor máximo, la mediana y el valor mínimo encontrados, o un mensaje de error si el archivo no existe o el JSON es inválido.
    """
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            datos = json.load(f)
    except FileNotFoundError:
        return f"Error: No se encontró el archivo en la ruta '{ruta_archivo}'."
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
