import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env (si existe)
load_dotenv()

# Directorio base de datos:
#   1. Si el usuario define K_ZERO_DATA_DIR (variable de entorno), se usa esa ruta.
#   2. Si no, se usa ~/.k_zero (directorio oculto en el home del usuario).
#      Esto garantiza que la librería funcione "out-of-the-box" sin depender
#      de la carpeta local del proyecto donde se instaló.
_env_data_dir = os.getenv("K_ZERO_DATA_DIR")
DATA_DIR = Path(_env_data_dir) if _env_data_dir else Path.home() / ".k_zero"

# Subdirectorios y archivos de datos
PROMPTS_FILE = DATA_DIR / "prompts.json"
PROVIDERS_FILE = DATA_DIR / "providers.json"
SHARED_INSTRUCTIONS_FILE = DATA_DIR / "shared_instructions.md"
SESSIONS_DIR = DATA_DIR / "sessions"
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
PLUGINS_DIR = DATA_DIR / "plugins"

# Crear directorios en el primer uso
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
