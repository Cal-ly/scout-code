#!/bin/bash
#
# Scout Setup for Linux with NVIDIA GPU
#
# Usage:
#   ./setup-linux-gpu.sh              # Auto-detect GPU, use recommended model
#   ./setup-linux-gpu.sh --model qwen2.5:14b    # Specify model
#   ./setup-linux-gpu.sh --cpu-only   # Force CPU mode
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Defaults
MODEL="qwen2.5:7b"
CPU_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL="$2"
            shift 2
            ;;
        --cpu-only)
            CPU_ONLY=true
            MODEL="qwen2.5:3b"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}========================================"
echo "Scout Setup for Linux"
echo -e "========================================${NC}"
echo ""

# Check Docker
echo -e "${YELLOW}[1/6] Checking Docker...${NC}"
if command -v docker &> /dev/null; then
    echo -e "  ${GREEN}✓ Docker found: $(docker --version)${NC}"
else
    echo -e "  ${RED}✗ Docker not found. Please install Docker.${NC}"
    echo "    https://docs.docker.com/engine/install/"
    exit 1
fi

# Check Docker Compose
echo -e "${YELLOW}[2/6] Checking Docker Compose...${NC}"
if docker compose version &> /dev/null; then
    echo -e "  ${GREEN}✓ Docker Compose found${NC}"
else
    echo -e "  ${RED}✗ Docker Compose not found.${NC}"
    exit 1
fi

# Check GPU
echo -e "${YELLOW}[3/6] Checking GPU...${NC}"
if [ "$CPU_ONLY" = false ]; then
    if command -v nvidia-smi &> /dev/null; then
        GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "")
        if [ -n "$GPU_INFO" ]; then
            echo -e "  ${GREEN}✓ NVIDIA GPU detected: $GPU_INFO${NC}"

            # Check NVIDIA Container Toolkit
            if docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi &> /dev/null; then
                echo -e "  ${GREEN}✓ NVIDIA Container Toolkit working${NC}"
            else
                echo -e "  ${YELLOW}! NVIDIA Container Toolkit not configured${NC}"
                echo "    Installing NVIDIA Container Toolkit..."

                # Install NVIDIA Container Toolkit
                distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
                curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
                curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
                    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
                    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
                sudo apt-get update
                sudo apt-get install -y nvidia-container-toolkit
                sudo nvidia-ctk runtime configure --runtime=docker
                sudo systemctl restart docker

                echo -e "  ${GREEN}✓ NVIDIA Container Toolkit installed${NC}"
            fi

            # Recommend model based on VRAM
            VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
            if [ "$VRAM" -ge 20000 ]; then
                RECOMMENDED="qwen2.5:32b"
            elif [ "$VRAM" -ge 12000 ]; then
                RECOMMENDED="qwen2.5:14b"
            elif [ "$VRAM" -ge 8000 ]; then
                RECOMMENDED="qwen2.5:7b"
            else
                RECOMMENDED="qwen2.5:3b"
            fi
            echo -e "  ${CYAN}  Recommended model for ${VRAM}MB VRAM: $RECOMMENDED${NC}"

        else
            echo -e "  ${YELLOW}! No NVIDIA GPU detected, using CPU mode${NC}"
            CPU_ONLY=true
            MODEL="qwen2.5:3b"
        fi
    else
        echo -e "  ${YELLOW}! nvidia-smi not found, using CPU mode${NC}"
        CPU_ONLY=true
        MODEL="qwen2.5:3b"
    fi
else
    echo -e "  - CPU-only mode selected"
fi

# Install Ollama
echo -e "${YELLOW}[4/6] Setting up Ollama...${NC}"
if ! command -v ollama &> /dev/null; then
    echo "  Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi
echo -e "  ${GREEN}✓ Ollama installed${NC}"

# Start Ollama and pull model
echo -e "${YELLOW}[5/6] Pulling model: $MODEL...${NC}"
# Ensure Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &> /dev/null &
    sleep 3
fi

ollama pull "$MODEL"
echo -e "  ${GREEN}✓ Model ready: $MODEL${NC}"

# Create .env file
echo -e "${YELLOW}[6/6] Configuring Scout...${NC}"
cat > .env << EOF
# Scout Configuration - Linux
PLATFORM=linux-gpu
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=$MODEL
SCOUT_PORT=8000
SCOUT_LOG_LEVEL=INFO
BENCHMARK_RUNS=3
EOF
echo -e "  ${GREEN}✓ Configuration saved to .env${NC}"

# Start Scout
echo ""
echo -e "${CYAN}========================================"
echo "Setup complete! Starting Scout..."
echo -e "========================================${NC}"
echo ""

if [ "$CPU_ONLY" = true ]; then
    docker compose up -d scout
else
    docker compose --profile gpu up -d scout
fi

echo ""
echo -e "${GREEN}Scout is starting. Access the web interface at:${NC}"
echo "  http://localhost:8000"
echo ""
echo -e "To run benchmarks:"
echo "  python benchmark/run_benchmark.py"
echo ""
echo -e "To view logs:"
echo "  docker compose logs -f scout"
