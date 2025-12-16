# Scout Portable Deployment

This directory contains everything needed to deploy Scout on different platforms for cross-platform benchmarking.

## Supported Platforms

| Platform | Script | Model | Expected Performance |
|----------|--------|-------|---------------------|
| Raspberry Pi 5 | `setup-rpi.sh` | qwen2.5:3b | ~2 tok/s, 5-8 min/job |
| Windows + NVIDIA GPU | `setup-windows.ps1` | qwen2.5:7b | ~40 tok/s, 30-60 sec/job |
| Linux + NVIDIA GPU | `setup-linux-gpu.sh` | qwen2.5:7b+ | ~50 tok/s, 20-40 sec/job |

## Quick Start

### 1. Clone and navigate to deploy directory

```bash
git clone <repository>
cd scout/deploy
```

### 2. Run platform-specific setup

**Raspberry Pi:**
```bash
chmod +x scripts/setup-rpi.sh
./scripts/setup-rpi.sh
```

**Windows (PowerShell as Administrator):**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\scripts\setup-windows.ps1
```

**Linux with NVIDIA GPU:**
```bash
chmod +x scripts/setup-linux-gpu.sh
./scripts/setup-linux-gpu.sh
```

### 3. Access Scout

Open http://localhost:8000 in your browser.

### 4. Run Benchmarks

```bash
python benchmark/run_benchmark.py
```

Results are saved to `benchmark/results/`.

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
nano .env
```

Key settings:
- `OLLAMA_MODEL` - Model to use (adjust based on available VRAM)
- `SCOUT_PORT` - Web interface port
- `SCOUT_LLM_TIMEOUT` - Timeout for LLM calls (increase for slow hardware)

## Docker Compose Profiles

```bash
# Scout only (Ollama running separately on host)
docker compose up -d scout

# Scout + Ollama CPU
docker compose --profile ollama-cpu up -d

# Scout + Ollama GPU (requires NVIDIA Container Toolkit)
docker compose --profile ollama-gpu up -d

# Full stack CPU
docker compose --profile full-cpu up -d

# Full stack GPU
docker compose --profile full-gpu up -d
```

## Benchmark Results

Benchmark results are JSON files with:
- System information (CPU, RAM, GPU)
- Per-job timing breakdowns
- Module-level metrics (rinser, analyzer, creator, formatter)
- Success rates and averages

Compare across platforms:
```bash
# View results
cat benchmark/results/benchmark_*.json | jq '.summary'
```

## Troubleshooting

### Ollama connection issues

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check from inside container
docker exec scout-app curl http://host.docker.internal:11434/api/tags
```

### GPU not detected

```bash
# Verify NVIDIA driver
nvidia-smi

# Verify container toolkit
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### Slow performance on RPi

- Ensure adequate cooling (active cooling recommended)
- Check thermal throttling: `vcgencmd measure_temp`
- Consider using swap if RAM limited: `sudo swapon --show`
