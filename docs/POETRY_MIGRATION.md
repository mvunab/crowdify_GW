# Migración a Poetry

## ✅ Completado el 5 de Noviembre, 2025

Este proyecto ha sido migrado de `requirements.txt` a **Poetry** para mejor gestión de dependencias.

## 🎯 ¿Por qué Poetry?

- ✅ **Gestión moderna**: Estándar de facto en Python moderno
- ✅ **Lock file determinístico**: Builds reproducibles con `poetry.lock`
- ✅ **Separación de entornos**: Dev vs Producción
- ✅ **Mejor resolución**: Conflictos de dependencias detectados temprano
- ✅ **Integración Docker**: Cache más eficiente, builds más rápidos

## 📦 Cambios realizados

### Archivos nuevos/modificados

- ✅ `pyproject.toml` - Configuración de Poetry y dependencias
- ✅ `Dockerfile` - Actualizado para instalar Poetry
- ✅ `docker-compose.yml` - Comandos usan `poetry run`
- ✅ `.gitignore` - Agregado `poetry.lock` y `.poetry/`
- ✅ `.dockerignore` - Optimizado para Poetry
- ✅ `README.md` - Instrucciones actualizadas

### Archivos conservados (por ahora)

- ⚠️ `requirements.txt` - Mantener temporalmente por compatibilidad
- ⚠️ `pdfsvc/requirements.txt` - PDF service aún usa pip (considerar migrar después)

## 🚀 Uso diario

### Agregar dependencias

```pwsh
# Dependencia de producción
docker compose exec backend poetry add requests

# Dependencia de desarrollo
docker compose exec backend poetry add --group dev black

# Con versión específica
docker compose exec backend poetry add "fastapi>=0.104.0,<0.105.0"
```

### Actualizar dependencias

```pwsh
# Actualizar todas
docker compose exec backend poetry update

# Actualizar una específica
docker compose exec backend poetry update fastapi

# Ver dependencias desactualizadas
docker compose exec backend poetry show --outdated
```

### Instalar dependencias nuevas

```pwsh
# Después de hacer pull con nuevas deps en pyproject.toml
docker compose exec backend poetry install
```

### Eliminar dependencias

```pwsh
docker compose exec backend poetry remove requests
```

## 🔧 Troubleshooting

### Error: "Poetry lock file is not compatible"

Regenera el lock file:

```pwsh
docker compose exec backend poetry lock --no-update
```

### Error: "Package not found in dependencies"

Asegúrate que está en `pyproject.toml` y ejecuta:

```pwsh
docker compose exec backend poetry install
```

### Desarrollo local sin Docker

Instala Poetry en tu máquina:

```pwsh
# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

# Luego
poetry install
poetry shell
poetry run uvicorn main:app --reload
```

## 📊 Comparación: requirements.txt vs Poetry

| Aspecto               | requirements.txt    | Poetry               |
| --------------------- | ------------------- | -------------------- |
| Lock file             | ❌ No               | ✅ Sí (poetry.lock)  |
| Resolución conflictos | ❌ Manual           | ✅ Automática        |
| Dev dependencies      | ❌ Archivo separado | ✅ Grupos integrados |
| Builds reproducibles  | ⚠️ Parcial          | ✅ Completo          |
| Gestión de versiones  | ❌ Manual           | ✅ Semántica         |
| Cache en Docker       | ⚠️ Básico           | ✅ Avanzado          |

## 🔄 Rollback (si es necesario)

Si necesitas volver a `requirements.txt`:

1. Revierte cambios en `Dockerfile`:

   ```dockerfile
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   ```

2. Revierte `docker-compose.yml`:

   ```yaml
   command:
     ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
   ```

3. Rebuild:
   ```pwsh
   docker compose down
   docker compose up -d --build
   ```

## 📝 Próximos pasos (opcional)

- [ ] Migrar `pdfsvc/` a Poetry también
- [ ] Agregar pre-commit hooks con Poetry
- [ ] Configurar CI/CD para usar Poetry
- [ ] Implementar `poetry export` para generar requirements.txt si se necesita compatibilidad

## 🔗 Referencias

- [Poetry Docs](https://python-poetry.org/docs/)
- [Poetry con Docker](https://python-poetry.org/docs/faq/#i-want-to-use-poetry-with-docker)
- [Poetry Commands](https://python-poetry.org/docs/cli/)
