k_zero_core ahora es k_zero_core (se renombró el proyecto, pero la estructura es la misma)

# Guía de Extensibilidad — apiVoice CLI

Documento de referencia para agentes de código que necesiten extender el proyecto.
Cubre tres puntos de extensión: **Proveedores de IA**, **Modos** y **Herramientas (Tools)**.

> **Regla de oro**: cada punto de extensión está diseñado para que solo tengas que
> crear/modificar **2 archivos** como máximo. Nunca modifiques `console.py` ni `menus.py`
> para agregar funcionalidad nueva.

---

## 1. Agregar un Proveedor de IA

### Cuándo usar esto
Cuando quieras integrar un servicio de LLM externo: Groq, Anthropic, OpenAI, Cerebras,
OpenRouter, Google Gemini API, Mistral, etc.

### Archivos involucrados

| Acción | Archivo |
|---|---|
| CREAR | `k_zero_core/services/providers/<nombre>_provider.py` |
| MODIFICAR (2 líneas) | `k_zero_core/services/providers/__init__.py` |

### Contrato obligatorio (`AIProvider`)

Ubicación: `k_zero_core/services/providers/base_provider.py`

```python
class AIProvider(ABC):
    key: str = ""  # Identificador único en minúsculas. Ej: "groq", "openai"

    @abstractmethod
    def get_display_name(self) -> str:
        """Nombre que aparece en el menú de selección. Ej: 'Groq (Cloud)'"""

    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Lista de modelos disponibles en este proveedor.
        Debe lanzar una excepción descriptiva si el servicio no está disponible.
        """

    @abstractmethod
    def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],  # formato OpenAI-compatible
        tools: Optional[List] = None,    # funciones callable, puede ser None
    ) -> Generator[str, None, None]:
        """
        Llamada principal al LLM. Debe hacer `yield` de los fragmentos de texto
        a medida que llegan (streaming). Si el proveedor no soporta streaming,
        hacer yield del texto completo en un solo chunk.
        """
```

### Ejemplo completo: GroqProvider

```python
# k_zero_core/services/providers/groq_provider.py
import os
from typing import List, Dict, Any, Optional, Generator

from groq import Groq  # uv pip install groq

from k_zero_core.services.providers.base_provider import AIProvider
from k_zero_core.core.exceptions import OllamaConnectionError  # reutiliza la excepción base


class GroqProvider(AIProvider):
    """Proveedor de IA usando la API de Groq (Cloud)."""

    key = "groq"

    # Modelos disponibles en Groq — actualizar según la documentación de Groq
    _MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ]

    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise OllamaConnectionError(
                "Variable de entorno GROQ_API_KEY no encontrada. "
                "Agrégala a tu .env o como variable de entorno del sistema."
            )
        self._client = Groq(api_key=api_key)

    def get_display_name(self) -> str:
        return "Groq (Cloud — Ultra rápido)"

    def get_available_models(self) -> List[str]:
        # Groq no requiere descarga — los modelos siempre están disponibles
        return list(self._MODELS)

    def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List] = None,
    ) -> Generator[str, None, None]:
        try:
            stream = self._client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            raise OllamaConnectionError(f"Error en Groq API: {e}")
```

### Registro en 2 líneas

```python
# k_zero_core/services/providers/__init__.py
from k_zero_core.services.providers.groq_provider import GroqProvider  # ← agregar

PROVIDER_REGISTRY: dict[str, Type[AIProvider]] = {
    OllamaProvider.key: OllamaProvider,
    GroqProvider.key: GroqProvider,   # ← agregar
}
```

### Comportamiento automático tras el registro

- Si hay **1 proveedor**: se selecciona sin mostrar menú.
- Si hay **2+ proveedores**: aparece el menú `=== Proveedor de IA ===` automáticamente.
- `choose_embedding_model()` filtra por keywords de embedding — funciona igual con cualquier proveedor.

### Variables de entorno recomendadas

Nunca hardcodees credenciales. Usa un archivo `.env` (python-dotenv ya está instalado vía chromadb):

