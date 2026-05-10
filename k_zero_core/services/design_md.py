"""Capa de diseño DESIGN.md y parsing estructurado para entregables."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from k_zero_core.core.tool_safety import resolve_safe_path


SECTION_ORDER = [
    "overview",
    "colors",
    "typography",
    "layout",
    "elevation & depth",
    "shapes",
    "components",
    "do's and don'ts",
]

PROMPT_INJECTION_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "ignora las instrucciones",
    "olvida las instrucciones",
    "system prompt",
    "developer message",
)

DEFAULT_DESIGN_MD = """---
version: "1.0"
name: "K-Zero ejecutivo"
description: "Diseño sobrio para reportes técnicos, decisiones ejecutivas y entregables legibles."
colors:
  primary: "#1f5f8b"
  primaryDark: "#143d59"
  accent: "#2f855a"
  text: "#1f2933"
  mutedText: "#52606d"
  surface: "#ffffff"
  surfaceAlt: "#f5f7fa"
  border: "#d9e2ec"
typography:
  fontFamily: "Aptos"
  headingFontFamily: "Aptos Display"
  fontSize: "10.5pt"
  h1Size: "24pt"
  h2Size: "15pt"
  lineHeight: "1.35"
spacing:
  pageMargin: "0.7in"
  blockGap: "8pt"
rounded:
  small: "4px"
  medium: "6px"
components:
  table:
    headerBackground: "{colors.primary}"
    headerText: "{colors.surface}"
    borderColor: "{colors.border}"
  callout:
    backgroundColor: "{colors.surfaceAlt}"
    textColor: "{colors.text}"
---
# Overview
K-Zero ejecutivo prioriza claridad, jerarquía y lectura rápida. Los entregables deben sentirse nativos del formato, no Markdown pegado en una página.

# Colors
Usa primary para encabezados y cabeceras de tabla. Usa surfaceAlt para bloques secundarios y border para separadores discretos.

# Typography
Titulares compactos, cuerpo legible y sin adornos. Evita textos gigantes fuera de portadas o slides de sección.

# Layout
Respeta márgenes generosos, tablas con ancho completo y saltos de página cuando una sección crece.

