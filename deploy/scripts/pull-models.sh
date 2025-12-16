#!/bin/bash
#
# Pull Ollama models for different deployment scenarios
#

set -e

echo "Scout Model Download Helper"
echo "==========================="
echo ""

case "$1" in
    minimal)
        echo "Pulling minimal model (qwen2.5:3b) - ~2GB"
        ollama pull qwen2.5:3b
        ;;
    standard)
        echo "Pulling standard model (qwen2.5:7b) - ~5GB"
        ollama pull qwen2.5:7b
        ;;
    full)
        echo "Pulling full model (qwen2.5:14b) - ~9GB"
        ollama pull qwen2.5:14b
        ;;
    all)
        echo "Pulling all models..."
        ollama pull qwen2.5:3b
        ollama pull qwen2.5:7b
        ollama pull qwen2.5:14b
        ;;
    *)
        echo "Usage: $0 {minimal|standard|full|all}"
        echo ""
        echo "  minimal  - qwen2.5:3b  (~2GB) - RPi, low-end systems"
        echo "  standard - qwen2.5:7b  (~5GB) - 8GB+ GPU"
        echo "  full     - qwen2.5:14b (~9GB) - 12GB+ GPU"
        echo "  all      - Download all models"
        exit 1
        ;;
esac

echo ""
echo "Done! Models are ready for use."