```bash
# .env (en la raíz del proyecto — NO commitear)
GROQ_API_KEY=gsk_...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

```python
# En tu provider, cargar al inicio:
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
```

---

## 2. Agregar un Modo de Interacción

### Cuándo usar esto
Cuando quieras añadir un nuevo flujo de conversación con el LLM: traductor, generador de código,
tutor, analizador de imágenes, transcriptor, etc.

### Archivos involucrados

| Acción | Archivo |
|---|---|
| CREAR | `k_zero_core/modes/<nombre>.py` |
| MODIFICAR (2 líneas) | `k_zero_core/modes/__init__.py` |

### Elegir la clase base correcta

#### `BaseMode` — para modos conversacionales normales (el más común)

El loop estándar ya está implementado: leer input → agregar a historial → llamar LLM → mostrar respuesta → persistir sesión → repetir.

Solo debes implementar los 3 métodos abstractos. Opcionalmente puedes sobreescribir hooks.

```
Métodos OBLIGATORIOS:
    get_name() -> str               Nombre en el menú
    get_description() -> str        Descripción de una línea en el menú
    get_default_system_prompt() -> Optional[str]   System prompt por defecto

Métodos OPCIONALES (hooks con comportamiento por defecto):
    get_voice() -> str              Voz TTS (default: "es-MX-DaliaNeural")
    get_tools() -> Optional[list]   Tools para el agente (default: todas las tools)
    on_start(session, io) -> None   Lógica antes del loop (default: nada)

Método HEREDADO (ya implementado, usa en subclases avanzadas):
    _stream_and_respond(session, io, label, tools) -> str
```

#### `AccumulatorMode` — para modos que acumulan y procesan en batch

Reemplaza el loop normal por uno que acumula todos los inputs hasta una palabra clave,
luego llama a `process_accumulated()` con toda la lista. Ideal para: dictado, Brain Dump,
transcripción de reuniones, etc.

```
Métodos OBLIGATORIOS (adicionales a BaseMode):
    process_accumulated(texts, session, io) -> None   Procesar lista acumulada

Métodos OPCIONALES:
    get_stop_words() -> List[str]         Palabras que disparan el procesamiento
    get_accumulation_prompt() -> str      Instrucción mostrada al inicio
```

### Ejemplo 1: Modo `BaseMode` simple (Traductor)

```python
# k_zero_core/modes/translator.py
from typing import Optional
from k_zero_core.modes.base import BaseMode


class TranslatorMode(BaseMode):
    def get_name(self) -> str:
        return "Traductor Universal"

    def get_description(self) -> str:
        return "Traduce texto a cualquier idioma. Especifica el idioma destino."

    def get_default_system_prompt(self) -> Optional[str]:
        return (
            "Eres un traductor experto. El usuario te enviará texto y te indicará "
            "el idioma al que quiere traducirlo. Retorna SOLO la traducción, "
            "sin explicaciones adicionales ni comillas."
        )

    def get_tools(self):
        return None  # Los traductores no necesitan tools

    def get_voice(self) -> str:
        return "es-MX-DaliaNeural"  # Cambiar según el idioma destino si es necesario
```

### Ejemplo 2: Modo `AccumulatorMode` (Transcriptor de Reunión)

```python
# k_zero_core/modes/meeting_transcriber.py
from typing import List, Optional
from k_zero_core.modes.base import AccumulatorMode
from k_zero_core.services.chat_session import ChatSession
from k_zero_core.audio.io_handler import IOHandler
from k_zero_core.core.config import DATA_DIR
import datetime


class MeetingTranscriberMode(AccumulatorMode):
    def get_name(self) -> str:
        return "Transcriptor de Reunión"

    def get_description(self) -> str:
        return "Dicta los puntos de la reunión y genera el acta en Markdown."

    def get_default_system_prompt(self) -> Optional[str]:
        return (
            "Eres un secretario corporativo. Recibirás notas crudas de una reunión. "
            "Genera un acta profesional en Markdown con: asistentes (si se mencionan), "
            "puntos discutidos, acuerdos y responsables."
        )

    def get_stop_words(self) -> List[str]:
        return ["acta lista", "terminar", "fin", "salir"]

    def get_accumulation_prompt(self) -> str:
        return "Dicta los puntos de la reunión. Habla con naturalidad."

    def process_accumulated(
        self,
        texts: List[str],
        chat_session: ChatSession,
        io_handler: IOHandler,
    ) -> None:
        if not texts:
            print("No se dictó ningún punto.")
            return

        contenido = "\n".join(f"- {t}" for t in texts)
        chat_session.add_user_message(
            f"Genera el acta con estos puntos:\n{contenido}"
        )

        stream = chat_session.provider.stream_chat(chat_session.model, chat_session.messages)
        acta = "".join(stream)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo = DATA_DIR / f"acta_{timestamp}.md"
        archivo.write_text(acta, encoding="utf-8")

        print(f"\n✅ Acta guardada en: {archivo}")
        io_handler.output_response("El acta ha sido generada.")
