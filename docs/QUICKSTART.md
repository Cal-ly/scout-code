# Scout Quick Start Guide

Get Scout running locally in 5 minutes.

---

## Prerequisites

- Python 3.11 or 3.12
- [Ollama](https://ollama.ai/) installed and running
- 8GB+ RAM recommended (16GB for comfortable operation)

---

## Setup Steps

### 1. Clone and Setup Virtual Environment

```bash
git clone https://github.com/yourusername/scout-code.git
cd scout-code

# Create virtual environment
python -m venv venv

# Activate (Linux/macOS)
source venv/bin/activate

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Ollama Models

```bash
# Ensure Ollama is running
ollama serve &  # or start Ollama app

# Pull required models
ollama pull qwen2.5:3b    # Primary model (~2GB)
ollama pull gemma2:2b     # Fallback model (~1.5GB)

# Verify models
ollama list
```

### 4. Create Your Profile

```bash
# Copy example profile
cp docs/test_data/my_test_profile.yaml data/profile.yaml

# Edit with your information
nano data/profile.yaml  # or your preferred editor
```

### 5. Start Scout

```bash
uvicorn src.web.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Access the Interface

Open your browser to: **http://localhost:8000**

---

## Verify Installation

```bash
# Check health endpoint
curl http://localhost:8000/api/v1/health

# Expected response:
# {"status": "healthy", "version": "0.1.0", "services": {...}}

# Run quick diagnostics
curl http://localhost:8000/api/v1/diagnostics
```

---

## Quick Test

1. Navigate to http://localhost:8000
2. Paste a job posting into the text area
3. Click "Analyze" for quick compatibility score
4. Click "Generate Application" for full CV + cover letter

---

## Troubleshooting

### Ollama Not Connected
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve
```

### Model Not Found
```bash
# List available models
ollama list

# Pull missing model
ollama pull qwen2.5:3b
```

### Import Errors
```bash
# Ensure you are in the virtual environment
which python  # Should show venv path

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## Next Steps

- **Customize Profile**: Edit `data/profile.yaml` with your details
- **API Reference**: See `docs/current_state/api_routes.md`
- **Deployment**: See `docs/deployment/Raspberry_Pi_5_Deployment_Guide.md`

---

*For detailed documentation, see [docs/README.md](README.md)*
