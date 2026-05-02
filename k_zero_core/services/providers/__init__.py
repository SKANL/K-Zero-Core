"""
Registry central de proveedores de IA disponibles.

Para agregar un nuevo proveedor (ej. Groq, OpenAI, Anthropic):
  1. Crea tu clase en services/providers/mi_proveedor.py heredando de AIProvider
  2. Importa la clase aquí y agrégala al PROVIDER_REGISTRY
  3. No necesitas modificar ningún otro archivo del proyecto
"""
from typing import Type

from k_zero_core.services.providers.base_provider import AIProvider
from k_zero_core.services.providers.ollama_provider import OllamaProvider

PROVIDER_REGISTRY: dict[str, Type[AIProvider]] = {
    OllamaProvider.key: OllamaProvider,
}


def get_provider(key: str) -> AIProvider:
    """
    Retorna una instancia del proveedor registrado con la clave dada.
    Si la clave no existe, retorna el proveedor por defecto (Ollama).

    Args:
        key: Clave del proveedor (ej. 'ollama', 'groq').

    Returns:
        Instancia de AIProvider lista para usar.
    """
    ProviderClass = PROVIDER_REGISTRY.get(key, OllamaProvider)
    return ProviderClass()


__all__ = ["AIProvider", "PROVIDER_REGISTRY", "get_provider"]
