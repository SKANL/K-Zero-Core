"""
K-Zero-Core
===========

Core library for Voice, RAG, and local LLM orchestration.
This package provides the foundational architecture for building modular AI agents.
"""

from k_zero_core.core.cuda_fix import fix_cuda_paths
fix_cuda_paths()

__version__ = "0.1.0"

# Expose main entry points for convenience
from k_zero_core.cli.console import run

__all__ = ["__version__", "run"]
