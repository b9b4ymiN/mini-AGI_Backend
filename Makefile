# =============================================================================
# Mini-AGI Backend - Makefile
# =============================================================================
# Convenience commands for development and deployment
#
# Usage:
#   make dev         # Start development environment
#   make prod        # Start production environment
#   make logs        # View logs
#   make test        # Test the API
#   make clean       # Stop and clean up
# =============================================================================

.PHONY: help dev prod stop logs test clean pull-model status health

# Default target
help:
	@echo "Mini-AGI Backend - Available Commands:"
	@echo ""
	@echo "  make dev          Start development environment"
	@echo "  make prod         Start production environment"
	@echo "  make stop         Stop all services"
	@echo "  make logs         View service logs"
	@echo "  make logs-f       Follow service logs"
	@echo "  make test         Test API endpoints"
	@echo "  make pull-model   Pull Ollama model"
	@echo "  make status       Show service status"
	@echo "  make health       Check service health"
	@echo "  make clean        Stop and remove containers"
	@echo "  make rebuild      Rebuild and restart"
	@echo "  make shell        Open shell in backend container"
	@echo ""

# Development deployment
dev:
	@echo "Starting development deployment..."
	@test -f .env || (echo "Creating .env from template..." && cp .env.example .env)
	docker-compose up -d --build
	@echo "✓ Development environment started"
	@echo "  Backend: http://localhost:8000"
	@echo "  Ollama: http://localhost:11434"
	@echo ""
	@echo "Next: make pull-model"

# Production deployment
prod:
	@echo "Starting production deployment..."
	@test -f .env || (echo "Creating .env from template..." && cp .env.example .env)
	docker-compose -f docker-compose.prod.yml up -d --build
	@echo "✓ Production environment started"
	@echo "  Backend: http://localhost:8000"
	@echo ""
	@echo "Next: make pull-model && make health"

# Stop services
stop:
	@echo "Stopping services..."
	docker-compose down
	docker-compose -f docker-compose.prod.yml down || true
	@echo "✓ Services stopped"

# View logs (last 100 lines)
logs:
	docker-compose logs --tail=100

# Follow logs
logs-f:
	docker-compose logs -f

# Test API endpoints
test:
	@echo "Testing API endpoints..."
	@echo ""
	@echo "1. Health check:"
	@curl -s http://localhost:8000/health | jq '.'
	@echo ""
	@echo "2. LLM info:"
	@curl -s http://localhost:8000/llm/info | jq '.'
	@echo ""
	@echo "3. Available personas:"
	@curl -s http://localhost:8000/personas | jq '.'
	@echo ""
	@echo "✓ All endpoints tested"

# Pull Ollama model
pull-model:
	@echo "Pulling Ollama model..."
	@MODEL=$$(grep LLM_MODEL .env | cut -d '=' -f2 | tr -d ' '); \
	if docker ps | grep -q "ollama-prod"; then \
		CONTAINER="ollama-prod"; \
	else \
		CONTAINER="ollama"; \
	fi; \
	echo "Pulling $$MODEL into $$CONTAINER..."; \
	docker exec -it $$CONTAINER ollama pull $$MODEL
	@echo "✓ Model pulled"

# Show service status
status:
	@echo "Service Status:"
	@docker-compose ps
	@echo ""
	@echo "Container Stats:"
	@docker stats --no-stream

# Check health
health:
	@echo "Checking service health..."
	@if curl -s http://localhost:8000/health | grep -q "ok"; then \
		echo "✓ Backend is healthy"; \
	else \
		echo "✗ Backend is not responding"; \
		exit 1; \
	fi
	@if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then \
		echo "✓ Ollama is healthy"; \
	else \
		echo "⚠ Ollama is not accessible (may be using external provider)"; \
	fi

# Clean up everything
clean:
	@echo "Cleaning up..."
	docker-compose down -v
	docker-compose -f docker-compose.prod.yml down -v || true
	@echo "✓ Cleanup complete"

# Rebuild and restart
rebuild:
	@echo "Rebuilding..."
	docker-compose up -d --build --force-recreate
	@echo "✓ Rebuild complete"

# Open shell in backend container
shell:
	@if docker ps | grep -q "mini-agi-backend-prod"; then \
		docker exec -it mini-agi-backend-prod bash; \
	else \
		docker exec -it mini-agi-backend bash; \
	fi

# Open shell in Ollama container
shell-ollama:
	@if docker ps | grep -q "ollama-prod"; then \
		docker exec -it ollama-prod bash; \
	else \
		docker exec -it ollama bash; \
	fi

# List Ollama models
list-models:
	@if docker ps | grep -q "ollama-prod"; then \
		docker exec -it ollama-prod ollama list; \
	else \
		docker exec -it ollama ollama list; \
	fi

# Backup Ollama data
backup:
	@echo "Creating backup..."
	@mkdir -p ./backup
	@BACKUP_FILE="backup/ollama-models-$$(date +%Y%m%d-%H%M%S).tar.gz"; \
	docker run --rm \
		-v mini-agi-backend_ollama-data:/data \
		-v $$(pwd)/backup:/backup \
		alpine tar czf /$$BACKUP_FILE /data
	@echo "✓ Backup created in ./backup/"

# Show Docker images
images:
	@docker images | grep -E "mini-agi|ollama|REPOSITORY"

# Prune Docker system (be careful!)
prune:
	@echo "⚠️  This will remove all unused Docker resources!"
	@read -p "Continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker system prune -a; \
	fi
