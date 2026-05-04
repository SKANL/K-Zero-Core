from k_zero_core.modes.base import BaseMode
from k_zero_core.modes import MODE_REGISTRY

class HelloMode(BaseMode):
    """
    Un plugin simple que demuestra cómo añadir un nuevo modo sin tocar el core.
    """
    def get_name(self) -> str:
        return "Modo Saludo (Plugin)"

    def get_description(self) -> str:
        return "Un modo de prueba cargado dinámicamente que solo saluda."

    def get_default_system_prompt(self) -> str:
        return "Eres un asistente extremadamente amable que siempre empieza sus respuestas con un saludo efusivo."

# Registrar el modo en el diccionario global para que aparezca en el menú
MODE_REGISTRY["hello"] = HelloMode
