import argparse
from k_zero_core.cli.console import run

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="K-Zero-Core CLI")
    parser.add_argument("--cleanup", action="store_true", help="Limpia colecciones huérfanas en la base de datos RAG")
    args = parser.parse_args()

    if args.cleanup:
        from k_zero_core.storage.session_manager import get_all_active_collections
        from k_zero_core.services.vector_store import VectorStore
        print("🔍 Buscando colecciones huérfanas en ChromaDB...")
        active = get_all_active_collections()
        store = VectorStore()
        deleted = store.cleanup_orphan_collections(active)
        print(f"✅ Limpieza completada. Se eliminaron {deleted} colecciones huérfanas.")
    else:
        run()