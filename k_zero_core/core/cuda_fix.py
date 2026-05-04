# Lista global para evitar que el Garbage Collector elimine los handles en Windows
dll_handles = []

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
                
        # Forzar chequeo relativo al ejecutable actual (crucial para entornos virtuales uv/venv)
        exe_dir = os.path.dirname(sys.executable)
        venv_site = os.path.join(os.path.dirname(exe_dir), "Lib", "site-packages")
        if venv_site not in search_paths:
            search_paths.append(venv_site)

        for base_path in search_paths:
            nvidia_base = os.path.join(base_path, "nvidia")
            if os.path.isdir(nvidia_base):
                # Iterar sobre todos los módulos de nvidia (cublas, cudnn, cuda_runtime, etc.)
                for module_name in os.listdir(nvidia_base):
                    bin_path = os.path.join(nvidia_base, module_name, "bin")
                    if os.path.isdir(bin_path):
                        # 1. Inyectar en el sistema de Python
                        if hasattr(os, "add_dll_directory"):
                            dll_handles.append(os.add_dll_directory(bin_path))
                        # 2. Inyectar en el PATH nativo (Crucial para C++)
                        os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
    except Exception as e:
        print(f"Error inicializando CUDA paths: {e}")
