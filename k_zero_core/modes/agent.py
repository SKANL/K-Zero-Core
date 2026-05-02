from k_zero_core.modes.base import BaseMode

class AgentMode(BaseMode):
    def get_name(self) -> str:
        return "Agente Asistente (Acceso a PC local)"

    def get_description(self) -> str:
        return "Un asistente con acceso a herramientas de tu PC."

    def get_default_system_prompt(self) -> str:
        return (
            "Eres un asistente virtual avanzado con acceso a herramientas externas. "
            "Si el usuario pide información sobre la hora actual, fecha, o hacer un cálculo matemático, "
            "utiliza la herramienta correspondiente en lugar de adivinar. "
            "Responde de manera concisa y útil."
        )
