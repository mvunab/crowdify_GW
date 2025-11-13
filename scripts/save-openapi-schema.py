#!/usr/bin/env python3
"""
Script para guardar el schema OpenAPI de la API en el proyecto.
Útil para que el agente de IA pueda leer la documentación de la API.
"""

import json
import sys
import requests
from pathlib import Path

# URL de la API (ajusta según tu entorno)
API_URL = "http://localhost:8000"
OPENAPI_JSON_URL = f"{API_URL}/openapi.json"
OUTPUT_FILE = Path(__file__).parent.parent / "docs" / "openapi.json"


def fetch_openapi_schema():
    """Obtiene el schema OpenAPI de la API"""
    try:
        response = requests.get(OPENAPI_JSON_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener el schema OpenAPI: {e}")
        print(f"Asegúrate de que la API esté corriendo en {API_URL}")
        sys.exit(1)


def main():
    """Función principal"""
    print("Obteniendo schema OpenAPI...")
    openapi_schema = fetch_openapi_schema()
    
    # Guardar archivo
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"Schema OpenAPI guardado en: {OUTPUT_FILE}")
    print("\nEl agente de IA puede leer este archivo para entender tu API.")


if __name__ == "__main__":
    main()

