"""
Herramientas de sistema de archivos: leer archivos y listar directorios.
"""
from pathlib import Path


def leer_archivo(ruta: str, max_chars: int = 8000) -> str:
    """
    Lee y retorna el contenido de un archivo de texto del sistema local.

    Útil para leer código fuente, archivos de configuración, logs, documentos,
    o cualquier archivo de texto plano.

    Args:
        ruta: Ruta absoluta o relativa al archivo a leer.
        max_chars: Número máximo de caracteres a retornar (por defecto 8000).
                   Usa 0 para sin límite (puede ser muy largo).

    Returns:
        El contenido del archivo como texto, o un mensaje de error si no se pudo leer.
    """
    path = Path(ruta).expanduser()

    if not path.exists():
        return f"Error: El archivo '{path}' no existe."

    if path.is_dir():
        return f"Error: '{path}' es un directorio, no un archivo. Usa listar_directorio()."

    # Limitar a archivos de texto — rechazar binarios muy grandes
    if path.stat().st_size > 10 * 1024 * 1024:  # 10 MB
        return f"Error: El archivo es demasiado grande ({path.stat().st_size // 1024} KB). Usa un editor externo."

    try:
        contenido = path.read_text(encoding="utf-8", errors="replace")
    except PermissionError:
        return f"Error: Sin permiso para leer '{path}'."
    except Exception as e:
        return f"Error al leer '{path}': {e}"

    if max_chars and max_chars > 0 and len(contenido) > max_chars:
        truncado = contenido[:max_chars]
        return f"{truncado}\n\n[... archivo truncado a {max_chars:,} caracteres. Total: {len(contenido):,} chars]"

    return contenido if contenido else "(El archivo está vacío)"


def listar_directorio(ruta: str = ".") -> str:
    """
    Lista el contenido de un directorio del sistema local.

    Muestra archivos y carpetas con sus tamaños y fechas de modificación.

    Args:
        ruta: Ruta al directorio a listar. Por defecto usa el directorio actual (".").

    Returns:
        Lista formateada con archivos y carpetas, o un mensaje de error.
    """
    path = Path(ruta).expanduser()

    if not path.exists():
        return f"Error: El directorio '{path}' no existe."

    if not path.is_dir():
        return f"Error: '{path}' es un archivo, no un directorio. Usa leer_archivo()."

    try:
        entries = sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
    except PermissionError:
        return f"Error: Sin permiso para listar '{path}'."
    except Exception as e:
        return f"Error al listar '{path}': {e}"

    if not entries:
        return f"El directorio '{path}' está vacío."

    lineas = [f"📁 Contenido de: {path.resolve()}\n"]
    dirs_count = 0
    files_count = 0

    for entry in entries:
        try:
            stat = entry.stat()
            import datetime
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

            if entry.is_dir():
                lineas.append(f"  📂 {entry.name}/  ({mtime})")
                dirs_count += 1
            else:
                size = stat.st_size
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                lineas.append(f"  📄 {entry.name}  [{size_str}]  ({mtime})")
                files_count += 1
        except Exception:
            lineas.append(f"  ⚠️  {entry.name}  (sin acceso)")

    lineas.append(f"\n{dirs_count} carpeta(s), {files_count} archivo(s)")
    return "\n".join(lineas)
