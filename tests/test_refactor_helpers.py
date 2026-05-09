import tempfile
import unittest
from pathlib import Path


class ModeStreamingTests(unittest.TestCase):
    def test_stream_chunks_prints_label_and_returns_complete_text(self):
        from k_zero_core.modes.mode_streaming import stream_text_response

        chunks = iter(["hola", " ", "mundo"])
        output: list[str] = []

        result = stream_text_response(chunks, "Respuesta", output.append)

        self.assertEqual(result, "hola mundo")
        self.assertEqual(
            output,
            ["\n[Respuesta]: ", "hola", " ", "mundo", "\n\n"],
        )


class RagHelpersTests(unittest.TestCase):
    def test_compute_collection_id_is_stable_for_same_file_content(self):
        from k_zero_core.modes.rag_helpers import compute_collection_id

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "documento.txt"
            path.write_text("contenido estable", encoding="utf-8")

            first = compute_collection_id(str(path))
            second = compute_collection_id(str(path))

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("doc-"))
        self.assertEqual(len(first), 28)

    def test_build_rag_messages_does_not_mutate_session_history(self):
        from k_zero_core.modes.rag_helpers import build_rag_messages

        history = [{"role": "system", "content": "responde con contexto"}]
        messages = build_rag_messages(history, ["fragmento uno", "fragmento dos"], "pregunta")

        self.assertEqual(history, [{"role": "system", "content": "responde con contexto"}])
        self.assertEqual(len(messages), 2)
        self.assertIn("fragmento uno", messages[-1]["content"])
        self.assertIn("[Pregunta del usuario]\npregunta", messages[-1]["content"])


class DirectorHelpersTests(unittest.TestCase):
    def test_parse_roles_handles_accents_and_none(self):
        from k_zero_core.modes.director_helpers import parse_roles

        self.assertEqual(parse_roles("investigador, técnico, analista"), ["investigador", "analista", "tecnico"])
        self.assertEqual(parse_roles("ninguno"), [])

    def test_build_director_context_includes_sub_agent_results(self):
        from k_zero_core.modes.director_helpers import build_director_context

        context = build_director_context(["DATOS DEL ANALISTA:\n42"])

        self.assertIn("Aquí tienes la información recopilada", context)
        self.assertIn("DATOS DEL ANALISTA:\n42", context)


if __name__ == "__main__":
    unittest.main()
