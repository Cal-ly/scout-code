---
updated: 2025-10-04, 18:18
---
## Scout PoC - Complete Project Structure & Configuration

### Project Directory Structure

```
scout/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── jobs.py           # Job processing endpoints
│   │   │   ├── profile.py        # Profile management endpoints
│   │   │   ├── generation.py     # Application generation endpoints
│   │   │   └── health.py         # Health check & monitoring
│   │   └── dependencies.py       # Shared dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   ├── collector.py          # Module 1: Profile management
│   │   ├── rinser.py             # Module 2: Job cleaning
│   │   ├── analyzer.py           # Module 3: Matching analysis
│   │   ├── creator.py            # Module 4: Content generation
│   │   ├── formatter.py          # Module 5: Document formatting
│   │   └── pipeline.py           # Orchestration logic
│   ├── models/
│   │   ├── __init__.py
│   │   ├── profile.py            # User profile models
│   │   ├── job.py                # Job posting models
│   │   ├── application.py        # Application package models
│   │   └── analysis.py           # Analysis result models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm.py               # LLM service abstraction
│   │   ├── vector_store.py      # Vector DB abstraction
│   │   ├── cache.py              # Caching service
│   │   └── cost_tracker.py      # API cost monitoring
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py          # Pydantic settings
│   │   └── logging.py           # Logging configuration
│   ├── templates/
│   │   ├── cv/
│   │   │   ├── modern.html
│   │   │   ├── traditional.html
│   │   │   └── ats_friendly.html
│   │   ├── cover_letter/
│   │   │   └── standard.html
│   │   └── web/
│   │       ├── base.html
│   │       ├── index.html
│   │       └── dashboard.html
│   ├── static/
│   │   ├── css/
│   │   │   ├── main.css
│   │   │   └── tailwind.css
│   │   └── js/
│   │       └── app.js
│   └── utils/
│       ├── __init__.py
│       ├── validators.py        # Input validation utilities
│       ├── parsers.py           # Text parsing utilities
│       └── exceptions.py        # Custom exceptions
├── data/
│   ├── profile.yaml             # User profile (git-ignored in production)
│   ├── profile.example.yaml     # Example profile template
│   ├── vectors/                 # ChromaDB storage
│   ├── cache/                   # Response cache
│   └── exports/                 # Generated documents
├── prompts/
│   ├── extraction/
│   │   └── job_structure.txt    # Job parsing prompt
│   ├── analysis/
│   │   └── requirements.txt     # Requirement matching prompt
│   ├── generation/
│   │   ├── cv.txt              # CV generation prompt
│   │   └── cover_letter.txt    # Cover letter prompt
│   └── README.md                # Prompt engineering guide
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest configuration
│   ├── unit/
│   │   ├── test_collector.py
│   │   ├── test_rinser.py
│   │   ├── test_analyzer.py
│   │   ├── test_creator.py
│   │   └── test_formatter.py
│   ├── integration/
│   │   ├── test_pipeline.py
│   │   └── test_api.py
│   └── fixtures/
│       ├── job_postings/
│       │   ├── senior_python.txt
│       │   └── ml_engineer.txt
│       └── profiles/
│           └── test_profile.yaml
├── scripts/
│   ├── setup_dev.sh            # Development environment setup
│   ├── init_db.py              # Database initialization
│   └── test_llm.py             # LLM connection test
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .github/
│   └── workflows/
│       ├── test.yml            # CI testing
│       └── deploy.yml          # Deployment pipeline
├── requirements/
│   ├── base.txt               # Core dependencies
│   ├── dev.txt                # Development dependencies
│   └── prod.txt               # Production dependencies
├── .env.example               # Environment variables template
├── .gitignore
├── Makefile                   # Task automation
├── pyproject.toml            # Project metadata
├── README.md
└── LICENSE
```

### Core Configuration Files

#### `pyproject.toml`
```toml
[tool.poetry]
name = "scout"
version = "0.1.0"
description = "Intelligent Job Application System"
authors = ["Your Name <email@example.com>"]
python = "^3.11"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.110.0"
uvicorn = {extras = ["standard"], version = "^0.27.0"}
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
anthropic = "^0.25.0"
chromadb = "^0.4.22"
sentence-transformers = "^2.3.0"
pyyaml = "^6.0.1"
bleach = "^6.1.0"
weasyprint = "^61.0"
jinja2 = "^3.1.3"
sqlalchemy = "^2.0.25"
aiosqlite = "^0.19.0"
python-multipart = "^0.0.9"
httpx = "^0.26.0"
redis = "^5.0.1"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.23.0"
pytest-cov = "^4.1.0"
black = "^24.1.0"
isort = "^5.13.0"
flake8 = "^7.0.0"
mypy = "^1.8.0"
ipython = "^8.20.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 88
target-version = ["py311"]

[tool.isort]
profile = "black"
line_length = 88

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

#### `app/config/settings.py`
```python
from pydantic_settings import BaseSettings
from typing import Optional, List
from pathlib import Path

