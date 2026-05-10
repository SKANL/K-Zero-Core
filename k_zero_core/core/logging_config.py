"""Configuración central de logging para K-Zero-Core."""
from __future__ import annotations

import logging
import os
from pathlib import Path


PACKAGE_LOGGER_NAME = "k_zero_core"
DEFAULT_LOG_LEVEL = "WARNING"
CONSOLE_LOG_FORMAT = "%(levelname)s:%(name)s:%(message)s"
FILE_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_MANAGED_HANDLER_ATTR = "_k_zero_managed_handler"


def _coerce_level(level: str | int | None) -> int:
    if isinstance(level, int):
        return level
    name = (level or DEFAULT_LOG_LEVEL).strip().upper()
    return getattr(logging, name, logging.WARNING)


def resolve_log_level(*, verbose: bool = False, level: str | int | None = None) -> int:
    """Resuelve el nivel efectivo de logs para la CLI."""
    if level is not None:
        return _coerce_level(level)
    if verbose:
        return logging.INFO
    return _coerce_level(os.getenv("K_ZERO_LOG_LEVEL"))


def _remove_managed_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        if getattr(handler, _MANAGED_HANDLER_ATTR, False):
            logger.removeHandler(handler)
            handler.close()


def _mark_managed(handler: logging.Handler) -> logging.Handler:
    setattr(handler, _MANAGED_HANDLER_ATTR, True)
    return handler


def configure_logging(
    *,
    verbose: bool = False,
    log_file: str | os.PathLike[str] | None = None,
    level: str | int | None = None,
) -> None:
    """Configura logs del paquete sin duplicar handlers entre invocaciones."""
    log_level = resolve_log_level(verbose=verbose, level=level)
    logger = logging.getLogger(PACKAGE_LOGGER_NAME)
    logger.setLevel(log_level)
    logger.propagate = False

    _remove_managed_handlers(logger)

    console_handler = _mark_managed(logging.StreamHandler())
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(CONSOLE_LOG_FORMAT))
    logger.addHandler(console_handler)

    file_path = log_file or os.getenv("K_ZERO_LOG_FILE")
    if file_path:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = _mark_managed(logging.FileHandler(path, encoding="utf-8"))
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(FILE_LOG_FORMAT))
        logger.addHandler(file_handler)
