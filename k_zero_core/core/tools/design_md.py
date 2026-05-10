"""Tools generales para DESIGN.md y preparación visual de entregables."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from k_zero_core.core.config import DATA_DIR
from k_zero_core.services.design_md import (
    DEFAULT_DESIGN_MD,
    aplicar_diseno_entregable,
    limpiar_markdown_entregable as limpiar_markdown_service,
    lint_design_md,
)


EXPORTS_DIR = DATA_DIR / "exports"


def validar_design_md(path_o_texto: str) -> str:
    """Valida un DESIGN.md por ruta o texto y devuelve hallazgos legibles."""
    findings = lint_design_md(path_o_texto)
    if not findings:
        return "DESIGN.md válido: no se detectaron hallazgos críticos."
    lines = ["Hallazgos DESIGN.md:"]
    for finding in findings:
        lines.append(f"- [{finding.severity}] {finding.code}: {finding.message}")
    return "\n".join(lines)


def crear_design_md(nombre: str, estilo: str = "k-zero-ejecutivo") -> str:
    """Crea un DESIGN.md base en exports para personalizar entregables."""
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    clean = "".join(char for char in nombre if char.isalnum() or char in ("-", "_")).strip() or "design"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = EXPORTS_DIR / f"{clean}_{timestamp}.DESIGN.md"
    content = DEFAULT_DESIGN_MD
    if estilo.lower().strip() not in {"k-zero-ejecutivo", "default"}:
        content += f"\n\n<!-- Estilo solicitado no disponible todavía: {estilo}. Se usó K-Zero ejecutivo. -->\n"
    output.write_text(content, encoding="utf-8")
    return f"Archivo creado: {output}"


def previsualizar_estilo_entregable(contenido_markdown: str, formato: str, design_md: str = "default") -> str:
    """Resume cómo se estructurará un entregable antes de renderizarlo."""
    deliverable = aplicar_diseno_entregable(contenido_markdown, formato, design_md)
    counts: dict[str, int] = {}
    for block in deliverable["blocks"]:
        counts[block["type"]] = counts.get(block["type"], 0) + 1
    lines = [
        f"Diseño: {deliverable['design'].name}",
        f"Formato destino: {deliverable['format']}",
        "Bloques detectados: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())),
    ]
    if deliverable["sources"]:
        lines.append("Fuentes detectadas:")
        lines.extend(f"- {url}" for url in deliverable["sources"])
    return "\n".join(lines)


def limpiar_markdown_entregable(contenido_markdown: str) -> str:
    """Devuelve una versión limpia del Markdown para entregables nativos."""
    return limpiar_markdown_service(contenido_markdown)
