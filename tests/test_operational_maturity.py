import json
import io
import logging
import os
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch


class ToolRegistryTests(unittest.TestCase):
    def test_tool_specs_preserve_callable_order(self):
        from k_zero_core.core.tools import get_all_tools, get_available_tool_specs, get_tool_specs

        tools = get_all_tools()
        specs = get_tool_specs()

        self.assertEqual([tool.__name__ for tool in tools], [spec.name for spec in specs])
        self.assertTrue(all(spec.func in tools for spec in specs))
        self.assertLessEqual(len(get_available_tool_specs()), len(specs))

    def test_document_write_tools_are_marked_write_local(self):
        from k_zero_core.core.tools import get_tool_specs
        from k_zero_core.core.tools.registry import ToolPermission

        specs = {spec.name: spec for spec in get_tool_specs()}

        for name in {
            "crear_docx",
            "editar_docx_copia",
            "crear_pdf",
            "editar_pdf_copia",
            "dividir_pdf_copia",
            "combinar_pdf_copia",
            "crear_xlsx",
            "editar_xlsx_copia",
            "crear_pptx",
            "editar_pptx_copia",
            "crear_design_md",
        }:
            self.assertEqual(specs[name].permission, ToolPermission.WRITE_LOCAL, name)

        self.assertEqual(specs["analizar_pdf"].permission, ToolPermission.READ_ONLY)


class ToolOutputTests(unittest.TestCase):
    def test_short_tool_output_stays_inline(self):
        from k_zero_core.core.tool_output import prepare_tool_result

        self.assertEqual(prepare_tool_result("respuesta corta", max_inline_chars=100), "respuesta corta")

    def test_large_tool_output_is_persisted_without_overwriting(self):
        from k_zero_core.core.tool_output import prepare_tool_result

        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_dir = Path(tmpdir)
            result = prepare_tool_result("x" * 25, max_inline_chars=10, artifact_dir=artifact_dir)

            self.assertIn("Resultado demasiado grande", result)
            files = list(artifact_dir.glob("tool-result-*.txt"))
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].read_text(encoding="utf-8"), "x" * 25)


class ToolExecutorTests(unittest.TestCase):
    def test_execute_tool_calls_appends_assistant_and_tool_messages(self):
        from k_zero_core.core.tool_executor import execute_tool_calls

        def sumar(a: int, b: int) -> str:
            return str(a + b)

        messages = [{"role": "user", "content": "suma"}]
        response_message = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "sumar", "arguments": {"a": 2, "b": 3}}}
            ],
        }

        self.assertTrue(execute_tool_calls(response_message, messages, [sumar]))
        self.assertEqual(messages[-1], {"role": "tool", "content": "5", "name": "sumar"})
        self.assertEqual(messages[1]["tool_calls"][0]["function"]["name"], "sumar")

    def test_execute_tool_calls_logs_tool_name_without_stdout_or_sensitive_info(self):
        from k_zero_core.core.tool_executor import execute_tool_calls

        def guardar(api_key: str, url: str, nombre: str) -> str:
            return f"guardado {nombre}"

        messages = [{"role": "user", "content": "guarda"}]
        response_message = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "guardar",
                        "arguments": {
                            "api_key": "sk-secret",
                            "url": "https://example.test/private",
                            "nombre": "demo",
                        },
                    }
                }
            ],
        }

        stdout = io.StringIO()
        with self.assertLogs("k_zero_core.core.tool_executor", level="INFO") as logs:
            with redirect_stdout(stdout):
                self.assertTrue(execute_tool_calls(response_message, messages, [guardar]))

        output = stdout.getvalue()
        joined_logs = "\n".join(logs.output)
        self.assertNotIn("[Agente ejecutando", output)
        self.assertIn("Ejecutando tool: guardar", joined_logs)
        self.assertNotIn("sk-secret", joined_logs)
        self.assertNotIn("https://example.test/private", joined_logs)