# Components
Tablas con encabezado sólido, bullets reales y fuentes como pie o sección final.
"""


@dataclass(frozen=True)
class DesignLintFinding:
    code: str
    severity: str
    message: str


@dataclass
class DesignSystem:
    raw: str
    tokens: dict[str, Any]
    body: str
    sections: dict[str, str] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return str(self.tokens.get("name") or "K-Zero ejecutivo")

    def token(self, path: str, default: Any = "") -> Any:
        current: Any = self.tokens
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current


def parse_design_md(text: str) -> DesignSystem:
    """Parsea YAML front matter + cuerpo Markdown de un DESIGN.md."""
    frontmatter, body = _split_frontmatter(text)
    tokens = yaml.safe_load(frontmatter) if frontmatter.strip() else {}
    if not isinstance(tokens, dict):
        tokens = {}
    return DesignSystem(raw=text, tokens=tokens, body=body, sections=_extract_sections(body))


def load_design_md(path_or_text: str | None = None) -> DesignSystem:
    """Carga un DESIGN.md por ruta, texto crudo o diseño por defecto."""
    value = (path_or_text or "").strip()
    if not value or value.lower() in {"default", "k-zero ejecutivo", "k-zero-ejecutivo"}:
        return parse_design_md(DEFAULT_DESIGN_MD)
    if "\n" in value or value.startswith("---"):
        return parse_design_md(value)
    try:
        resolved = resolve_safe_path(value)
    except ValueError:
        return parse_design_md(value)
    if resolved.exists() and resolved.is_file():
        return parse_design_md(resolved.read_text(encoding="utf-8", errors="replace"))
    return parse_design_md(value)


def lint_design_md(path_o_texto: str) -> list[DesignLintFinding]:
    """Valida reglas mínimas de DESIGN.md sin depender de Node/npm."""
    raw = _read_path_or_text(path_o_texto)
    design = parse_design_md(raw)
    findings: list[DesignLintFinding] = []

    colors = design.tokens.get("colors")
    if isinstance(colors, dict) and "primary" not in colors:
        findings.append(DesignLintFinding("missing-primary", "warning", "colors.primary no está definido."))
    if "typography" not in design.tokens:
        findings.append(DesignLintFinding("missing-typography", "warning", "Falta el bloque typography."))

    for reference in _find_token_references(design.tokens):
        if design.token(reference) == "":
            findings.append(DesignLintFinding("broken-ref", "error", f"Referencia rota: {{{reference}}}."))

    duplicate = _find_duplicate_sections(design.body)
    for section in duplicate:
        findings.append(DesignLintFinding("duplicate-section", "error", f"Sección duplicada: {section}."))

    if _sections_out_of_order(design.sections):
        findings.append(DesignLintFinding("section-order", "warning", "Las secciones no siguen el orden recomendado."))

    for warning in _contrast_findings(design):
        findings.append(warning)

    lowered = raw.lower()
    if any(pattern in lowered for pattern in PROMPT_INJECTION_PATTERNS):
        findings.append(
            DesignLintFinding(
                "prompt-injection",
                "warning",
                "El DESIGN.md contiene texto con apariencia de instrucción al modelo; se trata como datos.",
            )
        )
    return findings


def limpiar_markdown_entregable(contenido_markdown: str) -> str:
    """Convierte Markdown útil a texto limpio sin marcadores crudos visibles."""
    lines: list[str] = []
    for block in parse_markdown_blocks(contenido_markdown):
        kind = block["type"]
        if kind == "heading":
            lines.append(clean_inline_text(block["text"]))
        elif kind == "paragraph":
            lines.append(clean_inline_text(block["text"]))
        elif kind in {"bullets", "numbers"}:
            lines.extend(f"- {clean_inline_text(item)}" for item in block["items"])
        elif kind == "table":
            rows = [block["headers"], *block["rows"]]
            lines.extend(" \t ".join(clean_inline_text(cell) for cell in row) for row in rows)
        elif kind == "code":
            lines.append(block["text"].strip())
        if lines and lines[-1] != "":
            lines.append("")
    return "\n".join(lines).strip()


def aplicar_diseno_entregable(
    contenido_markdown: str,
    formato: str,
    design_md: str | None = None,
) -> dict[str, Any]:
    """Devuelve contenido estructurado listo para renderizadores nativos."""
    design = load_design_md(design_md)
    blocks = parse_markdown_blocks(contenido_markdown)
    return {
        "format": formato.lower().strip(),
        "design": design,
        "blocks": blocks,
        "sources": extract_urls(contenido_markdown),
        "clean_text": limpiar_markdown_entregable(contenido_markdown),
    }


def parse_markdown_blocks(markdown: str) -> list[dict[str, Any]]:
    """Parser Markdown interno enfocado en entregables, no en Markdown completo."""
    blocks: list[dict[str, Any]] = []
    lines = markdown.replace("\r\n", "\n").split("\n")
    index = 0
    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("```"):
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            blocks.append({"type": "code", "text": "\n".join(code_lines)})
            index += 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            blocks.append({"type": "heading", "level": len(heading.group(1)), "text": clean_inline_text(heading.group(2))})
            index += 1
            continue
        if _looks_like_table_row(stripped):
            table_lines: list[str] = []
            while index < len(lines) and _looks_like_table_row(lines[index].strip()):
                table_lines.append(lines[index].strip())
                index += 1
            table = _parse_pipe_table(table_lines)
            if table:
                blocks.append(table)
            continue
        bullet = re.match(r"^\s*[-*]\s+(.+)$", line)
        if bullet:
            items: list[str] = []
            while index < len(lines):
                match = re.match(r"^\s*[-*]\s+(.+)$", lines[index])
                if not match:
                    break
                items.append(clean_inline_text(match.group(1)))
                index += 1
            blocks.append({"type": "bullets", "items": items})
            continue
        numbered = re.match(r"^\s*\d+[.)]\s+(.+)$", line)
        if numbered:
            items = []
            while index < len(lines):
                match = re.match(r"^\s*\d+[.)]\s+(.+)$", lines[index])
                if not match:
                    break
                items.append(clean_inline_text(match.group(1)))
                index += 1
            blocks.append({"type": "numbers", "items": items})
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            next_line = lines[index].strip()
            if (
                not next_line
                or re.match(r"^(#{1,6})\s+", next_line)
                or _looks_like_table_row(next_line)
                or re.match(r"^\s*[-*]\s+", lines[index])
                or re.match(r"^\s*\d+[.)]\s+", lines[index])
                or next_line.startswith("```")
            ):
                break
            paragraph_lines.append(next_line)
            index += 1
        blocks.append({"type": "paragraph", "text": clean_inline_text(" ".join(paragraph_lines))})
    return blocks


def clean_inline_text(text: str) -> str:
    """Elimina marcadores inline de Markdown preservando URLs y significado."""
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text.strip())
    return re.sub(r"\s+", " ", text).strip()


def extract_urls(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s)\]>\"']+", text)
    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        clean = url.rstrip(".,;")
        if clean not in seen:
            seen.add(clean)
            deduped.append(clean)
    return deduped


def _split_frontmatter(text: str) -> tuple[str, str]:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return "", normalized
    end = normalized.find("\n---", 4)
    if end == -1:
        return "", normalized
    frontmatter = normalized[4:end]
    body = normalized[end + len("\n---") :].lstrip("\n")
    return frontmatter, body


def _extract_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []
    for line in body.splitlines():
        match = re.match(r"^#\s+(.+)$", line.strip())
        if match:
            if current is not None:
                sections[current] = "\n".join(buffer).strip()
            current = match.group(1).strip().lower()
            buffer = []
        elif current is not None:
            buffer.append(line)
    if current is not None:
        sections[current] = "\n".join(buffer).strip()
    return sections


def _find_duplicate_sections(body: str) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for line in body.splitlines():
        match = re.match(r"^#\s+(.+)$", line.strip())
        if not match:
            continue
        title = match.group(1).strip().lower()
        if title in seen and title not in duplicates:
            duplicates.append(title)
        seen.add(title)
    return duplicates


def _sections_out_of_order(sections: dict[str, str]) -> bool:
    positions = [SECTION_ORDER.index(section) for section in sections if section in SECTION_ORDER]
    return positions != sorted(positions)


def _find_token_references(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            refs.extend(_find_token_references(child))
    elif isinstance(value, list):
        for child in value:
            refs.extend(_find_token_references(child))
    elif isinstance(value, str):
        refs.extend(re.findall(r"\{([a-zA-Z0-9_.-]+)\}", value))
    return refs


def _read_path_or_text(path_o_texto: str) -> str:
    value = path_o_texto.strip()
    if "\n" in value or value.startswith("---"):
        return path_o_texto
    try:
        resolved = resolve_safe_path(value)
    except ValueError:
        return path_o_texto
    if resolved.exists() and resolved.is_file():
        return resolved.read_text(encoding="utf-8", errors="replace")
    return path_o_texto


def _looks_like_table_row(line: str) -> bool:
    return line.startswith("|") and line.endswith("|") and line.count("|") >= 2


def _parse_pipe_table(lines: list[str]) -> dict[str, Any] | None:
    rows: list[list[str]] = []
    for line in lines:
        cells = [clean_inline_text(cell.strip()) for cell in line.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells):
            continue
        rows.append(cells)
    if not rows:
        return None
    headers = rows[0]
    body_rows = [row + [""] * (len(headers) - len(row)) for row in rows[1:]]
    return {"type": "table", "headers": headers, "rows": [row[: len(headers)] for row in body_rows]}


def _contrast_findings(design: DesignSystem) -> list[DesignLintFinding]:
    findings: list[DesignLintFinding] = []
    components = design.tokens.get("components")
    if not isinstance(components, dict):
        return findings
    for name, component in components.items():
        if not isinstance(component, dict):
            continue
        background = _resolve_color(design, component.get("backgroundColor") or component.get("headerBackground"))
        foreground = _resolve_color(design, component.get("textColor") or component.get("headerText"))
        if background and foreground and _contrast_ratio(background, foreground) < 4.5:
            findings.append(
                DesignLintFinding(
                    "contrast-ratio",
                    "warning",
                    f"Contraste bajo en component.{name}: {background} / {foreground}.",
                )
            )
    return findings


def _resolve_color(design: DesignSystem, value: Any) -> str:
    if not isinstance(value, str):
        return ""
    ref = re.fullmatch(r"\{([^}]+)\}", value.strip())
    if ref:
        value = design.token(ref.group(1), "")
    return value if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value) else ""


def _contrast_ratio(hex_a: str, hex_b: str) -> float:
    lum_a = _relative_luminance(hex_a)
    lum_b = _relative_luminance(hex_b)
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


def _relative_luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
