#!/usr/bin/env python3
"""
scripts/check_ollama.py - Section 4.2
Utility to verify Ollama is ready for deployment
"""
import sys
sys.path.insert(0, '.')

import asyncio
from src.services.llm_service.providers import OllamaProvider

async def check_ollama():
    """Check if Ollama is running and models are available"""
    provider = OllamaProvider()

    try:
        print("Checking Ollama availability...")
        await provider.initialize()

        print("[PASS] Ollama is running")

        health = await provider.health_check()
        print(f"[PASS] Primary model: {health.get('model', 'N/A')}")
        print(f"[PASS] Fallback model: {health.get('fallback_model', 'N/A')}")
        print(f"[PASS] Available models: {health.get('available_models', 0)}")

        await provider.shutdown()
        return 0

    except Exception as e:
        print(f"[FAIL] Ollama check failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure Ollama is installed: curl -fsSL https://ollama.com/install.sh | sh")
        print("2. Start Ollama service: ollama serve")
        print("3. Pull required models:")
        print("   - ollama pull qwen2.5:3b")
        print("   - ollama pull gemma2:2b")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(check_ollama()))
