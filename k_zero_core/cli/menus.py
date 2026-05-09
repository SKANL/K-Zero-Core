from typing import List, Optional

from k_zero_core.storage.prompt_manager import load_all_prompts, save_prompt, delete_prompt
from k_zero_core.storage.session_manager import list_sessions, delete_session
from k_zero_core.cli.stt_menu import choose_stt_config as _choose_stt_config

# Keywords para detectar modelos de embedding dedicados vs modelos LLM genéricos
_EMBEDDING_KEYWORDS = [
    "embed", "nomic", "bge", "e5", "jina", "minilm", "mxbai", "gte", "stella"
]


def _select_from_list(prompt: str, options: List) -> int:
    """
    Solicita al usuario que elija un índice válido de una lista.

    Args:
        prompt: Texto del input a mostrar.
        options: Lista de opciones (para validar el rango).

    Returns:
        Índice 0-based de la selección.
    """
    while True:
        seleccion = input(prompt)
        try:
            indice = int(seleccion) - 1
            if 0 <= indice < len(options):
                return indice
            print("Número fuera de rango. Intenta de nuevo.")
        except ValueError:
            print("Por favor, ingresa solo números.")


def choose_provider():
    """
    Muestra el menú de proveedores de IA disponibles.
    Si solo hay uno registrado, lo selecciona automáticamente sin mostrar menú.

    Returns:
        Instancia de AIProvider lista para usar.
    """
    from k_zero_core.services.providers import list_provider_options

    instances = list_provider_options()

    if len(instances) == 1:
        # Un solo proveedor disponible — no tiene sentido mostrar menú
        return instances[0]

    print("\n=== Proveedor de IA ===")
    for i, p in enumerate(instances):
        print(f"{i + 1}. {p.get_display_name()}")

    indice = _select_from_list(
        f"\nElige un proveedor (1 - {len(instances)}): ", instances
    )
    return instances[indice]


def choose_embedding_model(provider) -> str:
    """
    Permite al usuario seleccionar el modelo de embedding disponible.

    Filtra automáticamente modelos conocidos de embedding por keywords.
    Si solo hay uno detectado, lo selecciona sin mostrar menú.
    Si no detecta ninguno, muestra todos los modelos con una advertencia.

    Args:
        provider: AIProvider instance para consultar modelos disponibles.

    Returns:
        Nombre del modelo de embedding seleccionado.
    """
    all_models = provider.get_available_models()

    embedding_models = [
        m for m in all_models
        if any(kw in m.lower() for kw in _EMBEDDING_KEYWORDS)
    ]
    models_to_show = embedding_models if embedding_models else all_models

    if not embedding_models:
        print("\n⚠️  No se detectaron modelos de embedding específicos.")
        print("   Se muestran todos los modelos. Para mejores resultados instala")
        print("   un modelo dedicado: ollama pull nomic-embed-text-v2-moe\n")

    if len(models_to_show) == 1:
        print(f"(Modelo de embedding: '{models_to_show[0]}' — seleccionado automáticamente)")
        return models_to_show[0]

    print("\n=== Modelo de Embedding ===")
    for i, model in enumerate(models_to_show):
        print(f"{i + 1}. {model}")

    indice = _select_from_list(
        f"\nElige el modelo de embedding (1 - {len(models_to_show)}): ",
        models_to_show,
    )
    return models_to_show[indice]


def choose_model(provider) -> str:
    """
    Prompt the user to select a model from the given provider.

    Args:
        provider: AIProvider instance to query for available models.
    """
    models = provider.get_available_models()
    if not models:
        print("Error: No tienes ningún modelo instalado para este proveedor.")
        print("Consulta la documentación del proveedor para instalar modelos.")
        exit(1)

    print("\n=== Modelos de IA Disponibles ===")
    for i, model in enumerate(models):
        print(f"{i + 1}. {model}")

    indice = _select_from_list(f"\nElige un modelo (1 - {len(models)}): ", models)
    return models[indice]


