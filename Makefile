.PHONY: help install install-dev test lint format clean run docker-build docker-up docker-down docker-logs docker-pull-models docker-clean

help:
	@echo "Scout - Development Commands"
	@echo ""
	@echo "Local Development:"
	@echo "  setup         - Initial project setup (venv + install)"
	@echo "  install       - Install core dependencies"
	@echo "  install-dev   - Install development dependencies"
	@echo "  test          - Run test suite"
	@echo "  test-cov      - Run tests with coverage report"
	@echo "  lint          - Run ruff linter"
	@echo "  format        - Format code with black"
	@echo "  typecheck     - Run mypy type checker"
	@echo "  clean         - Remove cache and build artifacts"
	@echo "  run           - Run the Scout application"
	@echo ""
	@echo "Docker Deployment:"
	@echo "  docker-build       - Build Scout Docker image"
	@echo "  docker-up          - Start Scout with Docker Compose"
	@echo "  docker-down        - Stop Scout containers"
	@echo "  docker-logs        - View Scout container logs"
	@echo "  docker-pull-models - Pull required Ollama models"
	@echo "  docker-clean       - Remove all Scout containers and volumes"
	@echo ""

setup:
	python -m venv venv
	@echo "Virtual environment created. Activate with:"
	@echo "  Windows: venv\\Scripts\\activate"
	@echo "  Linux/Mac: source venv/bin/activate"
	@echo "Then run: make install-dev"

install:
	pip install --upgrade pip
	pip install -r requirements.txt

install-dev:
	pip install --upgrade pip
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

lint:
	ruff check src/ tests/

format:
	black src/ tests/

typecheck:
	mypy src/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete

run:
	uvicorn src.web.main:app --reload --host 0.0.0.0 --port 8000

# Docker commands
docker-build:
	docker build -t scout-app:latest .

docker-up:
	docker compose --profile ollama-cpu up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f scout

docker-pull-models:
	@echo "Pulling required Ollama models..."
	docker exec scout-ollama ollama pull qwen2.5:3b
	docker exec scout-ollama ollama pull gemma2:2b
	@echo "Models pulled successfully!"

docker-clean:
	docker compose down -v
	docker rmi scout-app:latest 2>/dev/null || true