class WebToolErrorHandlingTests(unittest.TestCase):
    def test_duckduckgo_fallback_returns_error_string_on_network_failure(self):
        from k_zero_core.core.tools.web_search import _buscar_duckduckgo_api

        with patch("urllib.request.urlopen", side_effect=OSError("sin red")):
            result = _buscar_duckduckgo_api("consulta")

        self.assertIn("Error al buscar", result)
        self.assertIn("sin red", result)

    def test_web_reader_returns_error_string_on_network_failure(self):
        from k_zero_core.core.tools.web_reader import leer_pagina_web

        with patch("urllib.request.urlopen", side_effect=OSError("sin red")):
            result = leer_pagina_web("https://example.test")

        self.assertIn("Error al extraer", result)
        self.assertIn("sin red", result)


class ToolSafetyTests(unittest.TestCase):
    def test_resolve_safe_path_rejects_null_bytes(self):
        from k_zero_core.core.tool_safety import resolve_safe_path

        with self.assertRaises(ValueError):
            resolve_safe_path("archivo\x00.txt")

    def test_resolve_safe_path_respects_opt_in_roots(self):
        from k_zero_core.core.tool_safety import resolve_safe_path

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            child = root / "ok.txt"
            child.write_text("ok", encoding="utf-8")

            with patch.dict(os.environ, {"K_ZERO_SAFE_PATH_ROOTS": str(root)}):
                self.assertEqual(resolve_safe_path(str(child)), child.resolve())
                with self.assertRaises(ValueError):
                    resolve_safe_path(str(root.parent / "escape.txt"))

    def test_json_analysis_respects_opt_in_safe_roots(self):
        from k_zero_core.core.tools.analisis_json import analizar_valores_json

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            allowed = root / "datos.json"
            blocked = root.parent / "blocked.json"
            allowed.write_text(json.dumps({"values": [1, 2, 3]}), encoding="utf-8")
            blocked.write_text(json.dumps({"values": [99]}), encoding="utf-8")

            with patch.dict(os.environ, {"K_ZERO_SAFE_PATH_ROOTS": str(root)}):
                self.assertIn("Máximo: 3.0", analizar_valores_json(str(allowed)))
                self.assertIn("fuera de K_ZERO_SAFE_PATH_ROOTS", analizar_valores_json(str(blocked)))


class PromptComposerTests(unittest.TestCase):
    def test_compose_system_prompt_includes_shared_instructions_and_sanitizes(self):
        from k_zero_core.services.prompt_composer import compose_system_prompt

        with tempfile.TemporaryDirectory() as tmpdir:
            shared = Path(tmpdir) / "shared_instructions.md"
            shared.write_text("Usa contexto\U000E0041 compartido", encoding="utf-8")

            prompt = compose_system_prompt("Prompt base", shared_instructions_file=shared)

        self.assertIn("Prompt base", prompt)
        self.assertIn("Usa contexto compartido", prompt)
        self.assertNotIn("\U000E0041", prompt)


