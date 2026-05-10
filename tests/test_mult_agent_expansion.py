import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class SystemToolExpansionTests(unittest.TestCase):
    def test_informacion_sistema_remains_backward_compatible(self):
        from k_zero_core.core.tools.sistema import informacion_sistema

        report = informacion_sistema()

        self.assertIn("Información del Sistema", report)
        self.assertIn("Sistema Operativo", report)

    def test_informacion_sistema_supports_detailed_sections(self):
        from k_zero_core.core.tools.sistema import informacion_sistema

        self.assertIn("Memoria RAM", informacion_sistema(detalle="hardware"))
        self.assertIn("Ollama", informacion_sistema(detalle="ollama"))
        self.assertIn("Disco principal", informacion_sistema(detalle="disco"))
        self.assertIn("Memoria RAM", informacion_sistema(detalle="todo"))


class DocumentToolTests(unittest.TestCase):
    def test_text_file_tools_read_metadata_and_project_summary(self):
        from k_zero_core.core.tools.local_files import (
            buscar_archivos_locales,
            inspeccionar_proyecto,
            leer_metadatos_archivo,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            (root / "app.py").write_text("print('hola')\n", encoding="utf-8")

            metadata = leer_metadatos_archivo(str(root / "app.py"))
            matches = buscar_archivos_locales("app", str(root), ".py")
            summary = inspeccionar_proyecto(str(root))

        self.assertIn("app.py", metadata)
        self.assertIn("app.py", matches)
        self.assertIn("pyproject.toml", summary)

    def test_document_tools_create_and_edit_copies_in_exports(self):
        from k_zero_core.core.tools.documents import crear_docx, editar_docx_copia

        with tempfile.TemporaryDirectory() as tmpdir:
            original = Path(tmpdir) / "original.docx"
            with patch("k_zero_core.core.tools.documents.EXPORTS_DIR", Path(tmpdir) / "exports"):
                created = crear_docx("# Titulo\n\nContenido", "original")
                original_path = Path(created.split("Archivo creado: ", 1)[1].splitlines()[0])
                original_path.replace(original)

                edited = editar_docx_copia(str(original), "Agregar nota")

            edited_path = Path(edited.split("Copia editada: ", 1)[1].strip())

        self.assertNotEqual(original, edited_path)
        self.assertTrue(edited_path.name.endswith(".docx"))

    def test_xlsx_and_pptx_creation_tools_return_export_paths(self):
        from k_zero_core.core.tools.documents import crear_pptx, crear_xlsx

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("k_zero_core.core.tools.documents.EXPORTS_DIR", Path(tmpdir) / "exports"):
                xlsx_result = crear_xlsx(json.dumps([{"a": 1, "b": 2}]), "datos")
                pptx_result = crear_pptx("# Portada\n\n## Seccion\n\nContenido", "deck")

        self.assertIn(".xlsx", xlsx_result)
        self.assertIn(".pptx", pptx_result)


class SourceTrackingTests(unittest.TestCase):
    def test_source_tracking_extracts_urls_and_detects_missing_sources(self):
        from k_zero_core.core.source_tracking import extract_sources, requires_sources

        text = "Resultado\nURL: https://example.com/a\nFuente: https://example.org/b"

        self.assertEqual(len(extract_sources(text)), 2)
        self.assertTrue(requires_sources(["investigador"]))
        self.assertFalse(requires_sources(["analista"]))

    def test_web_search_formats_sources_consistently(self):
        from k_zero_core.core.tools import web_search

        with patch.object(
            web_search,
            "_search_ddgs",
            return_value="Resultados\n1. Demo\n   URL: https://example.com\n   Resumen: ok",
        ):
            result = web_search.buscar_en_internet("demo")

        self.assertIn("FUENTES CONSULTADAS", result)
        self.assertIn("https://example.com", result)


class DirectorExpansionTests(unittest.TestCase):
    def test_parse_roles_supports_new_specialists_in_stable_order(self):
        from k_zero_core.modes.director_helpers import parse_roles

        roles = parse_roles("documentalista, datos, seguridad, verificador, fuentes")

        self.assertEqual(roles, ["fuentes", "documentalista", "datos", "seguridad", "verificador"])

    def test_director_context_blocks_web_without_sources(self):
        from k_zero_core.modes.director_helpers import build_director_context

        context = build_director_context(["DATOS DEL INVESTIGADOR:\nsin urls"], roles=["investigador"])

        self.assertIn("FUENTES REQUERIDAS", context)

    def test_director_context_tells_final_writer_to_report_created_paths(self):
        from k_zero_core.modes.director_helpers import build_director_context

        context = build_director_context(
            ["DATOS DEL PRODUCTOR:\nArchivo creado: C:\\tmp\\Demo.docx\nTipo: docx"],
            roles=["productor"],
        )

        self.assertIn("Incluye las rutas exactas", context)
        self.assertIn("no afirmes que no tienes acceso", context)

    def test_director_keeps_write_tools_only_for_productor(self):
        from k_zero_core.modes.director_helpers import ROLE_DEFINITIONS

        write_tools = {
            "crear_docx",
            "crear_pdf",
            "crear_xlsx",
            "crear_pptx",
            "editar_docx_copia",
            "editar_pdf_copia",
            "editar_xlsx_copia",
            "editar_pptx_copia",
        }
        documentalista_tools = {tool.__name__ for tool in ROLE_DEFINITIONS["documentalista"].tools}
        datos_tools = {tool.__name__ for tool in ROLE_DEFINITIONS["datos"].tools}
        productor_tools = {tool.__name__ for tool in ROLE_DEFINITIONS["productor"].tools}

        self.assertTrue(write_tools.isdisjoint(documentalista_tools))
        self.assertTrue(write_tools.isdisjoint(datos_tools))
        self.assertTrue(write_tools.issubset(productor_tools))

    def test_new_tools_are_registered_globally(self):
        from k_zero_core.core.tools import get_all_tools

        names = {tool.__name__ for tool in get_all_tools()}

        expected = {
            "leer_archivo_inteligente",
            "analizar_docx",
            "crear_pdf",
            "analizar_archivos_frontend",
            "validar_entregable",
        }
        self.assertTrue(expected.issubset(names))


if __name__ == "__main__":
    unittest.main()