```

### Ejemplo 3: Modo con `run()` sobreescrito (control total del loop)

Solo necesario cuando el flujo es radicalmente diferente (ej: el modo RAG existente).

```python
# k_zero_core/modes/mi_modo_avanzado.py
from k_zero_core.modes.base import BaseMode
from k_zero_core.services.chat_session import ChatSession
from k_zero_core.audio.io_handler import IOHandler
from k_zero_core.storage.session_manager import save_session


class MiModoAvanzado(BaseMode):
    def get_name(self): return "Mi Modo Avanzado"
    def get_description(self): return "Descripción."
    def get_default_system_prompt(self): return "System prompt."

    def on_start(self, chat_session: ChatSession, io_handler: IOHandler) -> None:
        # Inicialización: conectar a servicios externos, cargar datos, etc.
        self._alguna_variable = "valor"

    def run(self, chat_session: ChatSession, io_handler: IOHandler) -> None:
        print(f"\n--- Modo Activado: {self.get_name()} ---")
        self.on_start(chat_session, io_handler)

        while True:
            user_text = io_handler.get_user_input()
            if not user_text:
                continue
            if user_text.lower().strip() in ['salir', 'exit', 'quit']:
                break

            # Tu lógica personalizada aquí...
            chat_session.add_user_message(user_text)
            respuesta = self._stream_and_respond(chat_session, io_handler)
            # _stream_and_respond ya guarda la sesión y activa TTS automáticamente
```

### Registro en 2 líneas

```python
# k_zero_core/modes/__init__.py
from k_zero_core.modes.translator import TranslatorMode  # ← agregar

MODE_REGISTRY: dict[str, Type[BaseMode]] = {
    "classic":     ClassicMode,
    "companion":   VoiceCompanionMode,
    "dungeon_master": DungeonMasterMode,
    "agent":       AgentMode,
    "brain_dump":  BrainDumpMode,
    "rag":         DocumentRAGMode,
    "translator":  TranslatorMode,  # ← agregar (la key determina el orden)
}
```

### Persistencia de estado de sesión en un Modo

Si tu modo necesita guardar datos entre sesiones (como el modo RAG guarda el `collection_id`),
usa `chat_session.metadata` — es un `dict` libre persistido automáticamente en el JSON de sesión:

```python
# Guardar estado específico de tu modo
chat_session.metadata["mi_modo_config"] = {
    "parametro": "valor",
    "otro": 42,
}

# Recuperar al reanudar sesión (en on_start):
config = chat_session.metadata.get("mi_modo_config", {})
parametro = config.get("parametro")
```

---

## 3. Agregar una Herramienta (Tool)

### Cuándo usar esto
Las tools son funciones Python que el modelo puede invocar durante una conversación cuando
lo necesite. Ejemplos útiles: búsqueda web, ejecutar scripts, llamar APIs externas,
leer sensores, etc. Solo los modos que retornan tools las usan (por defecto todos excepto RAG).

### Archivos involucrados

| Acción | Archivo |
|---|---|
| CREAR | `k_zero_core/core/tools/<nombre_tool>.py` |
| MODIFICAR (2 líneas) | `k_zero_core/core/tools/__init__.py` |

### Contrato de una Tool

El SDK de Ollama parsea automáticamente las funciones Python en schemas de herramientas
usando los **type hints** y el **docstring**. Esto es crítico — el modelo decide cuándo
y cómo llamar a la herramienta basándose únicamente en el docstring.

**Reglas de diseño:**

1. **Nombre descriptivo en inglés o español** — el modelo lo usa para decidir si llamarla.
2. **Type hints obligatorios** en todos los parámetros y en el retorno.
3. **Docstring claro** con sección `Args:` describiendo cada parámetro.
4. **Siempre retornar `str`** — Ollama espera strings como resultado de tools.
5. **Nunca lanzar excepciones al modelo** — captura errores y retorna un mensaje descriptivo.
6. **Parámetros simples** — el modelo tiene que ser capaz de inferirlos. Evita tipos complejos.

### Formato del docstring (crítico para el comportamiento del LLM)

```python
def mi_herramienta(param1: str, param2: int = 10) -> str:
    """
    Una oración clara describiendo QUÉ hace la herramienta y CUÁNDO usarla.

    Args:
        param1: Descripción precisa del parámetro. El modelo la usa para saber
                qué valor pasar. Sé específico.
        param2: Descripción del segundo parámetro (indicar si es opcional y el default).

    Returns:
        Descripción de qué retorna. El modelo lee esto para interpretar el resultado.
    """
