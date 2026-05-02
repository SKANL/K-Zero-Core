from k_zero_core.modes.base import BaseMode

class ClassicMode(BaseMode):
    def get_name(self) -> str:
        return "Chat Clásico"

    def get_description(self) -> str:
        return "Modo tradicional. Interactúa con el modelo."

    def get_default_system_prompt(self) -> str:
        return ""
