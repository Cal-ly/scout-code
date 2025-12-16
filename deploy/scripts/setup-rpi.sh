#!/bin/bash
#
# Scout Setup for Raspberry Pi 5
#
# Optimized for:
#   - Raspberry Pi 5 (8GB or 16GB)
#   - Ubuntu Server 24.04 or Raspberry Pi OS (64-bit)
#   - CPU-only inference with qwen2.5:3b
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

MODEL="qwen2.5:3b"

echo -e "${CYAN}========================================"
echo "Scout Setup for Raspberry Pi 5"
echo -e "========================================${NC}"
echo ""

# Check we're on ARM64
echo -e "${YELLOW}[1/5] Checking platform...${NC}"
ARCH=$(uname -m)
if [[ "$ARCH" != "aarch64" ]]; then
    echo -e "  ${RED}✗ This script is for ARM64 (aarch64). Detected: $ARCH${NC}"
    exit 1
fi

# Check memory
MEM_GB=$(free -g | awk '/^Mem:/{print $2}')
echo -e "  ${GREEN}✓ Platform: Raspberry Pi (ARM64)${NC}"
echo -e "  ${GREEN}✓ Memory: ${MEM_GB}GB${NC}"

if [ "$MEM_GB" -lt 8 ]; then
    echo -e "  ${YELLOW}! Less than 8GB RAM. Performance may be limited.${NC}"
fi

# Check Docker
echo -e "${YELLOW}[2/5] Checking Docker...${NC}"
if command -v docker &> /dev/null; then
    echo -e "  ${GREEN}✓ Docker found${NC}"
else
    echo "  Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo -e "  ${GREEN}✓ Docker installed${NC}"
    echo -e "  ${YELLOW}! You may need to log out and back in for docker permissions${NC}"
fi

# Install Ollama
echo -e "${YELLOW}[3/5] Setting up Ollama...${NC}"
if ! command -v ollama &> /dev/null; then
    echo "  Installing Ollama for ARM64..."
    curl -fsSL https://ollama.com/install.sh | sh
fi
echo -e "  ${GREEN}✓ Ollama installed${NC}"

# Pull model
echo -e "${YELLOW}[4/5] Pulling model: $MODEL...${NC}"
echo "  This will take several minutes on RPi..."
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &> /dev/null &
    sleep 5
fi
ollama pull "$MODEL"
echo -e "  ${GREEN}✓ Model ready${NC}"

# Configure Scout
echo -e "${YELLOW}[5/5] Configuring Scout...${NC}"
cat > .env << EOF
# Scout Configuration - Raspberry Pi 5
PLATFORM=rpi
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=$MODEL
SCOUT_PORT=8000
SCOUT_LOG_LEVEL=INFO
SCOUT_LLM_TIMEOUT=600
BENCHMARK_RUNS=3
EOF
echo -e "  ${GREEN}✓ Configuration saved${NC}"

# Build and start
echo ""
echo -e "${CYAN}========================================"
echo "Setup complete! Starting Scout..."
echo -e "========================================${NC}"
echo ""

docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d scout

echo ""
echo -e "${GREEN}Scout is starting. Access the web interface at:${NC}"
echo "  http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo -e "Performance notes for Raspberry Pi:"
echo "  - Expected inference speed: 1.5-2.5 tokens/second"
echo "  - Full pipeline time: 5-10 minutes"
echo "  - Monitor temperature: vcgencmd measure_temp"
echo ""
echo -e "To run benchmarks:"
echo "  python benchmark/run_benchmark.py"
