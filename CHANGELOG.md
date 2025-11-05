# Changelog

Todas las modificaciones importantes del proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [1.0.0] - 2025-11-05

### 🏗️ Refactorización mayor - Reestructuración del proyecto

#### Agregado

- ✅ **Poetry** como gestor de dependencias moderno
  - `pyproject.toml` con todas las dependencias
  - `poetry.lock` para builds reproducibles
  - Soporte para dev dependencies separadas
- ✅ `.dockerignore` optimizado para Poetry
- ✅ `CHANGELOG.md` para tracking de cambios
- ✅ Documentación completa en `docs/POETRY_MIGRATION.md`
- ✅ `.env.example` expandido con más contexto y ejemplos

#### Cambiado

- 🔄 **Estructura del proyecto** - Movido todo de `backend/` a raíz
  - Simplifica la navegación del código
  - Elimina redundancia de carpetas
  - Más alineado con estándares de proyectos Python
- 🔄 **Dockerfile** actualizado para usar Poetry
  - Instala Poetry 1.7.1
  - Usa `poetry install` en lugar de pip
  - Build layers optimizados para mejor cache
- 🔄 **docker-compose.yml** actualizado
  - Build desde raíz (`.` en lugar de `./backend`)
  - Comandos usan `poetry run`
  - Defaults para todas las variables de entorno (sin warnings)
  - Soporte para DATABASE_URL de Supabase o Postgres local
- 🔄 **README.md** expandido con:
  - Instrucciones de Poetry
  - Desarrollo local sin Docker
  - Troubleshooting específico de Poetry
  - Gestión de dependencias
- 🔄 `.gitignore` actualizado para Poetry (excluye `.poetry/` pero NO `poetry.lock`)

#### Eliminado

- ❌ Carpeta `backend/` redundante
  - Todo el código movido a raíz
  - Docs movidos a `docs/`
  - Scripts movidos a `scripts/`
- ❌ `backend/docker-compose.yml` duplicado (ya no necesario)

#### Migración de archivos

```
backend/app/          → app/
backend/services/     → services/
backend/shared/       → shared/
backend/scripts/      → scripts/
backend/main.py       → main.py
backend/Dockerfile    → Dockerfile
backend/requirements.txt → requirements.txt (mantenido por compatibilidad)
backend/.env          → .env
backend/.gitignore    → .gitignore
backend/README.md     → docs/BACKEND_README.md
backend/docs/*        → docs/*
```

### 🐛 Correcciones

- ✅ Eliminado warning de `version` obsoleta en docker-compose
- ✅ Todos los defaults de env vars configurados correctamente
- ✅ Healthcheck de Postgres con default correcto

### 📦 Dependencias

- Todas las dependencias ahora gestionadas por Poetry
- Lock file garantiza versiones exactas reproducibles
- Dev dependencies separadas en grupo `dev`

### ⚡ Mejoras de rendimiento

- Docker builds más rápidos con cache de Poetry
- Layers optimizados en Dockerfile
- Volúmenes configurados correctamente para hot-reload

### 🔒 Seguridad

- Lock file con hashes SHA256 de todas las dependencias
- Resolución automática de conflictos de versiones
- Variables de entorno con defaults seguros para desarrollo

---

## [0.9.0] - Antes de 2025-11-05

### Estado inicial

- Estructura con carpeta `backend/` redundante
- Gestión de dependencias con `requirements.txt`
- Docker Compose funcional pero con warnings
- Supabase configurado como DB principal
