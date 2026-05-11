# Release Notes: Workflows + Extensibility

Esta rama introduce una UX workflow-first y mantiene los modos existentes como modo avanzado.

## Cambios Principales

- Nuevo paquete `k_zero_core.workflows`.
- Workflows built-in para transcripción, ideas, RAG, entregables, investigación y análisis técnico.
- Metadata de costo, privacidad, red y escritura para tools.
- Metadata de capacidades para providers.
- `DirectorEngine` reusable para orquestación interna.
- `WorkflowStore` para workflows JSON del usuario.
- CLI con `Tareas guiadas`, `Modo avanzado` y `Workflows técnicos`.

## Seguridad y Confianza

- Workflows que escriben archivos, notas, transcripciones o índices locales piden confirmación.
- Workflows JSON no ejecutan código arbitrario.
- Providers sin tool calling se bloquean en workflows agenticos.
- La ruta local/gratis sigue siendo el default.