class DeclarativeProviderTests(unittest.TestCase):
    def test_load_declarative_provider_configs_reads_valid_entries(self):
        from k_zero_core.services.providers.declarative import load_declarative_provider_configs

        with tempfile.TemporaryDirectory() as tmpdir:
            providers_file = Path(tmpdir) / "providers.json"
            providers_file.write_text(
                json.dumps(
                    {
                        "providers": [
                            {
                                "key": "ollama_cloud",
                                "display_name": "Ollama Cloud",
                                "base_url": "https://ollama.com/v1",
                                "api_key_env": "OLLAMA_CLOUD_API_KEY",
                                "models": ["gpt-oss:20b"],
                                "default_model": "gpt-oss:20b",
                                "supports_streaming": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            configs = load_declarative_provider_configs(providers_file)

        self.assertEqual(len(configs), 1)
        self.assertEqual(configs[0].key, "ollama_cloud")
        self.assertEqual(configs[0].chat_completions_url, "https://ollama.com/v1/chat/completions")

    def test_parse_sse_chat_chunks_extracts_content(self):
        from k_zero_core.services.providers.declarative import parse_sse_chat_chunks

        payload = [
            b'data: {"choices":[{"delta":{"content":"hola"}}]}\n\n',
            b'data: {"choices":[{"delta":{"content":" mundo"}}]}\n\n',
            b"data: [DONE]\n\n",
        ]

        self.assertEqual(list(parse_sse_chat_chunks(payload)), ["hola", " mundo"])


class DoctorTests(unittest.TestCase):
    def test_doctor_reports_without_running_cleanup(self):
        from k_zero_core.cli.doctor import run_doctor

        with patch("k_zero_core.cli.doctor.OllamaProvider.get_available_models", return_value=["llama3"]):
            report = run_doctor()

        names = [check.name for check in report.checks]
        self.assertIn("data_dir", names)
        self.assertIn("ollama_models", names)
        self.assertIsInstance(report.exit_code, int)


class STTMenuTests(unittest.TestCase):
    def test_choose_stt_config_keeps_file_flow_values(self):
        from k_zero_core.cli.stt_menu import choose_stt_config

        selections = iter([3, 1, 0])

        def select_from_list(_prompt, _options):
            return next(selections)

        with patch("builtins.input", return_value="C:\\audio\\sample.wav"):
            config = choose_stt_config(select_from_list)

        self.assertEqual(
            config,
            {
                "source": "file",
                "filepath": "C:\\audio\\sample.wav",
                "model_size": "base",
                "language": "es",
            },
        )


class AudioFileCaptureTests(unittest.TestCase):
    def test_transcribe_file_source_uses_configured_file_path(self):
        from k_zero_core.audio.file_capture import transcribe_file_source

        class FakeStt:
            def __init__(self):
                self.paths = []

            def transcribe_file(self, path):
                self.paths.append(path)
                return "texto transcrito"

        stt = FakeStt()

        result = transcribe_file_source(stt, {"filepath": "C:\\audio\\sample.wav"}, "file")

        self.assertEqual(result, "texto transcrito")
        self.assertEqual(stt.paths, ["C:\\audio\\sample.wav"])

    def test_transcribe_file_source_cleans_youtube_temp_file(self):
        from k_zero_core.audio.file_capture import transcribe_file_source

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            temp_path = tmp.name

        class FakeStt:
            def transcribe_file(self, path):
                self.received = path
                return "youtube transcrito"

        stt = FakeStt()

        result = transcribe_file_source(
            stt,
            {"youtube_url": "https://example.test/video"},
            "youtube",
            download_youtube_audio_func=lambda _url: temp_path,
        )

        self.assertEqual(result, "youtube transcrito")
        self.assertEqual(stt.received, temp_path)
        self.assertFalse(Path(temp_path).exists())


class CLISessionSetupTests(unittest.TestCase):
    def test_setup_chat_session_restores_saved_provider_and_history(self):
        from k_zero_core.cli.session_setup import setup_chat_session

        class FakePlugin:
            def get_name(self):
                return "Modo Fake"

            def get_default_system_prompt(self):
                return "prompt base"

        class FakeProvider:
            key = "selected"

            def get_display_name(self):
                return "Selected"

        class SavedProvider:
            key = "saved"

            def get_display_name(self):
                return "Saved Provider"

        session = setup_chat_session(
            FakePlugin(),
            FakeProvider(),
            "abc123",
            load_session_func=lambda _sid: {
                "provider": "saved",
                "model": "llama3",
                "metadata": {"x": 1},
                "messages": [{"role": "user", "content": "hola"}],
            },
            get_provider_func=lambda key: SavedProvider(),
        )

        self.assertEqual(session.session_id, "abc123")
        self.assertEqual(session.provider.key, "saved")
        self.assertEqual(session.model, "llama3")
        self.assertEqual(session.metadata, {"x": 1})
        self.assertEqual(session.messages, [{"role": "user", "content": "hola"}])

    def test_setup_chat_session_applies_composed_custom_prompt_for_new_session(self):
        from k_zero_core.cli.session_setup import setup_chat_session

        class FakePlugin:
            def get_name(self):
                return "Modo Fake"

            def get_default_system_prompt(self):
                return "prompt base"

        class FakeProvider:
            key = "ollama"

            def get_display_name(self):
                return "Ollama"

        session = setup_chat_session(
            FakePlugin(),
            FakeProvider(),
            None,
            choose_model_func=lambda _provider: "llama3",
            choose_system_prompt_func=lambda _default: "prompt usuario",
            compose_prompt_func=lambda prompt: f"compuesto: {prompt}",
        )

        self.assertEqual(session.model, "llama3")
        self.assertEqual(
            session.messages,
            [{"role": "system", "content": "compuesto: prompt usuario"}],
        )


class RAGSearchContextTests(unittest.TestCase):
    def test_buscar_en_documentos_uses_active_context(self):
        from k_zero_core.core.tools.rag_search import buscar_en_documentos_locales, set_active_rag

        class FakeRagEngine:
            def search(self, query: str, collection_id: str, top_k: int = 3):
                self.received = (query, collection_id, top_k)
                return ["fragmento"]

        engine = FakeRagEngine()
        set_active_rag(engine, "doc-123")

        result = buscar_en_documentos_locales("pregunta", top_k=2)

        self.assertIn("fragmento", result)
        self.assertEqual(engine.received, ("pregunta", "doc-123", 2))


class RagEngineEmbeddingClientTests(unittest.TestCase):
    def test_ingest_uses_named_batch_size_constant(self):
        from k_zero_core.services.rag_engine import RagEngine

        self.assertEqual(RagEngine.EMBEDDING_BATCH_SIZE, 50)

    def test_ingest_uses_injected_embedding_client_for_document_batches(self):
        from k_zero_core.services.rag_engine import RagEngine

        class FakeStore:
            def __init__(self):
                self.stored = None

            def collection_exists(self, _collection_id):
                return False

            def store(self, collection_id, chunks, embeddings):
                self.stored = (collection_id, chunks, embeddings)

        class FakeEmbeddingClient:
            def __init__(self):
                self.document_calls = []

            def embed_documents(self, model, texts):
                self.document_calls.append((model, texts))
                return [[float(i)] for i, _text in enumerate(texts)]

        store = FakeStore()
        embeddings = FakeEmbeddingClient()
        engine = RagEngine("embed-model", store, embedding_client=embeddings)

        total = engine.ingest("Una oración. Otra oración.", "doc-1")

        self.assertEqual(total, 1)
        self.assertEqual(embeddings.document_calls[0][0], "embed-model")
        self.assertEqual(embeddings.document_calls[0][1], ["search_document: Una oración. Otra oración."])
        self.assertEqual(store.stored[0], "doc-1")
        self.assertEqual(store.stored[2], [[0.0]])

    def test_ingest_reports_progress_with_logger_not_stdout(self):
        from k_zero_core.services.rag_engine import RagEngine

        class FakeStore:
            def store(self, _collection_id, _chunks, _embeddings):
                return None

        class FakeEmbeddingClient:
            def embed_documents(self, _model, texts):
                return [[1.0] for _text in texts]

        engine = RagEngine("embed-model", FakeStore(), embedding_client=FakeEmbeddingClient())
        stdout = io.StringIO()

        with self.assertLogs("k_zero_core.services.rag_engine", level="INFO") as logs:
            with redirect_stdout(stdout):
                total = engine.ingest("Una oración. Otra oración.", "doc-1")

        self.assertEqual(total, 1)
        self.assertEqual(stdout.getvalue(), "")
        joined_logs = "\n".join(logs.output)
        self.assertIn("Fragmentando en 1 bloques", joined_logs)
        self.assertIn("Generando embeddings con 'embed-model'", joined_logs)
        self.assertIn("Guardando en base de datos vectorial", joined_logs)

    def test_search_uses_injected_embedding_client_for_query(self):
        from k_zero_core.services.rag_engine import RagEngine

        class FakeStore:
            def __init__(self):
                self.received = None

            def search(self, collection_id, query_embedding, top_k):
                self.received = (collection_id, query_embedding, top_k)
                return ["fragmento"]

        class FakeEmbeddingClient:
            def __init__(self):
                self.query_calls = []

            def embed_query(self, model, text):
                self.query_calls.append((model, text))
                return [42.0]

        store = FakeStore()
        embeddings = FakeEmbeddingClient()
        engine = RagEngine("embed-model", store, embedding_client=embeddings)

        result = engine.search("pregunta", "doc-1", top_k=2)

        self.assertEqual(result, ["fragmento"])
        self.assertEqual(embeddings.query_calls, [("embed-model", "search_query: pregunta")])
        self.assertEqual(store.received, ("doc-1", [42.0], 2))


class DirectorDeclarativeTests(unittest.TestCase):
    def test_role_definitions_keep_existing_role_order(self):
        from k_zero_core.modes.director_helpers import ROLE_DEFINITIONS, parse_roles

        self.assertEqual(list(ROLE_DEFINITIONS)[:4], ["investigador", "analista", "tecnico", "voz"])
        self.assertIn("documentalista", ROLE_DEFINITIONS)
        self.assertIn("verificador", ROLE_DEFINITIONS)
        self.assertEqual(parse_roles("investigador, técnico, analista"), ["investigador", "analista", "tecnico"])


class VectorStoreLoggingTests(unittest.TestCase):
    def test_search_logs_chromadb_errors_and_returns_empty_list(self):
        from k_zero_core.services import vector_store
        from k_zero_core.services.vector_store import VectorStore

        class FailingClient:
            def get_collection(self, name):
                raise RuntimeError(f"fallo {name}")

        with patch.object(vector_store.chromadb, "PersistentClient", return_value=FailingClient()):
            store = VectorStore()
            with self.assertLogs("k_zero_core.services.vector_store", level="WARNING") as logs:
                result = store.search("doc-1", [1.0], top_k=1)

        self.assertEqual(result, [])
        self.assertIn("Error buscando en colección ChromaDB 'doc-1'", "\n".join(logs.output))

    def test_cleanup_logs_chromadb_errors_and_returns_zero_without_stdout(self):
        from k_zero_core.services import vector_store
        from k_zero_core.services.vector_store import VectorStore

        class FailingClient:
            def list_collections(self):
                raise RuntimeError("cleanup down")

        with patch.object(vector_store.chromadb, "PersistentClient", return_value=FailingClient()):
            store = VectorStore()
            stdout = io.StringIO()
            with self.assertLogs("k_zero_core.services.vector_store", level="WARNING") as logs:
                with redirect_stdout(stdout):
                    result = store.cleanup_orphan_collections(set())

        self.assertEqual(result, 0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Error limpiando colecciones en ChromaDB", "\n".join(logs.output))


class LoggingConfigTests(unittest.TestCase):
    def tearDown(self):
        from k_zero_core.core.logging_config import configure_logging

        configure_logging(level="WARNING")

    def test_configure_logging_uses_warning_by_default_and_avoids_duplicate_handlers(self):
        from k_zero_core.core.logging_config import configure_logging

        logger = logging.getLogger("k_zero_core")
        configure_logging()
        first_count = len(logger.handlers)
        self.assertEqual(logger.level, logging.WARNING)

        configure_logging()

        self.assertEqual(len(logger.handlers), first_count)

    def test_configure_logging_supports_verbose_env_level_and_log_file(self):
        from k_zero_core.core.logging_config import configure_logging

        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "k-zero.log"
            with patch.dict(os.environ, {"K_ZERO_LOG_LEVEL": "ERROR", "K_ZERO_LOG_FILE": str(log_path)}):
                configure_logging(verbose=True)

            logger = logging.getLogger("k_zero_core")
            for handler in logger.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    handler.setLevel(logging.CRITICAL + 1)
            logger.error("mensaje de prueba")

            self.assertEqual(logger.level, logging.INFO)
            self.assertTrue(log_path.exists())
            self.assertIn("mensaje de prueba", log_path.read_text(encoding="utf-8"))
            configure_logging(level="WARNING")


if __name__ == "__main__":
    unittest.main()
