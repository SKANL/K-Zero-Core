# K-Zero-Core

K-Zero-Core es una librería modular para la orquestación de LLMs locales (vía Ollama u otros proveedores), sistemas RAG (Retrieval-Augmented Generation), y agentes interactivos con capacidades de voz.

Diseñada para ser la base de proyectos más grandes (como interfaces gráficas o sistemas especializados), abstrae la complejidad de manejar sesiones, embeddings, text-to-speech y flujos de conversación continua.

## Características Principales

- 🧠 **Proveedores de IA Agnostic**: Integración nativa con Ollama, fácil de extender a proveedores en la nube (Groq, OpenAI, etc.).
- 🎙️ **Voz Bidireccional Nativa**: Dictado (STT) usando Faster-Whisper y lectura (TTS) usando Edge-TTS.
- 📚 **RAG Integrado**: Ingestión de PDFs/TXTs y búsqueda semántica respaldada por ChromaDB.
- 🛠️ **Arquitectura de Herramientas**: Facilidad para que el LLM ejecute código Python local como herramientas (ej. buscar en web, leer sistema de archivos).
- 💾 **Gestión de Sesiones**: Persistencia automática de conversaciones para continuar chats pasados sin esfuerzo.
- ⚙️ **Extensibilidad Máxima**: Diseñado para agregar nuevos "Modos" de interacción, "Tools" y "Proveedores" escribiendo apenas dos archivos.

## Instalación

Puedes instalar K-Zero-Core directamente en tu entorno virtual:

```bash
pip install -e .
```

O si lo usas como dependencia en otro proyecto, añádelo a tu `requirements.txt` apuntando a tu repositorio/ruta.

## Uso Básico (Standalone CLI)

La librería incluye una interfaz de terminal completa lista para usar. Una vez instalada, simplemente ejecuta:

```bash
k-zero
```

## Uso como Librería

Para integrar K-Zero-Core en tu propia aplicación, puedes instanciar los componentes centrales.

```python
import os
# Configurar la ruta donde k-zero-core guardará sesiones y datos (opcional)
os.environ["K_ZERO_DATA_DIR"] = "./mi_data"

from k_zero_core.services.chat_session import ChatSession
from k_zero_core.services.providers.ollama_provider import OllamaProvider

# 1. Crear proveedor y sesión
provider = OllamaProvider()
session = ChatSession(model="llama3:latest", provider=provider)

# 2. Enviar un mensaje
session.add_user_message("¡Hola! ¿Cómo estás?")
stream = provider.stream_chat(session.model, session.messages)

# 3. Consumir la respuesta
print("IA: ", end="")
for chunk in stream:
    print(chunk, end="", flush=True)

# 4. Guardar la sesión para el futuro
from k_zero_core.storage.session_manager import save_session
save_session(session)
```

## Extensibilidad

Para aprender a crear tus propios modos de interacción, integrar nuevas APIs de IA o construir herramientas personalizadas para el agente, consulta la [Guía de Extensibilidad](EXTENSIBILITY.md).
