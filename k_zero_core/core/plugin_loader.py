import importlib.util
import os
import sys
import traceback
import logging

from k_zero_core.core.config import PLUGINS_DIR

logger = logging.getLogger(__name__)

def load_external_plugins() -> None:
    """
    Busca e importa todos los archivos .py en el directorio PLUGINS_DIR.
    Esto permite que los plugins se inyecten a sí mismos en MODE_REGISTRY o
    PROVIDER_REGISTRY sin necesidad de modificar el código fuente de k_zero_core.
    """
    if not PLUGINS_DIR.exists() or not PLUGINS_DIR.is_dir():
        return

    for filename in os.listdir(PLUGINS_DIR):
        if filename.endswith(".py") and not filename.startswith("_"):
            module_name = f"k_zero_plugins.{filename[:-3]}"
            file_path = PLUGINS_DIR / filename
            
            try:
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    # Añadir al sys.modules es buena práctica para evitar recargas o imports cruzados fallidos
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)
                    logger.info("Plugin cargado exitosamente: %s", filename)
            except Exception as e:
                logger.error("Error al cargar el plugin %s: %s", filename, e)
                print(f"⚠️  Error cargando plugin '{filename}': {e}")
                # traceback.print_exc()
