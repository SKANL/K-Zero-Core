"""
K-Zero-Core
===========

Core library for Voice, RAG, and local LLM orchestration.
This package provides the foundational architecture for building modular AI agents.
"""

from k_zero_core.core.cuda_fix import fix_cuda_paths
fix_cuda_paths()

__version__ = "0.1.0"

def __getattr__(name: str):
    """Carga entrypoints públicos de forma perezosa para evitar imports pesados."""
    if name == "run":
        from k_zero_core.cli.console import run
        return run
    raise AttributeError(f"module 'k_zero_core' has no attribute {name!r}")

__all__ = ["__version__", "run"]
