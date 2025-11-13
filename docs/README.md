# Documentación de la API

Esta carpeta contiene la documentación completa de la API de Crowdify.

## Archivos Disponibles

- **`API_DOCUMENTATION.md`** - Documentación completa en Markdown con ejemplos
- **`openapi.json`** - Schema OpenAPI 3.1 (generado automáticamente)

## Para el Agente de IA

El agente de IA puede usar estos archivos para entender cómo funciona la API:

1. **`API_DOCUMENTATION.md`** - Documentación legible con ejemplos de uso
2. **`openapi.json`** - Schema técnico con todos los endpoints, parámetros y respuestas

## Generar/Actualizar el Schema OpenAPI

Si necesitas actualizar el schema OpenAPI:

```bash
# Asegúrate de que la API esté corriendo
docker compose up -d backend

# Genera el schema
python scripts/save-openapi-schema.py
```

O manualmente:

```bash
curl http://localhost:8000/openapi.json > docs/openapi.json
```

## Documentación Interactiva

También puedes explorar la API de forma interactiva:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

