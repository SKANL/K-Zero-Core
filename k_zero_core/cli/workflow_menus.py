"""Menú técnico para workflows declarativos."""
from __future__ import annotations

from pathlib import Path

from k_zero_core.storage.workflow_manager import WorkflowStore
from k_zero_core.workflows.registry import list_workflows


def run_workflow_studio(store: WorkflowStore | None = None) -> None:
    """CLI simple para listar, crear desde plantilla y exportar workflows."""
    store = store or WorkflowStore()
    while True:
        print("\n=== Workflows Técnicos ===")
        print("1. Listar workflows")
        print("2. Crear workflow desde plantilla")
        print("3. Exportar workflow")
        print("4. Volver")
        choice = input("Elige una opción: ").strip()
        if choice == "1":
            for workflow in list_workflows():
                print(f"- {workflow.key}: {workflow.name} ({workflow.privacy.value}, {workflow.cost.value})")
        elif choice == "2":
            templates = list_workflows(include_user=False)
            for i, template in enumerate(templates, start=1):
                print(f"{i}. {template.key} - {template.name}")
            try:
                index = int(input("Plantilla: ").strip()) - 1
                template = templates[index]
            except (ValueError, IndexError):
                print("Plantilla inválida.")
                continue
            key = input("Clave del nuevo workflow: ").strip()
            workflow = store.create_from_template(key, template.key)
            print(f"Workflow creado: {workflow.key}")
        elif choice == "3":
            key = input("Clave del workflow: ").strip()
            destination = Path(input("Ruta destino JSON: ").strip()).expanduser()
            try:
                print(f"Exportado a: {store.export_workflow(key, destination)}")
            except Exception as exc:
                print(f"No se pudo exportar: {exc}")
        elif choice == "4":
            return
        else:
            print("Opción inválida.")
