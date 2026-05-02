import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from k_zero_core.core.config import SESSIONS_DIR
from k_zero_core.core.exceptions import StorageError


def _get_session_path(session_id: str) -> Path:
    """Genera la ruta segura al archivo JSON de una sesión."""
    safe_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_"))
    return SESSIONS_DIR / f"{safe_id}.json"


def save_session(
    session_id: str,
    messages: List[Dict[str, Any]],
    model_name: str,
    provider_name: str = "ollama",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Save the chat history, model, provider and mode-specific metadata to a JSON file.

    Args:
        session_id: Unique session identifier.
        messages: Full message history.
        model_name: Model used in this session.
        provider_name: Provider key (e.g. 'ollama').
        metadata: Optional mode-specific metadata (e.g. RAG collection_id).
    """
    data = {
        "updated_at": datetime.now().isoformat(),
        "model": model_name,
        "provider": provider_name,
        "metadata": metadata or {},
        "messages": messages,
    }
    path = _get_session_path(session_id)
    try:
        path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        raise StorageError(f"Failed to save session '{session_id}': {e}")


def load_session(session_id: str) -> Dict[str, Any]:
    """Load a specific session's data (messages, model, provider, metadata)."""
    path = _get_session_path(session_id)
    if not path.exists():
        raise StorageError(f"Session file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raise StorageError(f"Error decoding JSON from {path}")
    except Exception as e:
        raise StorageError(f"Failed to load session '{session_id}': {e}")


def list_sessions() -> List[Dict[str, Any]]:
    """List all available sessions with their metadata."""
    if not SESSIONS_DIR.exists():
        return []

    sessions = []
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            sessions.append({
                "id": path.stem,
                "updated_at": data.get("updated_at", ""),
                "model": data.get("model", "unknown"),
                "provider": data.get("provider", "ollama"),
            })
        except Exception:
            continue

    sessions.sort(key=lambda x: x["updated_at"], reverse=True)
    return sessions


def delete_session(session_id: str) -> bool:
    """Delete a session file. Returns True if deleted, False if not found."""
    path = _get_session_path(session_id)
    if path.exists():
        try:
            path.unlink()
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete session '{session_id}': {e}")
    return False
