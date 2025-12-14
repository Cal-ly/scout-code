# Deployment TODOs

## Overview
Scout is deployed on Raspberry Pi 5 with local Ollama LLM inference. This document tracks deployment-related tasks and optimizations.

**Status**: Deployed and operational

---

## Current Deployment

| Component | Status | Notes |
|-----------|--------|-------|
| Scout Application | Running | systemd service |
| Ollama Server | Running | Local LLM inference |
| Qwen 2.5 3B | Loaded | Primary model |
| Gemma 2 2B | Available | Fallback model |
| ChromaDB | Operational | Vector storage |
| WeasyPrint | Operational | PDF generation |

### Access Points
- **Web Interface**: `http://<pi-ip>:8000`
- **API Docs**: `http://<pi-ip>:8000/docs`
- **Ollama API**: `http://<pi-ip>:11434`

---

## Outstanding Tasks

### High Priority

- [ ] **Service Auto-Restart**: Ensure services restart on failure
  - **Current**: systemd may not restart on OOM
  - **Location**: `/etc/systemd/system/scout.service`
  - **Suggestion**: Add `Restart=always` and `RestartSec=10`

- [ ] **Log Rotation**: Application logs can grow large
  - **Current**: Logs to stdout (journald)
  - **Suggestion**: Configure journald max size or add logrotate

### Medium Priority

- [ ] **Memory Monitoring**: Alert on high memory usage
  - **Current**: Pi has 8GB, LLM uses ~4GB
  - **Suggestion**: Simple cron script to check free memory

- [ ] **Health Check Endpoint**: Enhanced monitoring
  - **Current**: `/health` returns basic status
  - **Enhancement**: Add LLM health, disk space, memory

- [ ] **Backup Strategy**: Profile and output backup
  - **Current**: No automated backups
  - **Suggestion**: Daily rsync of `data/` directory

### Low Priority

- [ ] **Performance Metrics Dashboard**: Visual monitoring
  - **Current**: Metrics in logs only
  - **Suggestion**: Simple grafana or just a stats page

- [ ] **Remote Access**: Secure access from outside network
  - **Current**: Local network only
  - **Options**: Tailscale, WireGuard, SSH tunnel

---

## Performance Optimization Notes

### Current Performance (Pi 5, 8GB RAM)

| Metric | Value | Notes |
|--------|-------|-------|
| Token Rate (Qwen) | 2-4 tok/s | Acceptable |
| Token Rate (Gemma) | 4-6 tok/s | Faster, smaller model |
| Full Pipeline | 4-8 min | Depends on job complexity |
| Memory Usage | ~4GB active | +2GB Ollama overhead |
| Disk Usage | ~8GB | Models + ChromaDB |

### Optimization Opportunities

1. **Model Quantization**: Qwen 3B Q4 is already quantized; further reduction possible but quality tradeoff

2. **Batch Processing**: Process multiple jobs overnight when time isn't critical

3. **Caching**: Already implemented; cache hit rate improves repeat queries

4. **SSD Storage**: If using SD card, consider USB3 SSD for ChromaDB

---

## Deployment Documentation

### Key Files
- `docs/deployment/Raspberry_Pi_5_Deployment_Guide.md` - Step-by-step
- `docs/deployment/Deployment_PreFlight_Verification.md` - Checklist
- `docs/deployment/Performance_Benchmarks.md` - Metrics
- `docs/deployment/User_Guide.md` - End-user docs

### Quick Commands

```bash
# Check service status
sudo systemctl status scout

# View logs
sudo journalctl -u scout -f

# Restart service
sudo systemctl restart scout

# Check Ollama
curl http://localhost:11434/api/tags

# Check Scout health
curl http://localhost:8000/health
```

---

## Troubleshooting Reference

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| LLM timeout | Model loading | Wait 30-60s on first request |
| OOM kill | Large job + full memory | Restart, use smaller model |
| PDF blank | WeasyPrint dependency | Check cairo/pango libs |
| ChromaDB lock | Previous crash | Remove `.lock` file |
| Slow performance | Thermal throttling | Improve cooling |

### Recovery Procedure

1. Check service status: `systemctl status scout`
2. Check logs: `journalctl -u scout -n 100`
3. Check Ollama: `systemctl status ollama`
4. Restart if needed: `systemctl restart scout`
5. If persistent, check disk space and memory

---

## Deferred Infrastructure

- [-] **Docker Deployment**: Direct install simpler for Pi
- [-] **Load Balancing**: Single instance sufficient for PoC
- [-] **Cloud Fallback**: Local-only per scope document
- [-] **Database Backup Service**: Manual backup sufficient

---

*Last updated: December 14, 2025*
