.PHONY: help up down build logs shell test poetry-add poetry-update clean

help: ## Mostrar este mensaje de ayuda
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Levantar todos los servicios
	docker compose up -d

down: ## Detener todos los servicios
	docker compose down

build: ## Construir las imágenes desde cero
	docker compose build --no-cache

logs: ## Ver logs de todos los servicios
	docker compose logs -f

logs-backend: ## Ver logs solo del backend
	docker compose logs -f backend

logs-worker: ## Ver logs solo del worker
	docker compose logs -f worker

shell: ## Abrir shell en el contenedor backend
	docker compose exec backend bash

shell-db: ## Abrir psql en la base de datos
	docker compose exec db psql -U tickets -d tickets

test: ## Ejecutar tests
	docker compose exec backend poetry run pytest

poetry-add: ## Agregar dependencia (uso: make poetry-add PKG=fastapi-users)
	docker compose exec backend poetry add $(PKG)

poetry-add-dev: ## Agregar dependencia de desarrollo (uso: make poetry-add-dev PKG=black)
	docker compose exec backend poetry add --group dev $(PKG)

poetry-update: ## Actualizar dependencias
	docker compose exec backend poetry update

poetry-lock: ## Regenerar poetry.lock
	docker compose exec backend poetry lock
	docker compose cp backend:/app/poetry.lock .

poetry-show: ## Ver dependencias instaladas
	docker compose exec backend poetry show --tree

clean: ## Limpiar contenedores, volúmenes e imágenes
	docker compose down -v
	docker system prune -f

restart: down up ## Reiniciar todos los servicios

restart-backend: ## Reiniciar solo el backend
	docker compose restart backend

ps: ## Ver estado de los servicios
	docker compose ps

health: ## Verificar health de los servicios
	@echo "Backend API:"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ Backend no responde"
	@echo "\nBackend Ready:"
	@curl -s http://localhost:8000/ready | python -m json.tool || echo "❌ Backend no está ready"
	@echo "\nPDF Service:"
	@curl -s http://localhost:9002/health | python -m json.tool || echo "❌ PDF Service no responde"
