.PHONY: help install install-dev test lint format clean run

help:
	@echo "Scout - Development Commands"
	@echo ""
	@echo "setup         - Initial project setup (venv + install)"
	@echo "install       - Install core dependencies"
	@echo "install-dev   - Install development dependencies"
	@echo "test          - Run test suite"
	@echo "test-cov      - Run tests with coverage report"
	@echo "lint          - Run ruff linter"
	@echo "format        - Format code with black"
	@echo "typecheck     - Run mypy type checker"
	@echo "clean         - Remove cache and build artifacts"
	@echo "run           - Run the Scout application"
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
