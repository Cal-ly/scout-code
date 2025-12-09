# Scout

**Intelligent Job Application Automation System**

Scout is a self-hosted AI-powered system that automates job discovery, semantic matching, and tailored application generation while maintaining strategic user control through four interaction gates.

## 🎯 Project Overview

Part of a bachelor's thesis exploring generative AI with edge computing on Raspberry Pi 5, Scout demonstrates practical AI applications in job search automation and validates edge deployment capabilities.

### Key Features
- **Intelligent Job Discovery**: Automated scanning of job platforms (LinkedIn, Jobindex.dk)
- **Semantic Matching**: Vector-based similarity scoring between user profiles and job requirements
- **Tailored Content Generation**: AI-powered CV, resume, and cover letter creation
- **Strategic Control**: Four user interaction gates for quality assurance
- **Cost Optimization**: Built-in budget controls and multi-tier caching
- **Edge-Ready**: Designed for deployment from Raspberry Pi 5 to cloud infrastructure

## 🏗️ Architecture

### Three-Layer Design
- **Data Layer**: User profiles, job database, template library
- **Processing Layer**: Discovery, matching, and management pipelines
- **Interface Layer**: Dashboard, configuration, and notifications

### Core Modules
1. **Collector**: Job discovery and data extraction
2. **Rinser**: Data normalization and quality enhancement
3. **Analyzer**: Semantic matching and scoring
4. **Creator**: Tailored content generation
5. **Formatter**: Multi-format document output

### Services
- LLM Service (Claude 3.5 Haiku)
- Cost Tracker
- Cache Service (Redis + Vector Store)
- Vector Store Service (ChromaDB)
- Pipeline Orchestrator
- Content Optimizer
- Notification Service

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Redis (for caching)
- Anthropic API key

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd scout-code
```

2. **Create and activate virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements-dev.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

5. **Run the application**
```bash
make run
# Or: uvicorn src.web.main:app --reload
```

## 📁 Project Structure

```
scout-code/
├── src/
│   ├── modules/          # Core processing modules
│   │   ├── collector/    # Job discovery
│   │   ├── rinser/       # Data normalization
│   │   ├── analyzer/     # Semantic matching
│   │   ├── creator/      # Content generation
│   │   └── formatter/    # Document output
│   ├── services/         # Supporting services
│   │   ├── llm_service/
│   │   ├── cost_tracker/
│   │   ├── cache_service/
│   │   └── vector_store/
│   └── web/              # Web interface
├── tests/                # Test suite
├── config/               # Configuration files
├── docs/                 # Documentation
└── data/                 # Runtime data (created automatically)
```

## 🧪 Development

### Available Commands
```bash
make install       # Install core dependencies
make install-dev   # Install development dependencies
make test          # Run test suite
make test-cov      # Run tests with coverage
make lint          # Run linter
make format        # Format code
make typecheck     # Run type checker
make clean         # Remove cache files
make run           # Run application
```

### Development Workflow
1. Ensure virtual environment is activated
2. Make changes to code
3. Run `make format` and `make lint`
4. Run `make test` to verify functionality
5. Commit changes

## 🎓 Project Context

This project serves dual purposes:
1. **Practical Application**: Demonstrating AI-powered job search automation
2. **Academic Research**: Validating edge deployment capabilities for generative AI

Target users: IT professionals seeking employment
Focus platforms: LinkedIn, Jobindex.dk
Output formats: CV, resume, cover letter

## 📊 Current Status

**Phase**: Initial Setup & Foundation
- ✅ Project structure established
- ✅ Core dependencies configured
- ✅ Development environment ready
- 🔄 PoC implementation in progress

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.12
- **LLM**: Anthropic Claude 3.5 Haiku
- **Vector DB**: ChromaDB with sentence-transformers
- **Caching**: Redis
- **Database**: SQLite (via aiosqlite)
- **Document Generation**: WeasyPrint, python-docx
- **Testing**: pytest, pytest-asyncio

## 🚀 Deployment Tiers

1. **Local Development**: Minimal cost, full feature access
2. **Hetzner Cloud VPS**: Production-ready deployment
3. **Raspberry Pi 5**: Edge deployment demonstration (portfolio piece)

## 📝 License

MIT License - See LICENSE file for details

## 👤 Author

Carsten - Bachelor's Thesis Project

## 🔗 Related Documentation

See `/docs` directory for detailed module specifications and architecture decisions.
