# Scout Quick Start Guide

Get Scout running on your development machine in minutes.

## Prerequisites

- Python 3.12+
- Git
- [Ollama](https://ollama.com) installed and running

## Setup (5 minutes)

### 1. Clone and Setup Environment

```bash
# Clone repository
git clone https://github.com/Cal-ly/scout-code.git
cd scout-code

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Ollama Models

```bash
# Ensure Ollama is running
ollama serve  # Or it may already be running as a service

# Pull required models (~3.5GB total)
ollama pull qwen2.5:3b    # Primary model
ollama pull gemma2:2b     # Fallback model

# Verify models installed
ollama list
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env if needed (defaults work for local development)
```

### 4. Run Scout

```bash
# Start the server
uvicorn src.web.main:app --host 0.0.0.0 --port 8000

# Or use make
make run
```

### 5. Access Scout

Open your browser to: **http://localhost:8000**

## Quick Test

1. Navigate to **Profiles** in the navbar
2. Create a new profile with your work experience
3. Go to the **Dashboard**
4. Paste a job posting and click **Apply**
5. Wait for pipeline completion (2-5 minutes locally)
6. Download your tailored CV and cover letter

## Development Commands

```bash
# Run tests
make test

# Run with coverage
make test-cov

# Format code
make format

# Lint code
make lint

# Type check
make typecheck
```

## Raspberry Pi Deployment

For deploying to Raspberry Pi 5, see:
- [Raspberry Pi 5 Deployment Guide](deployment/Raspberry_Pi_5_Deployment_Guide.md)

Quick deploy from Windows:
```powershell
.\scripts\deploy.ps1 -Message "Your commit message"
```

## Troubleshooting

### Ollama Connection Failed
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if not running
ollama serve
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Slow Generation
Local LLM inference is slower than cloud APIs:
- Qwen 2.5 3B: 2-4 tokens/second
- Full pipeline: 2-5 minutes (dev machine) / 15-30 minutes (Pi 5)

## Documentation

| Document | Purpose |
|----------|---------|
| [Current State](current_state/README.md) | Implementation documentation |
| [API Routes](current_state/api_routes.md) | REST endpoint reference |
| [PoC Scope](guides/Scout_PoC_Scope_Document.md) | Feature boundaries |

## Project Structure

```
scout-code/
├── src/
│   ├── modules/      # M1-M5: Collector, Rinser, Analyzer, Creator, Formatter
│   ├── services/     # S1-S4, S6, S8: LLM, Cache, VectorStore, etc.
│   └── web/          # FastAPI app, routes, templates
├── tests/            # 609+ tests
├── docs/             # Documentation
└── data/             # Runtime data (created automatically)
```

---

*For full documentation, see [docs/README.md](README.md)*
