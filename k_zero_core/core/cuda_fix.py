# Lista global para evitar que el Garbage Collector elimine los handles en Windows
import logging


dll_handles = []
logger = logging.getLogger(__name__)

def fix_cuda_paths():
    """
    Soluciona el problema de carga de librerías CUDA en Windows para faster-whisper.
    Debe llamarse ANTES de importar faster_whisper o ctranslate2.
    """
    import os
    import sys
    global dll_handles
    
    if sys.platform != "win32":
        return
        
    try:
        import site
        # Recolectar posibles rutas de site-packages
        search_paths = []
        try:
            search_paths.extend(site.getsitepackages())
        except Exception:
            pass
        
        if hasattr(site, "getusersitepackages"):
            try:
                search_paths.append(site.getusersitepackages())
            except Exception:
                pass
        
        # Añadir rutas del sys.path que parezcan site-packages
        for p in sys.path:
            if "site-packages" in p and p not in search_paths:
                search_paths.append(p)
                
        from pathlib import Path
        
        # Forzar chequeo relativo al ejecutable actual (crucial para entornos virtuales uv/venv)
        exe_path = Path(sys.executable)
        venv_site = str(exe_path.parent.parent / "Lib" / "site-packages")
        if venv_site not in search_paths:
            search_paths.append(venv_site)

        for base_path in search_paths:
            nvidia_base = Path(base_path) / "nvidia"
            if nvidia_base.is_dir():
                # Iterar sobre todos los módulos de nvidia (cublas, cudnn, cuda_runtime, etc.)
                for module_path in nvidia_base.iterdir():
                    if module_path.is_dir():
                        bin_path = module_path / "bin"
                        if bin_path.is_dir():
                            bin_str = str(bin_path)
                            # 1. Inyectar en el sistema de Python
                            if hasattr(os, "add_dll_directory"):
                                dll_handles.append(os.add_dll_directory(bin_str))
                            # 2. Inyectar en el PATH nativo (Crucial para C++)
                            os.environ["PATH"] = bin_str + os.pathsep + os.environ.get("PATH", "")
    except Exception as e:
        logger.warning("Error inicializando CUDA paths: %s", e)