def choose_system_prompt(mode_default: str = "") -> str:
    """
    Menú interactivo para seleccionar, crear o eliminar System Prompts.

    Muestra el prompt por defecto del modo activo como opción 0 (solo lectura),
    permite al usuario crear prompts nuevos (opción 1), seleccionar de los
    guardados y eliminarlos con el comando 'd <numero>'.

    Args:
        mode_default: El system prompt por defecto del modo activo.
                      Se muestra como referencia visual pero no se puede editar.

    Returns:
        El contenido del prompt seleccionado o creado.
        Retorna "" si el usuario elige usar el del modo (opción 0).
    """
    while True:
        prompts = load_all_prompts()
        prompt_names = list(prompts.keys())

        print("\n=== System Prompts ===")

        # Opción 0: prompt del modo activo (solo lectura)
        if mode_default:
            preview = (mode_default[:75] + "...") if len(mode_default) > 75 else mode_default
            print(f"  0. (Usar el del modo actual: \"{preview}\")")
        else:
            print("  0. (Sin System Prompt — el modo no tiene instrucciones base)")

        print("  1. ➕ Crear nuevo prompt personalizado")

        if prompt_names:
            print("\n  — Tus Prompts Guardados —")
            for i, name in enumerate(prompt_names):
                print(f"  {i + 2}. {name}")
            print("\n  Escribe 'd <numero>' para eliminar un prompt guardado (ej. 'd 2').")

        total = len(prompt_names) + 1
        seleccion = input(f"\nElige una opción (0 - {total}): ").strip()

        # Comando de eliminación
        if seleccion.lower().startswith("d "):
            try:
                idx = int(seleccion.split(" ")[1]) - 2
                if 0 <= idx < len(prompt_names):
                    name_to_delete = prompt_names[idx]
                    delete_prompt(name_to_delete)
                    print(f"✓ Prompt '{name_to_delete}' eliminado.")
                else:
                    print("Número fuera de rango. Solo puedes eliminar prompts guardados (opciones desde el 2).")
            except (ValueError, IndexError):
                print("Formato inválido. Usa: d <numero> (ej. 'd 2')")
            continue

        try:
            idx = int(seleccion)
            if idx == 0:
                return ""
            elif idx == 1:
                name = input("Nombre del nuevo prompt: ").strip()
                if not name:
                    print("El nombre no puede estar vacío.")
                    continue
                content = input("Contenido del System Prompt:\n> ").strip()
                if not content:
                    print("El contenido no puede estar vacío.")
                    continue
                save_prompt(name, content)
                print(f"✓ Prompt '{name}' guardado.")
                return content
            elif 2 <= idx <= total:
                return prompts[prompt_names[idx - 2]]
            else:
                print("Número fuera de rango. Intenta de nuevo.")
        except ValueError:
            print("Por favor, ingresa solo números o 'd <numero>'.")


def manage_sessions() -> Optional[str]:
    """Menu to resume, delete, or start a new session. Returns session_id or None."""
    sessions = list_sessions()
    if not sessions:
        return None

    print("\n=== Sesiones Anteriores ===")
    print("0. ➕ Iniciar nueva conversación")
    for i, s in enumerate(sessions):
        provider_label = f" [{s['provider']}]" if s.get('provider') else ""
        print(f"{i + 1}. [Modelo: {s['model']}{provider_label}] Modificado: {s['updated_at']} (ID: {s['id']})")

    while True:
        print("\nOpciones:")
        print(" - Ingresa el NÚMERO para continuar una sesión o 0 para una nueva.")
        print(" - Escribe 'd <numero>' para borrar una sesión (ej. 'd 2').")
        seleccion = input("Elige una opción: ").strip().lower()

        if seleccion == '0':
            return None

        if seleccion.startswith('d '):
            try:
                indice = int(seleccion.split(' ')[1]) - 1
                if 0 <= indice < len(sessions):
                    sid = sessions[indice]['id']
                    if delete_session(sid):
                        print(f"Sesión {sid} eliminada.")
                        return manage_sessions()
                else:
                    print("Número fuera de rango.")
            except ValueError:
                print("Formato inválido.")
            continue

        try:
            indice = int(seleccion) - 1
            if 0 <= indice < len(sessions):
                return sessions[indice]['id']
            print("Número fuera de rango.")
        except ValueError:
            print("Por favor, ingresa una opción válida.")


def choose_mode() -> str:
    """
    Muestra el menú de modos leyendo dinámicamente desde MODE_REGISTRY.
    Retorna la clave del modo seleccionado.
    """
    from k_zero_core.modes import MODE_REGISTRY

    mode_entries = list(MODE_REGISTRY.items())
    instances = [cls() for _, cls in mode_entries]

    print("\n=== Modo de Interacción ===")
    for i, instance in enumerate(instances):
        print(f"{i + 1}. {instance.get_name()}")
        print(f"     {instance.get_description()}")

    indice = _select_from_list(
        f"\nElige un modo (1 - {len(mode_entries)}): ", mode_entries
    )
    return mode_entries[indice][0]


def choose_io_mode() -> tuple[str, str]:
    """Prompt the user to select the I/O strategy. Returns (input_type, output_type)."""
    options = [
        ('text', 'text'),
        ('audio', 'audio'),
        ('text', 'audio'),
        ('audio', 'text'),
    ]
    labels = [
        "Texto → Texto  (Modo Silencioso)",
        "Voz   → Voz    (Manos libres)",
        "Texto → Voz    (Escribir y Escuchar)",
        "Voz   → Texto  (Dictado)",
    ]

    print("\n=== Método de Comunicación ===")
    for i, label in enumerate(labels):
        print(f"{i + 1}. {label}")

    indice = _select_from_list(f"\nElige una opción (1 - {len(options)}): ", options)
    return options[indice]

def choose_stt_config() -> dict:
    """Prompt the user for Advanced STT configuration."""
    return _choose_stt_config(_select_from_list)
