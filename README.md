# Scout

**Intelligent Job Application Automation System**

Scout is a self-hosted AI-powered system that automates job discovery, semantic matching, and tailored application generation. Built for edge deployment on Raspberry Pi 5 using local LLM inference.

## Project Overview

Part of a project exploring generative AI with edge computing on Raspberry Pi 5, Scout demonstrates practical AI applications in job search automation and validates edge deployment capabilities.

### Key Features

- **Semantic Matching**: Vector-based similarity scoring between user profiles and job requirements
- **Tailored Content Generation**: AI-powered CV and cover letter creation
- **Local LLM Inference**: Runs entirely on-device using Ollama (Qwen 2.5 3B / Gemma 2 2B)
- **Profile Management**: Multi-profile support with SQLite persistence
- **PDF Generation**: Professional document output via xhtml2pdf
- **Edge-Ready**: Optimized for Raspberry Pi 5 deployment

## Architecture

### Processing Pipeline

```
Job Text → Rinser → Analyzer → Creator → Formatter → PDF Output
              ↓         ↓          ↓
          LLM Service (Ollama local inference)
              ↓         ↓          ↓
         Vector Store (ChromaDB) + Cache Service
```

### Core Modules

1. **Collector** (M1): Profile and job data management
2. **Rinser** (M2): Data normalization and extraction
3. **Analyzer** (M3): Semantic matching and gap analysis
4. **Creator** (M4): Tailored content generation
5. **Formatter** (M5): PDF document output

### Services

- **LLM Service** (S1): Ollama integration with fallback models
- **Metrics Service** (S2): Performance and reliability tracking
- **Cache Service** (S3): Memory + file-based caching
- **Vector Store** (S4): ChromaDB for semantic search
- **Pipeline Orchestrator** (S6): Sequential execution
- **Notification Service** (S8): In-app toast notifications

## Quick Start

### Prerequisites

- Python 3.12+
- Ollama with models installed:
  ```bash
  ollama pull qwen2.5:3b
  ollama pull gemma2:2b
  ```

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd scout-code
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or: venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env if needed (defaults work for local development)
   ```

5. **Start Ollama and run the application**
   ```bash
   ollama serve &  # Start Ollama if not running
   make run
   # Or: uvicorn src.web.main:app --reload --port 8000
   ```

6. **Access the web interface**
   Open http://localhost:8000 in your browser

## Project Structure

```
scout-code/
├── src/
│   ├── modules/           # Core processing modules (M1-M5)
│   ├── services/          # Supporting services (S1-S8)
│   └── web/               # FastAPI app, routes, templates
├── tests/                 # Test suite (~650 tests)
├── docs/
│   ├── current_state/     # Current implementation docs
│   ├── deployment/        # Raspberry Pi deployment guides
│   └── guides/            # Development guides
├── data/                  # Runtime data (profiles, cache)
└── pyproject.toml         # Project configuration
```

## Development

### Available Commands

```bash
make install       # Install dependencies
make test          # Run test suite
make test-cov      # Run tests with coverage
make lint          # Run ruff linter
make format        # Format code with black
make typecheck     # Run mypy type checker
make run           # Run development server
```

### Code Quality

All code follows:
- Type hints with mypy validation
- Ruff linting
- Black formatting
- ~770 passing tests

## Current Status

**Phase**: Complete (PoC)

- All 5 modules implemented and tested
- All services operational
- Web interface functional
- Raspberry Pi deployment validated
- ~770 tests passing

## Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12+, FastAPI, Pydantic v2 |
| LLM | Ollama (Qwen 2.5 3B, Gemma 2 2B) |
| Vector DB | ChromaDB, sentence-transformers |
| Database | SQLite (aiosqlite) |
| PDF Generation | xhtml2pdf, Jinja2 |
| Frontend | Vanilla JS, HTML/CSS |
| Testing | pytest, pytest-asyncio |

## Deployment

### Supported Platforms

1. **Local Development**: Full feature access, fast iteration
2. **Raspberry Pi 5**: Edge deployment target (8GB RAM recommended)
3. **Docker**: Portable containerized deployment

See [Deployment Guide](docs/deployment/Raspberry_Pi_5_Deployment_Guide.md) for detailed instructions.

## Documentation

- [Current Implementation](docs/current_state/README.md) - What's actually built
- [API Reference](docs/current_state/api_routes.md) - REST API documentation
- [User Guide](docs/deployment/User_Guide.md) - End-user instructions
- [Development Guide](docs/guides/Scout_Claude_Code_Development_Guide.md) - Development workflow

## License

AGPL 3.0 License - See LICENSE file for details

## Author

Carsten Lydeking
