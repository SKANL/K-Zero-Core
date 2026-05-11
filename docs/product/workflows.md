# Workflows Guiados

La CLI ahora presenta primero tareas guiadas. Los modos siguen existiendo, pero quedan como experiencias avanzadas o motores internos.

## Workflows Built-In

- `transcribir_audio`: transcripción local sin LLM.
- `organizar_ideas`: acumula ideas y genera notas.
- `preguntar_documento`: RAG local sobre documentos.
- `crear_entregable`: usa documentalista, productor y verificador para crear documentos en `exports`.
- `investigar_fuentes`: usa investigación web con fuentes citables.
- `analizar_proyecto`: inspecciona carpetas/proyectos locales con foco técnico y seguridad.

## UX Free-First

Antes de ejecutar un workflow, el motor genera un resumen de costo, privacidad, uso de red y escritura de archivos. La ruta local/gratis se mantiene como default; cloud y servicios pagos son opt-in.

## Primer Uso Local Gratis

1. Instala y abre Ollama.
2. Descarga un modelo de chat local, por ejemplo `ollama pull llama3.1`.
3. Para RAG, descarga un modelo de embeddings, por ejemplo `ollama pull nomic-embed-text`.
4. Ejecuta K-Zero-Core y elige `Tareas guiadas`.
5. Empieza por `Transcribir audio`, `Organizar mis ideas` o `Preguntar sobre un documento`.

Los workflows que escriben archivos piden confirmación antes de continuar. Los entregables documentales guardan copias en `exports`; transcripción, BrainDump y RAG pueden guardar transcripciones, notas o índices locales dentro de `K_ZERO_DATA_DIR`.

## Cloud Opcional

Los providers cloud OpenAI-compatible pueden configurarse en `providers.json`. Si un provider no declara `supports_tools: true`, los workflows agenticos que necesitan tools se bloquean con un mensaje claro. Los workflows no agenticos pueden ejecutarse con providers cloud sin tool calling.
