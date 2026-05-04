"""
Registry central de modos de interacción disponibles en la aplicación.

Para agregar un nuevo modo:
  1. Crea tu clase en un nuevo archivo dentro de `k_zero_core/modes/`
  2. Importa la clase aquí y agrégala al diccionario MODE_REGISTRY.

No necesitas modificar ningún otro archivo (console.py y menus.py se actualizan solos).
"""
from typing import Type

from k_zero_core.modes.base import BaseMode
from k_zero_core.modes.classic import ClassicMode
from k_zero_core.modes.companion import VoiceCompanionMode
from k_zero_core.modes.dungeon_master import DungeonMasterMode
from k_zero_core.modes.agent import AgentMode
from k_zero_core.modes.brain_dump import BrainDumpMode
from k_zero_core.modes.rag import DocumentRAGMode
from k_zero_core.modes.transcription_only import TranscriptionOnlyMode
from k_zero_core.modes.director import DirectorMode

# El orden de inserción determina el orden en el menú.
MODE_REGISTRY: dict[str, Type[BaseMode]] = {
    "classic":        ClassicMode,
    "transcription":  TranscriptionOnlyMode,
    "companion":      VoiceCompanionMode,
    "dungeon_master": DungeonMasterMode,
    "agent":          AgentMode,
    "director":       DirectorMode,
    "brain_dump":     BrainDumpMode,
    "rag":            DocumentRAGMode,
}

__all__ = ["MODE_REGISTRY", "BaseMode"]
