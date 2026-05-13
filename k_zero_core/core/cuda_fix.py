import logging
from contextlib import suppress


dll_handles = []
logger = logging.getLogger(__name__)

def fix_cuda_paths():
    """
    Soluciona el problema de carga de librerías CUDA en Windows para faster-whisper.
    Debe llamarse ANTES de importar faster_whisper o ctranslate2.
    """
    import os
    import sys
    
    if sys.platform != "win32":
        return
        
    try:
        import site
        search_paths = []
        with suppress(Exception):
            search_paths.extend(site.getsitepackages())
        
        if hasattr(site, "getusersitepackages"):
            with suppress(Exception):
                search_paths.append(site.getusersitepackages())
        
        for p in sys.path:
            if "site-packages" in p and p not in search_paths:
                search_paths.append(p)
                
        from pathlib import Path
        
        exe_path = Path(sys.executable)
        venv_site = str(exe_path.parent.parent / "Lib" / "site-packages")
        if venv_site not in search_paths:
            search_paths.append(venv_site)

        for base_path in search_paths:
            nvidia_base = Path(base_path) / "nvidia"
            if not nvidia_base.is_dir():
                continue
            for module_path in nvidia_base.iterdir():
                bin_path = module_path / "bin"
                if not module_path.is_dir() or not bin_path.is_dir():
                    continue
                bin_str = str(bin_path)
                if hasattr(os, "add_dll_directory"):
                    dll_handles.append(os.add_dll_directory(bin_str))
                os.environ["PATH"] = bin_str + os.pathsep + os.environ.get("PATH", "")
    except Exception as e:
        logger.warning("Error inicializando CUDA paths: %s", e)
