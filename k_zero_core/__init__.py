"""
K-Zero-Core
===========

Core library for Voice, RAG, and local LLM orchestration.
This package provides the foundational architecture for building modular AI agents.
"""

__version__ = "0.1.0"

# Expose main entry points for convenience
from k_zero_core.cli.console import run

__all__ = ["__version__", "run"]