class Settings(BaseSettings):
    # Application
    app_name: str = "Scout"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"  # development, testing, production
    
    # API Keys
    anthropic_api_key: str
    anthropic_model: str = "claude-3-5-haiku-20241022"
    openai_api_key: Optional[str] = None  # Fallback option
    
    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent
    data_dir: Path = base_dir / "data"
    profile_path: Path = data_dir / "profile.yaml"
    vector_db_path: Path = data_dir / "vectors"
    cache_dir: Path = data_dir / "cache"
    export_dir: Path = data_dir / "exports"
    prompts_dir: Path = base_dir / "prompts"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./data/scout.db"
    
    # Vector Store
    embedding_model: str = "all-MiniLM-L6-v2"
    chroma_persist: bool = True
    
    # Redis Cache (optional)
    redis_url: Optional[str] = None
    cache_ttl: int = 3600  # 1 hour
    
    # LLM Configuration
    llm_temperature: float = 0.3
    llm_max_tokens: int = 2000
    llm_timeout: int = 30
    
    # Cost Control
    max_daily_spend: float = 10.00
    max_monthly_spend: float = 50.00
    enable_cost_tracking: bool = True
    
    # Rate Limiting
    rate_limit_per_minute: int = 10
    rate_limit_per_hour: int = 100
    
    # Security
    secret_key: str  # Generate with: openssl rand -hex 32
    allowed_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Monitoring
    enable_telemetry: bool = False
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

settings = Settings()
```

#### `.env.example`
```bash
# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-here-generate-with-openssl

# Anthropic Claude API
ANTHROPIC_API_KEY=sk-ant-api03-xxx
ANTHROPIC_MODEL=claude-3-5-haiku-20241022

# Optional OpenAI Fallback
# OPENAI_API_KEY=sk-xxx

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/scout.db

# Redis (optional for production)
# REDIS_URL=redis://localhost:6379/0

# Cost Control
MAX_DAILY_SPEND=10.00
MAX_MONTHLY_SPEND=50.00
ENABLE_COST_TRACKING=true

# Rate Limiting
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=100

# Monitoring
LOG_LEVEL=INFO
ENABLE_TELEMETRY=false
```

#### `Makefile`
```makefile
.PHONY: help install dev test clean run docker-up docker-down

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	poetry install

dev: ## Run development server with hot reload
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests with coverage
	poetry run pytest tests/ -v --cov=app --cov-report=term-missing

test-unit: ## Run unit tests only
	poetry run pytest tests/unit/ -v

test-integration: ## Run integration tests
	poetry run pytest tests/integration/ -v

format: ## Format code with black and isort
	poetry run black app/ tests/
	poetry run isort app/ tests/

lint: ## Run linting checks
	poetry run flake8 app/ tests/
	poetry run mypy app/

clean: ## Clean cache and temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/

init-db: ## Initialize database
	poetry run python scripts/init_db.py

init-profile: ## Create example profile
	cp data/profile.example.yaml data/profile.yaml
	@echo "Profile created at data/profile.yaml - please edit with your information"

docker-build: ## Build Docker image
	docker build -f docker/Dockerfile -t scout:latest .

docker-up: ## Start services with docker-compose
	docker-compose -f docker/docker-compose.yml up -d

docker-down: ## Stop docker services
	docker-compose -f docker/docker-compose.yml down

docker-logs: ## View docker logs
	docker-compose -f docker/docker-compose.yml logs -f

setup: install init-profile init-db ## Complete development setup
	@echo "Setup complete! Edit data/profile.yaml and run 'make dev' to start"

check-llm: ## Test LLM connection
	poetry run python scripts/test_llm.py

export-requirements: ## Export requirements.txt
	poetry export -f requirements.txt --output requirements/base.txt --without-hashes
	poetry export -f requirements.txt --output requirements/dev.txt --with dev --without-hashes
```

#### `docker/Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements/base.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application
COPY app/ /app/app/
COPY prompts/ /app/prompts/
COPY data/profile.example.yaml /app/data/profile.example.yaml

# Create necessary directories
RUN mkdir -p /app/data/vectors /app/data/cache /app/data/exports

# Set environment
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `docker/docker-compose.yml`
```yaml
version: '3.8'

services:
  scout:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: scout-app
    ports:
      - "8000:8000"
    volumes:
      - ../data:/app/data
      - ../prompts:/app/prompts
    environment:
      - ENVIRONMENT=${ENVIRONMENT:-development}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DATABASE_URL=${DATABASE_URL:-sqlite+aiosqlite:///./data/scout.db}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - MAX_DAILY_SPEND=${MAX_DAILY_SPEND:-10.00}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    container_name: scout-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  redis-data:
```

#### `app/main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config.settings import settings
from app.config.logging import setup_logging
from app.api.routes import jobs, profile, generation, health
from app.core import collector, rinser, analyzer, creator, formatter
from app.services.llm import LLMService
from app.services.cost_tracker import CostTracker

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Lifespan manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Initialize services
    app.state.llm = LLMService()
    app.state.cost_tracker = CostTracker()
    
    # Initialize core modules
    app.state.collector = collector.Collector()
    await app.state.collector.initialize()
    
    app.state.rinser = rinser.Rinser(app.state.llm)
    app.state.analyzer = analyzer.Analyzer(app.state.collector)
    app.state.creator = creator.Creator(app.state.llm)
    app.state.formatter = formatter.Formatter()
    
    logger.info("All modules initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Scout")
    # Cleanup if needed

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["profile"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(generation.router, prefix="/api/v1/generate", tags=["generation"])

@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "ready"
    }
```

### Development Setup Instructions

```bash
# 1. Clone and setup
git clone <repo>
cd scout

# 2. Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# 3. Install dependencies
make install

# 4. Setup configuration
cp .env.example .env
# Edit .env with your API keys

# 5. Initialize profile
make init-profile
# Edit data/profile.yaml with your information

# 6. Initialize database
make init-db

# 7. Test LLM connection
make check-llm

# 8. Run development server
make dev

# 9. Access at http://localhost:8000
```

This structure provides:
- **Clear separation of concerns** with organized modules
- **Flexible configuration** via environment variables
- **Docker support** for easy deployment
- **Comprehensive testing structure**
- **Task automation** via Makefile
- **Cost tracking** built into the architecture
- **Scalable design** from PoC to production