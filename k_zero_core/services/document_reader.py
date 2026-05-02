"""
Servicio para extracción de texto de documentos locales (PDF y texto plano).
Sin límite de caracteres — el pipeline RAG se encarga de gestionar el contexto.
"""
from pathlib import Path
from pypdf import PdfReader

from k_zero_core.core.exceptions import StorageError


def extract_text(file_path: str) -> str:
    """
    Extrae y retorna el contenido completo de texto de un archivo PDF o de texto plano.

    No aplica ningún límite de caracteres — el RagEngine se encarga de dividir
    el texto en chunks y gestionar el contexto del modelo.

    Args:
        file_path: Ruta al archivo (PDF o cualquier archivo de texto).

    Returns:
        El texto extraído como string.

    Raises:
        StorageError: Si el archivo no existe, no se puede leer, o está vacío.
    """
    path = Path(sanitize_path(file_path))

    if not path.exists():
        raise StorageError(f"Archivo no encontrado: {path}")

    try:
        if path.suffix.lower() == ".pdf":
            reader = PdfReader(str(path))
            texto = "".join(
                (page.extract_text() or "") + "\n"
                for page in reader.pages
            )
        else:
            texto = path.read_text(encoding="utf-8")
    except StorageError:
        raise
    except Exception as e:
        raise StorageError(f"Error al leer el archivo '{path}': {e}")

    if not texto.strip():
        raise StorageError("El archivo está vacío o no se pudo extraer texto.")

    return texto


def sanitize_path(file_path: str) -> str:
    """
    Elimina comillas que los sistemas operativos agregan al copiar rutas desde el terminal.

    Args:
        file_path: Ruta posiblemente envuelta en comillas simples o dobles.

    Returns:
        La ruta limpia sin comillas.
    """
    stripped = file_path.strip()
    if (stripped.startswith('"') and stripped.endswith('"')) or \
       (stripped.startswith("'") and stripped.endswith("'")):
        return stripped[1:-1]
    return stripped