```

### Ejemplo 1: Tool simple sin dependencias externas

```python
# k_zero_core/core/tools/clipboard.py
"""Herramienta: Acceso al portapapeles del sistema."""
import subprocess
import sys


def leer_portapapeles() -> str:
    """
    Lee y retorna el contenido actual del portapapeles del sistema operativo.

    Útil cuando el usuario dice 'lo que tengo copiado' o 'en mi portapapeles'.

    Returns:
        El texto en el portapapeles, o un mensaje si está vacío o no disponible.
    """
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["powershell", "-Command", "Get-Clipboard"],
                capture_output=True, text=True
            )
            contenido = result.stdout.strip()
        elif sys.platform == "darwin":
            result = subprocess.run(["pbpaste"], capture_output=True, text=True)
            contenido = result.stdout.strip()
        else:
            result = subprocess.run(["xclip", "-selection", "clipboard", "-o"],
                                    capture_output=True, text=True)
            contenido = result.stdout.strip()

        return contenido if contenido else "(El portapapeles está vacío)"
    except Exception as e:
        return f"Error al leer el portapapeles: {e}"
```

### Ejemplo 2: Tool con dependencia externa (búsqueda web)

```python
# k_zero_core/core/tools/web_search.py
"""Herramienta: Búsqueda en internet usando DuckDuckGo."""
import json
import urllib.request
import urllib.parse


def buscar_en_internet(query: str, max_resultados: int = 3) -> str:
    """
    Busca información actualizada en internet usando DuckDuckGo.

    Usa esta herramienta cuando el usuario pregunte por eventos recientes,
    noticias, precios actuales, o información que pueda haber cambiado.

    Args:
        query: Términos de búsqueda en lenguaje natural. Ej: "precio bitcoin hoy".
        max_resultados: Número máximo de resultados a retornar (1-5, default 3).

    Returns:
        Resumen de los resultados más relevantes con sus fuentes.
    """
    try:
        params = urllib.parse.urlencode({
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        })
        url = f"https://api.duckduckgo.com/?{params}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        resultados = []
        if data.get("AbstractText"):
            resultados.append(f"**Resumen**: {data['AbstractText']}")

        topics = data.get("RelatedTopics", [])[:max_resultados]
        for topic in topics:
            if isinstance(topic, dict) and topic.get("Text"):
                resultados.append(f"- {topic['Text']}")

        if not resultados:
            return f"No se encontraron resultados para: '{query}'"

        return "\n".join(resultados)
    except Exception as e:
        return f"Error al buscar '{query}': {e}"
```

### Ejemplo 3: Tool compleja con estado interno (caché)

Para tools que necesitan estado entre llamadas, usa una clase con `__call__`:

```python
# k_zero_core/core/tools/traductor_tool.py
"""Herramienta: Traducción de texto usando una API."""
import urllib.request
import urllib.parse
import json


class _TraductorTool:
    """Wrapper con caché para evitar llamadas repetidas a la API."""

    def __init__(self):
        self._cache: dict = {}

    def __call__(self, texto: str, idioma_destino: str) -> str:
        """
        Traduce un texto al idioma especificado.

        Args:
            texto: El texto a traducir.
            idioma_destino: Idioma destino en español. Ej: "inglés", "francés", "japonés".

        Returns:
            El texto traducido, o un mensaje de error si falla.
        """
        cache_key = f"{texto[:50]}:{idioma_destino}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Aquí iría la llamada real a la API de traducción
        # ...

        resultado = f"[Traducción a {idioma_destino}: {texto}]"  # placeholder
        self._cache[cache_key] = resultado
        return resultado

    # Necesario para que Ollama SDK pueda parsear el schema
    __name__ = "traducir_texto"
    __doc__ = __call__.__doc__


