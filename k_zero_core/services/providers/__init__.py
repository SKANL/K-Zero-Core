"""
Registry central de proveedores de IA disponibles.

Para agregar un nuevo proveedor (ej. Groq, OpenAI, Anthropic):
  1. Crea tu clase en services/providers/mi_proveedor.py heredando de AIProvider
  2. Importa la clase aquí y agrégala al PROVIDER_REGISTRY
  3. No necesitas modificar ningún otro archivo del proyecto
"""
from typing import Type

from k_zero_core.services.providers.base_provider import AIProvider
from k_zero_core.services.providers.declarative import (
    DeclarativeOpenAIProvider,
    get_declarative_provider,
    load_declarative_provider_configs,
)
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
    ProviderClass = PROVIDER_REGISTRY.get(key)
    if ProviderClass:
        return ProviderClass()

    declarative = get_declarative_provider(key)
    if declarative:
        return declarative

    return OllamaProvider()


def list_provider_options() -> list[AIProvider]:
    """Lista providers built-in y declarativos configurados."""
    providers: list[AIProvider] = [provider_class() for provider_class in PROVIDER_REGISTRY.values()]
    providers.extend(DeclarativeOpenAIProvider(config) for config in load_declarative_provider_configs())
    return providers


__all__ = ["AIProvider", "PROVIDER_REGISTRY", "get_provider", "list_provider_options"]
