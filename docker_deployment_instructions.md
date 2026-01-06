# Docker Deployment Instructions for Scout

**Target**: Create a root-level Dockerfile for the Scout application  
**Context**: The docker-compose.yml references a Dockerfile that doesn't exist

---

## Current State

- `deploy/docker-compose.yml` exists and references `Dockerfile` in root context
- `deploy/benchmark/Dockerfile` exists (for benchmark runner only)
- **Root `Dockerfile` is MISSING** - needs to be created

---

## Task: Create Root Dockerfile

Create a `Dockerfile` in the project root with the following requirements:

### Requirements

1. **Base Image**: `python:3.12-slim` (multi-arch, works on ARM/RPI5)

2. **Working Directory**: `/app`

3. **Dependencies to install**:
   - System packages: `build-essential`, `curl` (for healthcheck)
   - Python packages from `requirements.txt`

4. **Files to copy**:
   - `requirements.txt`
   - `src/` directory
   - `data/templates/` directory (if exists, for PDF templates)

5. **Exposed port**: `8000`

6. **Entry point**: 
   ```bash
   uvicorn src.web.main:app --host 0.0.0.0 --port 8000
   ```

7. **Health check**:
   ```
   GET /api/v1/health
   ```

8. **Environment variables** (with sensible defaults):
   - `OLLAMA_HOST=http://host.docker.internal:11434`
   - `OLLAMA_MODEL=qwen2.5:3b`
   - `SCOUT_LOG_LEVEL=INFO`
   - `SCOUT_ENVIRONMENT=production`

### Reference: Existing benchmark Dockerfile

From `deploy/benchmark/Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Command will be overridden by docker-compose
CMD ["python", "-m", "pytest"]
```

### Expected Dockerfile Structure

```dockerfile
# Base image - multi-arch for RPI5 compatibility
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ ./src/

# Copy templates if they exist
COPY data/templates/ ./data/templates/ 2>/dev/null || true

# Create directories for persistent data
RUN mkdir -p /app/data /app/outputs

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OLLAMA_HOST=http://host.docker.internal:11434 \
    OLLAMA_MODEL=qwen2.5:3b \
    SCOUT_LOG_LEVEL=INFO \
    SCOUT_ENVIRONMENT=production

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run application
CMD ["uvicorn", "src.web.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Verification

After creating the Dockerfile, verify:

1. **Build succeeds**:
   ```bash
   docker build -t scout:latest .
   ```

2. **Compose works**:
   ```bash
   cd deploy && docker-compose up scout
   ```

3. **Health check passes**:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

---

## Notes for ARM/RPI5 Deployment

- The `python:3.12-slim` image is multi-arch and works on ARM64
- Ollama must be installed separately on the RPI5 host or run as sidecar container
- Consider using `--platform linux/arm64` for explicit ARM builds
- Memory constraints: Keep container memory limit around 4-6GB to leave room for Ollama

---

## Integration with Existing docker-compose.yml

The existing `deploy/docker-compose.yml` already references:
```yaml
scout:
  build:
    context: ..
    dockerfile: Dockerfile
```

Once the root Dockerfile is created, the compose file should work without modification.
