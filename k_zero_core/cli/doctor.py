"""Diagnóstico operativo de K-Zero-Core."""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path

from k_zero_core.core.config import DATA_DIR, PLUGINS_DIR, PROVIDERS_FILE, SESSIONS_DIR, VECTOR_STORE_DIR
from k_zero_core.core.tools import get_tool_specs
from k_zero_core.services.providers.declarative import load_declarative_provider_configs
from k_zero_core.services.providers.ollama_provider import OllamaProvider


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    ok: bool
    message: str
    critical: bool = False


@dataclass(frozen=True)
class DoctorReport:
    checks: list[DoctorCheck]

    @property
    def exit_code(self) -> int:
        return 1 if any(check.critical and not check.ok for check in self.checks) else 0


def _check_directory(name: str, path: Path, *, critical: bool = True) -> DoctorCheck:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".doctor-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return DoctorCheck(name, True, f"OK: {path}", critical)
    except Exception as e:
        return DoctorCheck(name, False, f"Error en {path}: {e}", critical)


def _check_import(module_name: str, *, critical: bool = False) -> DoctorCheck:
    try:
        importlib.import_module(module_name)
        return DoctorCheck(f"import:{module_name}", True, "OK", critical)
    except Exception as e:
        return DoctorCheck(f"import:{module_name}", False, f"No disponible: {e}", critical)


def run_doctor() -> DoctorReport:
    """Ejecuta checks no destructivos del entorno local."""
    checks = [
        _check_directory("data_dir", DATA_DIR),
        _check_directory("sessions_dir", SESSIONS_DIR),
        _check_directory("vector_store_dir", VECTOR_STORE_DIR),
        _check_directory("plugins_dir", PLUGINS_DIR, critical=False),
        _check_import("ollama", critical=True),
        _check_import("chromadb", critical=True),
        _check_import("faster_whisper", critical=False),
        _check_import("edge_tts", critical=False),
    ]

    try:
        models = OllamaProvider().get_available_models()
        checks.append(
            DoctorCheck(
                "ollama_models",
                True,
                f"Modelos disponibles: {', '.join(models) if models else '(ninguno instalado)'}",
                critical=False,
            )
        )
    except Exception as e:
        checks.append(DoctorCheck("ollama_models", False, f"No se pudo consultar Ollama: {e}", critical=True))

    try:
        providers = load_declarative_provider_configs(PROVIDERS_FILE)
        checks.append(
            DoctorCheck(
                "declarative_providers",
                True,
                f"{len(providers)} provider(s) declarativo(s) en {PROVIDERS_FILE}",
                critical=False,
            )
        )
    except Exception as e:
        checks.append(DoctorCheck("declarative_providers", False, f"providers.json inválido: {e}", critical=False))

    unavailable = [spec.name for spec in get_tool_specs() if not spec.available]
    checks.append(
        DoctorCheck(
            "tools",
            True,
            "Todas las tools disponibles" if not unavailable else f"Tools con entorno faltante: {', '.join(unavailable)}",
            critical=False,
        )
    )

    return DoctorReport(checks)


def print_doctor_report(report: DoctorReport) -> None:
    """Imprime el reporte en formato CLI."""
    print("K-Zero Doctor\n")
    for check in report.checks:
        marker = "OK" if check.ok else "FAIL"
        print(f"[{marker}] {check.name}: {check.message}")
