import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class ToolRegistryTests(unittest.TestCase):
    def test_tool_specs_preserve_callable_order(self):
        from k_zero_core.core.tools import get_all_tools, get_available_tool_specs, get_tool_specs

        tools = get_all_tools()
        specs = get_tool_specs()

        self.assertEqual([tool.__name__ for tool in tools], [spec.name for spec in specs])
        self.assertTrue(all(spec.func in tools for spec in specs))
        self.assertLessEqual(len(get_available_tool_specs()), len(specs))


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


class DirectorDeclarativeTests(unittest.TestCase):
    def test_role_definitions_keep_existing_role_order(self):
        from k_zero_core.modes.director_helpers import ROLE_DEFINITIONS, parse_roles

        self.assertEqual(list(ROLE_DEFINITIONS), ["investigador", "analista", "tecnico"])
        self.assertEqual(parse_roles("investigador, técnico, analista"), ["investigador", "analista", "tecnico"])


if __name__ == "__main__":
    unittest.main()
