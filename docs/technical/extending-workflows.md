# Extender Workflows

Los workflows declarativos viven en `K_ZERO_DATA_DIR/workflows` o, si no se configura, en `~/.k_zero/workflows`.

## Formato JSON

```json
{
  "key": "mi_workflow",
  "name": "Mi Workflow",
  "description": "Describe qué resultado produce",
  "audience": "user",
  "cost": "free",
  "privacy": "local",
  "input_type": "text",
  "output_type": "text",
  "mode_key": "",
  "default_provider": "ollama",
  "toolsets": ["documents", "design"],
  "roles": ["documentalista", "productor", "verificador"],
  "system_prompt": "Instrucciones del workflow",
  "requires_llm": true,
  "requires_confirmation_for_writes": true,
  "writes_files": true,
  "write_description": "escribe copias en exports"
}
```

Los valores de `toolsets`, `roles` y `mode_key` se validan contra los registros internos. Un workflow JSON no puede importar ni ejecutar código Python; solo configura capacidades ya registradas.

## Bloques Técnicos

- `ToolSpec`: describe permisos, costo, privacidad, audiencia y escritura.
- `TOOLSETS`: agrupa tools por capacidad.
- `DirectorEngine`: ejecuta roles explícitos o clasificados.
- `AIProvider`: declara si es local/cloud y si soporta tools.
- `WorkflowStore`: guarda, carga, crea desde plantilla y exporta workflows JSON.

No se generan clases Python para workflows personalizados; el JSON se valida y se ejecuta como configuración.

## Providers Cloud

Los providers declarativos OpenAI-compatible aceptan `supports_tools`.

```json
{
  "providers": [
    {
      "key": "openrouter",
      "display_name": "OpenRouter",
      "base_url": "https://openrouter.ai/api/v1",
      "api_key_env": "OPENROUTER_API_KEY",
      "models": ["openai/gpt-4o-mini"],
      "default_model": "openai/gpt-4o-mini",
      "supports_streaming": true,
      "supports_tools": true
    }
  ]
}
```

Si `supports_tools` es `false` o se omite, el provider puede usarse para chat y workflows sin tools, pero no para workflows agenticos como `crear_entregable`.
