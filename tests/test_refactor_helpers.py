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


class ConversationFlowTests(unittest.TestCase):
    def test_is_exit_command_normalizes_whitespace_and_case(self):
        from k_zero_core.modes.conversation_flow import is_exit_command

        self.assertTrue(is_exit_command(" salir "))
        self.assertTrue(is_exit_command("EXIT"))
        self.assertTrue(is_exit_command("Quit"))
        self.assertFalse(is_exit_command("continuar"))

    def test_accumulator_stop_words_preserve_existing_order(self):
        from k_zero_core.modes.base import AccumulatorMode
        from k_zero_core.modes.conversation_flow import ACCUMULATOR_STOP_WORDS

        class FakeAccumulatorMode(AccumulatorMode):
            def get_name(self) -> str:
                return "fake"

            def get_description(self) -> str:
                return "fake"

            def get_default_system_prompt(self) -> str:
                return ""

            def process_accumulated(self, texts, chat_session, io_handler) -> None:
                return None

        self.assertEqual(
            ACCUMULATOR_STOP_WORDS,
            ("terminar", "guardar", "fin", "salir", "exit", "quit"),
        )
        self.assertEqual(FakeAccumulatorMode().get_stop_words(), list(ACCUMULATOR_STOP_WORDS))


class RagSetupTests(unittest.TestCase):
    def test_prepare_rag_document_restores_existing_index(self):
        from k_zero_core.modes.rag_setup import prepare_rag_document

        class FakeSession:
            provider = object()
            metadata = {
                "rag_collection_id": "doc-1",
                "rag_embedding_model": "embed-model",
                "rag_file_path": "documento.txt",
            }

        class FakeVectorStore:
            def collection_exists(self, collection_id):
                return collection_id == "doc-1"

        result = prepare_rag_document(
            FakeSession(),
            io_handler=None,
            vector_store=FakeVectorStore(),
            output_func=lambda _text: None,
        )

        self.assertEqual(result.collection_id, "doc-1")
        self.assertEqual(result.file_path, "documento.txt")

    def test_prepare_rag_document_indexes_new_file_and_updates_metadata(self):
        from k_zero_core.modes.rag_setup import prepare_rag_document

        class FakeProvider:
            def get_available_models(self):
                return ["embed-model"]

        class FakeSession:
            provider = FakeProvider()

            def __init__(self):
                self.metadata = {}

        class FakeIO:
            def __init__(self):
                self.responses = []

            def output_response(self, text):
                self.responses.append(text)

        class FakeEngine:
            instances = []

            def __init__(self, embedding_model, vector_store):
                self.embedding_model = embedding_model
                self.vector_store = vector_store
                self.ingested = None
                FakeEngine.instances.append(self)

            def is_indexed(self, collection_id):
                return False

            def ingest(self, text, collection_id):
                self.ingested = (text, collection_id)
                return 2

        session = FakeSession()
        io_handler = FakeIO()
        result = prepare_rag_document(
            session,
            io_handler,
            vector_store=object(),
            choose_embedding_model_func=lambda provider: "embed-model",
            input_func=lambda _prompt: "\"C:\\docs\\file.txt\"",
            extract_text_func=lambda path: f"texto de {path}",
            compute_collection_id_func=lambda path: "doc-new",
            engine_cls=FakeEngine,
            output_func=lambda _text: None,
        )

        self.assertEqual(result.collection_id, "doc-new")
        self.assertEqual(FakeEngine.instances[0].ingested, ("texto de C:\\docs\\file.txt", "doc-new"))
        self.assertEqual(
            session.metadata,
            {
                "rag_collection_id": "doc-new",
                "rag_embedding_model": "embed-model",
                "rag_file_path": "C:\\docs\\file.txt",
            },
        )
        self.assertEqual(io_handler.responses, ["Documento listo. ¿Qué quieres saber?"])


if __name__ == "__main__":
    unittest.main()
