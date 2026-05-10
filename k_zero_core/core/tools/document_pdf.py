"""Tools PDF para lectura, creación y edición por copia."""
from __future__ import annotations

import shutil
from typing import Any

from k_zero_core.core.tool_safety import resolve_safe_path
from k_zero_core.core.tools.document_common import (
    _created_result,
    _export_path,
    _first_heading,
    _table_rows,
    _theme_color,
)
from k_zero_core.services.design_md import aplicar_diseno_entregable
from k_zero_core.services.document_reader import extract_text


def analizar_pdf(path: str, max_chars: int = 12000) -> str:
    """Extrae texto básico de un PDF."""
    try:
        resolved = resolve_safe_path(path)
        text = extract_text(str(resolved))
        return f"PDF: {resolved}\nCaracteres extraídos: {len(text)}\n\n{text[:max_chars]}"
    except Exception as exc:
        return f"Error al analizar PDF: {exc}"


def crear_pdf(contenido_markdown: str, nombre_sugerido: str = "documento", design_md_path: str = "") -> str:
    """Crea un PDF en exports con párrafos, tablas y saltos nativos."""
    try:
        from xml.sax.saxutils import escape

        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        output = _export_path(nombre_sugerido, ".pdf")
        deliverable = aplicar_diseno_entregable(contenido_markdown, "pdf", design_md_path)
        blocks = deliverable["blocks"]
        primary = _theme_color(deliverable, "colors.primary", "#1f5f8b")
        border = _theme_color(deliverable, "colors.border", "#d9e2ec")
        styles = getSampleStyleSheet()
        body = ParagraphStyle(
            "KZeroBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            spaceAfter=8,
        )
        h1 = ParagraphStyle("KZeroH1", parent=styles["Title"], textColor=colors.HexColor(primary), fontSize=22, leading=27)
        h2 = ParagraphStyle("KZeroH2", parent=styles["Heading2"], textColor=colors.HexColor(primary), fontSize=14, leading=18)
        bullet = ParagraphStyle("KZeroBullet", parent=body, leftIndent=14, firstLineIndent=-8)
        story: list[Any] = []
        for block in blocks:
            kind = block["type"]
            if kind == "heading":
                story.append(Paragraph(escape(block["text"]), h1 if block.get("level") == 1 else h2))
                story.append(Spacer(1, 6))
            elif kind == "paragraph":
                story.append(Paragraph(escape(block["text"]), body))
            elif kind == "bullets":
                for item in block["items"]:
                    story.append(Paragraph(f"- {escape(item)}", bullet))
            elif kind == "numbers":
                for index, item in enumerate(block["items"], start=1):
                    story.append(Paragraph(f"{index}. {escape(item)}", bullet))
            elif kind == "table":
                rows = [
                    [Paragraph(escape(str(cell)), body) for cell in row]
                    for row in _table_rows(block)
                ]
                table = Table(rows, repeatRows=1, hAlign="LEFT")
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(primary)),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(border)),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f7fa")]),
                            ("LEFTPADDING", (0, 0), (-1, -1), 6),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ]
                    )
                )
                story.append(table)
                story.append(Spacer(1, 10))
            elif kind == "code":
                story.append(Paragraph(escape(block["text"]), styles["Code"]))
        doc = SimpleDocTemplate(
            str(output),
            pagesize=letter,
            rightMargin=0.65 * inch,
            leftMargin=0.65 * inch,
            topMargin=0.65 * inch,
            bottomMargin=0.65 * inch,
            title=_first_heading(blocks, nombre_sugerido),
        )
        doc.build(story)
        return _created_result(output, "pdf", nombre_sugerido)
    except Exception as exc:
        return f"Error al crear PDF: {exc}"


def editar_pdf_copia(path: str, instrucciones: str) -> str:
    """Crea una copia PDF y un archivo de instrucciones asociado en exports."""
    try:
        resolved = resolve_safe_path(path)
        output = _export_path(resolved.stem + "_editado", ".pdf")
        shutil.copy2(resolved, output)
        output.with_suffix(".notes.txt").write_text(instrucciones, encoding="utf-8")
        return f"Copia editada: {output}"
    except Exception as exc:
        return f"Error al editar PDF: {exc}"


def dividir_pdf_copia(path: str, paginas: str) -> str:
    """Crea un PDF con las páginas indicadas, sin modificar el original."""
    try:
        resolved = resolve_safe_path(path)
        from pypdf import PdfReader, PdfWriter

        selected = [int(part.strip()) - 1 for part in paginas.split(",") if part.strip().isdigit()]
        reader = PdfReader(str(resolved))
        writer = PdfWriter()
        for index in selected:
            if 0 <= index < len(reader.pages):
                writer.add_page(reader.pages[index])
        output = _export_path(resolved.stem + "_paginas", ".pdf")
        with output.open("wb") as file:
            writer.write(file)
        return _created_result(output, "pdf", resolved.stem)
    except Exception as exc:
        return f"Error al dividir PDF: {exc}"


def combinar_pdf_copia(paths: str, nombre_sugerido: str = "pdf_combinado") -> str:
    """Combina PDFs en una copia nueva en exports."""
    try:
        from pypdf import PdfReader, PdfWriter

        writer = PdfWriter()
        for raw_path in paths.split(";"):
            resolved = resolve_safe_path(raw_path.strip())
            reader = PdfReader(str(resolved))
            for page in reader.pages:
                writer.add_page(page)
        output = _export_path(nombre_sugerido, ".pdf")
        with output.open("wb") as file:
            writer.write(file)
        return _created_result(output, "pdf", nombre_sugerido)
    except Exception as exc:
        return f"Error al combinar PDFs: {exc}"
