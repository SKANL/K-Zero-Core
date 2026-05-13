import json

from k_zero_core.core.config import PROMPTS_FILE
from k_zero_core.core.exceptions import StorageError


def load_all_prompts() -> dict[str, str]:
    """Carga todos los prompts personalizados del usuario desde el archivo JSON local."""
    if not PROMPTS_FILE.exists():
        return {}
    try:
        return json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise StorageError(f"Error decodificando JSON desde {PROMPTS_FILE}")
    except Exception as e:
        raise StorageError(f"Error al leer prompts: {e}")


def save_prompt(name: str, content: str) -> None:
    """
    Guarda un nuevo prompt personalizado o sobreescribe uno existente.

    Args:
        name: Nombre identificador del prompt.
        content: Contenido del system prompt.
    """
    prompts = load_all_prompts()
    prompts[name] = content
    try:
        PROMPTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        PROMPTS_FILE.write_text(json.dumps(prompts, indent=4, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        raise StorageError(f"Error al guardar el prompt '{name}': {e}")


def delete_prompt(name: str) -> bool:
    """
    Elimina un prompt personalizado por nombre.

    Args:
        name: Nombre identificador del prompt a eliminar.

    Returns:
        True si fue eliminado, False si no existía.
    """
    prompts = load_all_prompts()
    if name not in prompts:
        return False
    del prompts[name]
    try:
        PROMPTS_FILE.write_text(json.dumps(prompts, indent=4, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception as e:
        raise StorageError(f"Error al eliminar el prompt '{name}': {e}")


def get_prompt(name: str) -> str | None:
    """
    Recupera un prompt específico por nombre.

    Args:
        name: Nombre identificador del prompt.

    Returns:
        Contenido del prompt o None si no existe.
    """
    return load_all_prompts().get(name)
