import argparse
from k_zero_core.cli.console import run
from k_zero_core.core.logging_config import configure_logging

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="K-Zero-Core CLI")
    parser.add_argument("--cleanup", action="store_true", help="Limpia colecciones huérfanas en la base de datos RAG")
    parser.add_argument("--doctor", action="store_true", help="Ejecuta diagnósticos no destructivos del entorno")
    parser.add_argument("--verbose", action="store_true", help="Muestra logs informativos de diagnóstico")
    parser.add_argument("--log-file", help="Escribe logs técnicos en el archivo indicado")
    args = parser.parse_args()
    configure_logging(verbose=args.verbose, log_file=args.log_file)

    if args.doctor:
        from k_zero_core.cli.doctor import print_doctor_report, run_doctor

        report = run_doctor()
        print_doctor_report(report)
        raise SystemExit(report.exit_code)
    elif args.cleanup:
        from k_zero_core.storage.session_manager import get_all_active_collections
        from k_zero_core.services.vector_store import VectorStore
        print("🔍 Buscando colecciones huérfanas en ChromaDB...")
        active = get_all_active_collections()
        store = VectorStore()
        deleted = store.cleanup_orphan_collections(active)
        print(f"✅ Limpieza completada. Se eliminaron {deleted} colecciones huérfanas.")
    else:
        run()