# Instancia singleton — se registra el objeto callable directamente
traducir_texto = _TraductorTool()
```

### Registro en 2 líneas

```python
# k_zero_core/core/tools/__init__.py
from k_zero_core.core.tools.clipboard import leer_portapapeles  # ← agregar

_ALL_TOOLS: List[Callable] = [
    obtener_hora_actual,
    calcular_matematica,
    leer_archivo,
    listar_directorio,
    informacion_sistema,
    leer_portapapeles,  # ← agregar
]
```

### Controlar qué tools recibe cada Modo

Por defecto, `BaseMode.get_tools()` retorna **todas** las tools. Para personalizar:

```python
# En tu modo, sobreescribir get_tools():
def get_tools(self) -> Optional[list]:
    return None  # Sin tools (ej: RAG mode, Brain Dump)

def get_tools(self) -> Optional[list]:
    # Solo tools específicas
    from k_zero_core.core.tools.filesystem import leer_archivo
    from k_zero_core.core.tools.date_time import obtener_hora_actual
    return [leer_archivo, obtener_hora_actual]

def get_tools(self) -> Optional[list]:
    from k_zero_core.core.tools import get_all_tools
    return get_all_tools()  # Todas (comportamiento por defecto)
```

---

## Estructura de Archivos de Referencia

```
k_zero_core/
├── services/
│   └── providers/
│       ├── base_provider.py      ← Contrato AIProvider (NO modificar)
│       ├── ollama_provider.py    ← Implementación Ollama (referencia)
│       ├── groq_provider.py      ← [NUEVO PROVEEDOR aquí]
│       └── __init__.py           ← PROVIDER_REGISTRY (agregar 2 líneas)
│
├── modes/
│   ├── base.py                   ← BaseMode + AccumulatorMode (NO modificar)
│   ├── classic.py                ← Ejemplo de BaseMode simple
│   ├── brain_dump.py             ← Ejemplo de AccumulatorMode
│   ├── rag.py                    ← Ejemplo de run() sobreescrito
│   ├── mi_nuevo_modo.py          ← [NUEVO MODO aquí]
│   └── __init__.py               ← MODE_REGISTRY (agregar 2 líneas)
│
└── core/
    └── tools/
        ├── __init__.py           ← _ALL_TOOLS registry (agregar 2 líneas)
        ├── date_time.py          ← Ejemplo de tool simple
        ├── matematica.py         ← Ejemplo de tool con lógica compleja
        ├── filesystem.py         ← Ejemplo de 2 tools en un archivo
        ├── sistema.py            ← Ejemplo de tool sin parámetros
        └── mi_nueva_tool.py      ← [NUEVA TOOL aquí]
```

---

## Checklist de Verificación

Después de agregar cualquier extensión, verifica:

```powershell
# 1. Verificación sintáctica (desde la raíz del proyecto)
python -m py_compile k_zero_core/services/providers/mi_provider.py
python -m py_compile k_zero_core/modes/mi_modo.py
python -m py_compile k_zero_core/core/tools/mi_tool.py

# 2. Verificar que el registry lo detecta
python -c "
from k_zero_core.services.providers import PROVIDER_REGISTRY
from k_zero_core.modes import MODE_REGISTRY
from k_zero_core.core.tools import get_all_tools

print('Proveedores:', list(PROVIDER_REGISTRY.keys()))
print('Modos:', list(MODE_REGISTRY.keys()))
print('Tools:', [t.__name__ for t in get_all_tools()])
"

# 3. Prueba funcional mínima
python main.py
```

## Errores Comunes

| Error | Causa | Solución |
|---|---|---|
| `Tool X not in PROVIDER_REGISTRY` | Olvidaste registrar el proveedor | Agregar en `providers/__init__.py` |
| El modo no aparece en el menú | Olvidaste registrar el modo | Agregar en `modes/__init__.py` |
| La tool nunca se llama | Docstring ambiguo o sin Args | Mejorar la descripción del docstring |
| Tool da error al modelo | Excepción no capturada | Envolver en `try/except` y retornar `str` |
| `AttributeError: 'NoneType'` en `stream_chat` | `provider` es None en `ChatSession` | Verificar que `console.py` asigna `provider` antes de llamar a `plugin.run()` |
| Credenciales no encontradas | `.env` no cargado | Agregar `load_dotenv()` en el `__init__` del proveedor |
