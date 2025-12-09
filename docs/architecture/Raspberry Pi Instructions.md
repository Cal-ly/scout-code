---
updated: 2025-10-05, 09:54
---
# Scout PoC - Raspberry Pi 5 Deployment Guide

## Executive Summary

This guide provides step-by-step instructions for deploying Scout on a Raspberry Pi 5 (8GB) as a PoC showcase environment. The deployment balances cost-efficiency with production-like infrastructure, demonstrating Scout's ability to run on edge hardware while remaining cloud-ready.

**Deployment Profile:**
- **Target**: Portfolio showcase, stakeholder demos, local development
- **Expected Load**: 1-5 concurrent users
- **Uptime Target**: 95% (development/demo environment)
- **Data Scale**: <5,000 job postings in vector store
- **Network**: Local network with optional VPN access
- **Total Setup Time**: 3-6 hours (including downloads)

---

## Phase 1: Hardware Preparation

### Required Hardware

**Essential:**
- Raspberry Pi 5 (8GB RAM) - $80
- Official Pi 5 Power Supply (27W USB-C PD) - $12
- High-quality microSD card (32GB, A2 rated minimum) - $10
- **USB 3.0 SSD (128GB minimum, 256GB recommended)** - $30-50
- Active cooling case (or official Active Cooler) - $10-15
- Ethernet cable (Cat6) - $5

**Optional but Recommended:**
- USB SD card reader (for flashing)
- HDMI cable + monitor (initial setup only)
- USB keyboard (initial setup only)

**Total Cost**: ~$150-180

### Hardware Assembly

1. **Install Active Cooling**
   ```bash
   # Why: Pi 5 can thermal throttle under sustained load
   # WeasyPrint PDF generation and sentence-transformers are CPU intensive
   ```
   - Mount heatsink with thermal pads on CPU
   - Connect 4-pin fan to designated header
   - Verify fan spins on boot (should be audible)

2. **Prepare External SSD**
   ```bash
   # Why: SD cards fail under database write patterns
   # ChromaDB + SQLite need reliable storage with good random I/O
   ```
   - Connect SSD to blue USB 3.0 port (left side, closest to USB-C power)
   - DO NOT use USB 2.0 ports (black) - significant performance penalty
   - If SSD has activity LED, position for visibility

3. **Initial Physical Setup**
   - Position Pi in ventilated area (not enclosed)
   - Ensure SSD cable isn't under tension
   - Connect Ethernet (preferred over WiFi for stability)
   - DO NOT power on yet

---

## Phase 2: Operating System Installation

### OS Preparation (on Development Machine)

1. **Download Raspberry Pi Imager**
   ```bash
   # On your Arch Linux system
   yay -S rpi-imager
   # Or download from: https://www.raspberrypi.com/software/
   ```

2. **Flash Raspberry Pi OS**
   ```
   Imager Settings:
   - OS: Raspberry Pi OS Lite (64-bit) - Debian Bookworm
   - Storage: Your microSD card
   - Advanced Options (Gear icon):
     ✅ Set hostname: scout-pi.local
     ✅ Enable SSH: Use password authentication
     ✅ Set username: scout
     ✅ Set password: [strong password]
     ✅ Configure WiFi: [optional backup connectivity]
     ✅ Set locale: Europe/Copenhagen, da_DK
     ✅ Keyboard layout: us
   ```

3. **Why Lite Edition?**
   - No desktop environment = more RAM for Scout
   - Faster boot time (~15s vs 45s)
   - Reduced attack surface (no X11, no display manager)
   - Lower power consumption and heat generation

### First Boot Configuration

1. **Initial Connection**
   ```bash
   # Wait 60-90 seconds after power on
   # Find Pi on network
   nmap -sn 192.168.1.0/24 | grep -A 2 "Raspberry"
   # Or use: ping scout-pi.local
   
   # SSH into Pi
   ssh scout@scout-pi.local
   # Accept fingerprint, enter password
   ```

2. **System Update**
   ```bash
   # Update package lists and system
   sudo apt update && sudo apt upgrade -y
   
   # Install essential utilities
   sudo apt install -y \
     vim \
     htop \
     git \
     curl \
     ufw \
     fail2ban \
     unattended-upgrades \
     tmux \
     ncdu
   
   # Reboot to apply kernel updates
   sudo reboot
   ```

3. **Configure Automatic Updates**
   ```bash
   # Reconnect after reboot
   ssh scout@scout-pi.local
   
   # Enable unattended security updates
   sudo dpkg-reconfigure -plow unattended-upgrades
   # Select: Yes
   
   # Verify configuration
   cat /etc/apt/apt.conf.d/50unattended-upgrades
   # Should show: Unattended-Upgrade::Automatic-Reboot "false";
   ```

---

## Phase 3: External SSD Configuration

### Why External SSD Strategy

**Architecture Decision**: Use SD card for OS, SSD for application data
- **Rationale**: 
  - SD card failures don't lose critical data (profile, vectors, exports)
  - SSD replacement doesn't require OS reinstall
  - Easier backup strategy (only mount point needs backing up)
  - Simpler disaster recovery (new Pi + SSD = restored system)

### SSD Setup

1. **Identify SSD Device**
   ```bash
   # List all block devices
   lsblk
   
   # Expected output:
   # NAME        MAJ:MIN RM   SIZE RO TYPE MOUNTPOINTS
   # mmcblk0     179:0    0  29.7G  0 disk 
   # ├─mmcblk0p1 179:1    0   512M  0 part /boot/firmware
   # └─mmcblk0p2 179:2    0  29.2G  0 part /
   # sda           8:0    0 238.5G  0 disk  <- Your SSD
   
   # Verify it's USB 3.0 (should show 5000M or 10000M)
   lsusb -t
   ```

2. **Partition and Format SSD**
   ```bash
   # ⚠️ VERIFY you're targeting correct device (sda, not mmcblk0)
   # This WILL ERASE ALL DATA on the drive
   
   # Create single partition
   sudo fdisk /dev/sda
   # Commands in fdisk:
   # n (new partition)
   # p (primary)
   # 1 (partition number)
   # [Enter] (default first sector)
   # [Enter] (default last sector - use whole disk)
   # w (write and exit)
   
   # Format as ext4 with optimizations for database workloads
   sudo mkfs.ext4 -L SCOUT_DATA \
     -O ^has_journal \
     -E lazy_itable_init=0,lazy_journal_init=0 \
     /dev/sda1
   
   # Why no journal? SSDs handle power loss better than spinning disks
   # Journaling adds write amplification, reduces SSD lifespan
   # Scout data is recoverable from backups if corruption occurs
   ```

3. **Configure Auto-Mount**
   ```bash
   # Get UUID of partition
   sudo blkid /dev/sda1
   # Copy the UUID value (e.g., 1234abcd-5678-efgh-9012-ijklmnopqrst)
   
   # Create mount point
   sudo mkdir -p /mnt/scout-data
   sudo chown scout:scout /mnt/scout-data
   
   # Add to fstab for automatic mounting
   echo "UUID=YOUR_UUID_HERE /mnt/scout-data ext4 defaults,noatime 0 2" | \
     sudo tee -a /etc/fstab
   
   # Mount and verify
   sudo mount -a
   df -h /mnt/scout-data
   
   # Should show your SSD mounted at /mnt/scout-data
   ```

4. **Test SSD Performance**
   ```bash
   # Write speed test (should be >200 MB/s for USB 3.0 SSD)
   dd if=/dev/zero of=/mnt/scout-data/test.img bs=1M count=1024 oflag=direct
   
   # Read speed test
   dd if=/mnt/scout-data/test.img of=/dev/null bs=1M iflag=direct
   
   # Cleanup
   rm /mnt/scout-data/test.img
   
   # If speeds < 100 MB/s, verify SSD is in blue USB 3.0 port
   ```

---

## Phase 4: Docker Installation (ARM64)

### Docker Engine Setup

1. **Install Docker from Official Repository**
   ```bash
   # Add Docker's official GPG key
   sudo install -m 0755 -d /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/debian/gpg | \
     sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   sudo chmod a+r /etc/apt/keyrings/docker.gpg
   
   # Add Docker repository
   echo \
     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
     https://download.docker.com/linux/debian \
     $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
     sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
   
   # Install Docker packages
   sudo apt update
   sudo apt install -y \
     docker-ce \
     docker-ce-cli \
     containerd.io \
     docker-buildx-plugin \
     docker-compose-plugin
   
   # Verify installation
   docker --version  # Should show 24.x or newer
   docker compose version  # Should show 2.x or newer
   ```

2. **Configure Docker for scout User**
   ```bash
   # Add scout user to docker group
   sudo usermod -aG docker scout
   
   # Apply group membership (logout/login or use newgrp)
   newgrp docker
   
   # Test Docker without sudo
   docker run --rm hello-world
   # Should see: "Hello from Docker!"
   ```

3. **Optimize Docker for Pi**
   ```bash
   # Create Docker daemon config
   sudo tee /etc/docker/daemon.json > /dev/null <<EOF
   {
     "log-driver": "json-file",
     "log-opts": {
       "max-size": "10m",
       "max-file": "3"
     },
     "storage-driver": "overlay2",
     "default-address-pools": [
       {
         "base": "172.17.0.0/16",
         "size": 24
       }
     ]
   }
   EOF
   
   # Restart Docker to apply changes
   sudo systemctl restart docker
   
   # Verify configuration
   docker info | grep -A 5 "Storage Driver"
   ```

4. **Why These Optimizations?**
   - **Log rotation**: Prevents logs from filling SD card
   - **overlay2**: Better performance than default on ARM
   - **Address pools**: Explicit network configuration prevents conflicts

---

## Phase 5: Scout Application Deployment

### Project Setup

1. **Create Project Directory Structure**
   ```bash
   # Application code goes on SD card (small, doesn't change often)
   mkdir -p ~/scout
   cd ~/scout
   
   # Data directory on SSD (large, write-heavy)
   mkdir -p /mnt/scout-data/{vectors,cache,exports,backups}
   
   # Create symbolic link for seamless integration
   ln -s /mnt/scout-data ~/scout/data
   ```

2. **Clone Scout Repository**
   ```bash
   # Replace with your actual repository
   git clone https://github.com/yourusername/scout.git ~/scout
   cd ~/scout
   
   # Verify project structure
   ls -la
   # Should see: app/ docker/ prompts/ requirements/ etc.
   ```

3. **Create Environment Configuration**
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Edit with your configuration
   vim .env
   ```

   **Critical `.env` settings for Pi:**
   ```bash
   # Application
   ENVIRONMENT=production
   DEBUG=false
   SECRET_KEY=$(openssl rand -hex 32)
   
   # Anthropic API
   ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE
   ANTHROPIC_MODEL=claude-3-5-haiku-20241022
   
   # Paths - Note: Using absolute paths for Docker volumes
   DATA_DIR=/mnt/scout-data
   PROFILE_PATH=/mnt/scout-data/profile.yaml
   VECTOR_DB_PATH=/mnt/scout-data/vectors
   CACHE_DIR=/mnt/scout-data/cache
   EXPORT_DIR=/mnt/scout-data/exports
   
   # Database
   DATABASE_URL=sqlite+aiosqlite:////mnt/scout-data/scout.db
   
   # Cost Control (important for API budget)
   MAX_DAILY_SPEND=5.00
   MAX_MONTHLY_SPEND=50.00
   ENABLE_COST_TRACKING=true
   
   # Rate Limiting
   RATE_LIMIT_PER_MINUTE=10
   RATE_LIMIT_PER_HOUR=50
   
   # Monitoring
   LOG_LEVEL=INFO
   ENABLE_TELEMETRY=false
   ```

4. **Create Pi-Optimized Docker Compose**
   ```bash
   # Create new docker-compose override for Pi
   vim docker/docker-compose.pi.yml
   ```

   ```yaml
   version: '3.8'
   
   services:
     scout:
       build:
         context: ..
         dockerfile: docker/Dockerfile.pi
         args:
           - BUILDPLATFORM=linux/arm64
       container_name: scout-app
       restart: unless-stopped
       
       ports:
         - "8000:8000"
       
       volumes:
         # Mount SSD data directory
         - /mnt/scout-data:/app/data
         - ../prompts:/app/prompts:ro
       
       environment:
         - ENVIRONMENT=${ENVIRONMENT:-production}
         - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
         - DATABASE_URL=${DATABASE_URL}
         - LOG_LEVEL=${LOG_LEVEL:-INFO}
         - MAX_DAILY_SPEND=${MAX_DAILY_SPEND}
         - PYTHONUNBUFFERED=1
       
       # Resource limits for Pi
       deploy:
         resources:
           limits:
             cpus: '3.0'
             memory: 4G
           reservations:
             cpus: '1.0'
             memory: 1G
       
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
         interval: 30s
         timeout: 10s
         retries: 3
         start_period: 40s
       
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "3"
   
     redis:
       image: redis:7-alpine
       container_name: scout-redis
       restart: unless-stopped
       
       ports:
         - "127.0.0.1:6379:6379"
       
       volumes:
         - /mnt/scout-data/redis:/data
       
       command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
       
       deploy:
         resources:
           limits:
             cpus: '0.5'
             memory: 512M
           reservations:
             memory: 128M
   ```

5. **Create ARM64-Optimized Dockerfile**
   ```bash
   vim docker/Dockerfile.pi
   ```

   ```dockerfile
   # Multi-stage build for smaller image
   FROM python:3.11-slim-bookworm AS builder
   
   WORKDIR /build
   
   # Install build dependencies
   RUN apt-get update && apt-get install -y --no-install-recommends \
       gcc \
       g++ \
       git \
       && rm -rf /var/lib/apt/lists/*
   
   # Copy requirements
   COPY requirements/base.txt /build/requirements.txt
   
   # Install Python dependencies
   RUN pip install --no-cache-dir --user -r requirements.txt
   
   # Runtime stage
   FROM python:3.11-slim-bookworm
   
   WORKDIR /app
   
   # Install runtime dependencies for WeasyPrint
   RUN apt-get update && apt-get install -y --no-install-recommends \
       libpango-1.0-0 \
       libpangocairo-1.0-0 \
       libgdk-pixbuf2.0-0 \
       libffi-dev \
       shared-mime-info \
       curl \
       && rm -rf /var/lib/apt/lists/*
   
   # Copy Python packages from builder
   COPY --from=builder /root/.local /root/.local
   
   # Make sure scripts in .local are usable
   ENV PATH=/root/.local/bin:$PATH
   
   # Copy application
   COPY app/ /app/app/
   COPY prompts/ /app/prompts/
   
   # Create data directory (will be volume mounted)
   RUN mkdir -p /app/data
   
   # Set environment
   ENV PYTHONPATH=/app
   ENV PYTHONUNBUFFERED=1
   ENV ENVIRONMENT=production
   
   # Health check
   HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
     CMD curl -f http://localhost:8000/health || exit 1
   
   EXPOSE 8000
   
   # Run as non-root user
   RUN useradd -m -u 1000 scout && chown -R scout:scout /app
   USER scout
   
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
   ```

### Building and Deploying

1. **Build Docker Image**
   ```bash
   cd ~/scout
   
   # Build for ARM64 (will take 10-15 minutes first time)
   docker compose -f docker/docker-compose.pi.yml build
   
   # Monitor build progress
   # You'll see packages compiling for ARM architecture
   # sentence-transformers and numpy take longest
   ```

2. **Initialize Application Data**
   ```bash
   # Create example profile
   cp data/profile.example.yaml /mnt/scout-data/profile.yaml
   
   # Edit with your information
   vim /mnt/scout-data/profile.yaml
   
   # Set proper permissions
   chmod 600 /mnt/scout-data/profile.yaml
   ```

3. **Start Services**
   ```bash
   # Start in detached mode
   docker compose -f docker/docker-compose.pi.yml up -d
   
   # Watch logs during startup
   docker compose -f docker/docker-compose.pi.yml logs -f
   
   # Should see:
   # - Redis starting
   # - Scout initializing modules
   # - ChromaDB creating collections
   # - FastAPI server ready
   
   # Press Ctrl+C to exit log view (containers keep running)
   ```

4. **Verify Deployment**
   ```bash
   # Check container status
   docker ps
   # Both scout-app and scout-redis should be "Up" and "healthy"
   
   # Test health endpoint
   curl http://localhost:8000/health
   # Should return: {"status":"healthy","version":"0.1.0"}
   
   # Test from your development machine
   curl http://scout-pi.local:8000/health
   ```

---

## Phase 6: Security Hardening

### Firewall Configuration

1. **Configure UFW (Uncomplicated Firewall)**
   ```bash
   # Default deny incoming, allow outgoing
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   
   # Allow SSH (rate limited)
   sudo ufw limit 22/tcp comment 'SSH rate limited'
   
   # Allow HTTP/HTTPS (for future Nginx reverse proxy)
   sudo ufw allow 80/tcp comment 'HTTP'
   sudo ufw allow 443/tcp comment 'HTTPS'
   
   # Allow Scout API (local network only)
   sudo ufw allow from 192.168.1.0/24 to any port 8000 proto tcp comment 'Scout API local'
   
   # Enable firewall
   sudo ufw enable
   
   # Verify rules
   sudo ufw status numbered
   ```

2. **Configure Fail2Ban for SSH Protection**
   ```bash
   # Create SSH jail configuration
   sudo tee /etc/fail2ban/jail.d/ssh.local > /dev/null <<EOF
   [sshd]
   enabled = true
   port = ssh
   filter = sshd
   logpath = /var/log/auth.log
   maxretry = 3
   bantime = 3600
   findtime = 600
   EOF
   
   # Restart fail2ban
   sudo systemctl restart fail2ban
   
   # Verify it's running
   sudo fail2ban-client status sshd
   ```

3. **Harden SSH Configuration**
   ```bash
   # Backup original config
   sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
   
   # Apply security settings
   sudo tee -a /etc/ssh/sshd_config > /dev/null <<EOF
   
   # Scout Security Hardening
   PermitRootLogin no
   PasswordAuthentication yes
   PubkeyAuthentication yes
   MaxAuthTries 3
   MaxSessions 2
   ClientAliveInterval 300
   ClientAliveCountMax 2
   AllowUsers scout
   EOF
   
   # Test configuration
   sudo sshd -t
   
   # If no errors, reload SSH
   sudo systemctl reload sshd
   ```

4. **Generate SSH Key for Secure Access**
   ```bash
   # On your development machine (not the Pi)
   ssh-keygen -t ed25519 -C "scout@scout-pi" -f ~/.ssh/scout-pi
   
   # Copy public key to Pi
   ssh-copy-id -i ~/.ssh/scout-pi.pub scout@scout-pi.local
   
   # Test key-based login
   ssh -i ~/.ssh/scout-pi scout@scout-pi.local
   
   # After confirming key works, optionally disable password auth:
   # sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
   # sudo systemctl reload sshd
   ```

### Application Security

1. **Secure API Keys and Secrets**
   ```bash
   # Ensure .env is not world-readable
   chmod 600 ~/scout/.env
   
   # Verify profile.yaml permissions
   chmod 600 /mnt/scout-data/profile.yaml
   
   # Check for accidental commits
   cd ~/scout
   git status
   # Ensure .env and profile.yaml are in .gitignore
   ```

2. **Set Up Log Rotation**
   ```bash
   # Create logrotate config for Scout
   sudo tee /etc/logrotate.d/scout > /dev/null <<EOF
   /var/log/scout/*.log {
       daily
       rotate 7
       compress
       delaycompress
       notifempty
       create 0640 scout scout
       sharedscripts
       postrotate
           docker compose -f /home/scout/scout/docker/docker-compose.pi.yml restart scout > /dev/null
       endscript
   }
   EOF
   
   # Create log directory
   sudo mkdir -p /var/log/scout
   sudo chown scout:scout /var/log/scout
   ```

---

## Phase 7: Monitoring and Maintenance

### System Monitoring

1. **Install Temperature Monitoring**
   ```bash
   # Create temperature monitoring script
   cat > ~/monitor-temp.sh <<'EOF'
   #!/bin/bash
   TEMP=$(vcgencmd measure_temp | cut -d'=' -f2 | cut -d"'" -f1)
   THROTTLE=$(vcgencmd get_throttled)
   
   echo "$(date '+%Y-%m-%d %H:%M:%S') - Temp: ${TEMP}°C - Throttle: ${THROTTLE}" >> /var/log/scout/temperature.log
   
   # Alert if over 70°C
   if (( $(echo "$TEMP > 70" | bc -l) )); then
       echo "WARNING: High temperature detected: ${TEMP}°C" | \
         logger -t scout-monitor -p user.warning
   fi
   EOF
   
   chmod +x ~/monitor-temp.sh
   
   # Add to crontab (every 5 minutes)
   (crontab -l 2>/dev/null; echo "*/5 * * * * /home/scout/monitor-temp.sh") | crontab -
   ```

2. **Create Health Check Script**
   ```bash
   cat > ~/health-check.sh <<'EOF'
   #!/bin/bash
   
   # Check if Scout container is healthy
   SCOUT_STATUS=$(docker inspect --format='{{.State.Health.Status}}' scout-app 2>/dev/null)
   
   if [ "$SCOUT_STATUS" != "healthy" ]; then
       echo "$(date '+%Y-%m-%d %H:%M:%S') - Scout container unhealthy, restarting..." | \
         tee -a /var/log/scout/health-check.log
       docker compose -f /home/scout/scout/docker/docker-compose.pi.yml restart scout
   fi
   
   # Check disk space
   DISK_USAGE=$(df /mnt/scout-data | tail -1 | awk '{print $5}' | sed 's/%//')
   if [ "$DISK_USAGE" -gt 80 ]; then
       echo "$(date '+%Y-%m-%d %H:%M:%S') - WARNING: Disk usage at ${DISK_USAGE}%" | \
         logger -t scout-monitor -p user.warning
   fi
   EOF
   
   chmod +x ~/health-check.sh
   
   # Run every 10 minutes
   (crontab -l 2>/dev/null; echo "*/10 * * * * /home/scout/health-check.sh") | crontab -
   ```

3. **Set Up Resource Monitoring Dashboard**
   ```bash
   # Install btop (modern htop alternative, better Pi support)
   sudo apt install -y btop
   
   # Create alias for quick monitoring
   echo "alias scout-status='btop && docker stats'" >> ~/.bashrc
   source ~/.bashrc
   ```

### Backup Strategy

1. **Create Backup Script**
   ```bash
   cat > ~/backup-scout.sh <<'EOF'
   #!/bin/bash
   
   # Configuration
   BACKUP_DIR="/mnt/scout-data/backups"
   TIMESTAMP=$(date +%Y%m%d_%H%M%S)
   BACKUP_NAME="scout_backup_${TIMESTAMP}.tar.gz"
   
   # Create backup directory if doesn't exist
   mkdir -p "$BACKUP_DIR"
   
   echo "Starting Scout backup at $(date)"
   
   # Stop Scout container to ensure data consistency
   docker compose -f /home/scout/scout/docker/docker-compose.pi.yml stop scout
   
   # Backup data directory (excluding backups subdirectory)
   tar -czf "${BACKUP_DIR}/${BACKUP_NAME}" \
     --exclude="${BACKUP_DIR}" \
     -C /mnt/scout-data \
     profile.yaml \
     vectors/ \
     cache/ \
     exports/ \
     scout.db
   
   # Restart Scout
   docker compose -f /home/scout/scout/docker/docker-compose.pi.yml start scout
   
   # Keep only last 7 backups
   cd "$BACKUP_DIR"
   ls -t scout_backup_*.tar.gz | tail -n +8 | xargs -r rm
   
   echo "Backup completed: ${BACKUP_NAME}"
   echo "Backup size: $(du -h ${BACKUP_DIR}/${BACKUP_NAME} | cut -f1)"
   EOF
   
   chmod +x ~/backup-scout.sh
   
   # Schedule daily backup at 3 AM
   (crontab -l 2>/dev/null; echo "0 3 * * * /home/scout/backup-scout.sh >> /var/log/scout/backup.log 2>&1") | crontab -
   ```

2. **Test Backup**
   ```bash
   # Run manual backup
   ~/backup-scout.sh
   
   # Verify backup was created
   ls -lh /mnt/scout-data/backups/
   
   # Test backup integrity
   tar -tzf /mnt/scout-data/backups/scout_backup_*.tar.gz | head -20
   ```

3. **Optional: Cloud Backup Integration**
   ```bash
   # Install rclone for cloud backups
   sudo apt install -y rclone
   
   # Configure cloud provider (interactive)
   rclone config
   # Follow prompts to set up Google Drive, Dropbox, or S3
   
   # Add to backup script (after local backup creation)
   cat >> ~/backup-scout.sh <<'EOF'
   
   # Sync to cloud (if configured)
   if [ -f ~/.config/rclone/rclone.conf ]; then
       rclone sync ${BACKUP_DIR}/ remote:scout-backups/ \
         --include "scout_backup_*.tar.gz" \
         --min-age 1h
   fi
   EOF
   ```

---

## Phase 8: Network Access Configuration

### Option A: Local Network Only (Recommended for Start)

1. **Configure Static IP (Optional)**
   ```bash
   # Find current IP and gateway
   ip addr show eth0
   ip route | grep default
   
   # Edit dhcpcd configuration
   sudo vim /etc/dhcpcd.conf
   
   # Add at the end:
   # interface eth0
   # static ip_address=192.168.1.100/24
   # static routers=192.168.1.1
   # static domain_name_servers=192.168.1.1 8.8.8.8
   
   # Restart networking
   sudo systemctl restart dhcpcd
   ```

2. **Access from Development Machine**
   ```bash
   # Add to your hosts file for easy access
   echo "192.168.1.100 scout-pi.local" | sudo tee -a /etc/hosts
   
   # Test access
   curl http://scout-pi.local:8000/health
   ```

### Option B: Secure Remote Access via Tailscale VPN

1. **Install Tailscale**
   ```bash
   # On Raspberry Pi
   curl -fsSL https://tailscale.com/install.sh | sh
   
   # Authenticate (opens browser)
   sudo tailscale up
   
   # Get Tailscale IP
   tailscale ip -4
   # Note this IP (e.g., 100.x.x.x)
   ```

2. **Install on Development Machine**
   ```bash
   # On your Arch Linux machine
   yay -S tailscale
   sudo systemctl enable --now tailscaled
   sudo tailscale up
   
   # Both devices should now see each other
   tailscale status
   ```

3. **Access Scout via Tailscale**
   ```bash
   # Use Tailscale IP directly
   curl http://100.x.x.x:8000/health
   
   # Or use machine name
   curl http://scout-pi:8000/health
   ```

### Option C: Public Access via Nginx Reverse Proxy (Advanced)

**⚠️ Only implement after testing locally. Requires domain and SSL setup.**

1. **Install Nginx**
   ```bash
   sudo apt install -y nginx certbot python3-certbot-nginx
   ```

2. **Configure Nginx Reverse Proxy**
   ```bash
   sudo tee /etc/nginx/sites-available/scout > /dev/null <<EOF
   server {
       listen 80;
       server_name your-domain.com;
       
       # Rate limiting
       limit_req_zone \$binary_remote_addr zone=scout:10m rate=10r/m;
       
       location / {
           limit_req zone=scout burst=5;
           
           proxy_pass http://localhost:8000;
           proxy_set_header Host \$host;
           proxy_set_header X-Real-IP \$remote_addr;
           proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto \$scheme;
           
           # Timeouts
           proxy_connect_timeout 60s;
           proxy_send_timeout 60s;
           proxy_read_timeout 60s;
       }
   }
   EOF
   
   # Enable site
   sudo ln -s /etc/nginx/sites-available/scout /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

3. **Configure SSL with Let's Encrypt**
   ```bash
   sudo certbot --nginx -d your-domain.com
   # Follow prompts, select redirect HTTP to HTTPS
   
   # Auto-renewal (certbot installs timer automatically)
   sudo systemctl status certbot.timer
   ```

---

## Phase 9: Testing and Validation

### Functional Testing

1. **Test Profile Loading**
   ```bash
   # API endpoint test
   curl http://localhost:8000/api/v1/profile/summary
   
   # Should return profile information from profile.yaml
   ```

2. **Test Job Processing**
   ```bash
   # Create test job posting file
   cat > /tmp/test-job.txt <<EOF
   Senior Python Developer
   Company: TechCorp
   Location: Copenhagen
   
   Requirements:
   - 5+ years Python experience
   - FastAPI and Django
   - Docker and Kubernetes
   - Machine Learning experience preferred
   EOF
   
   # Submit via API
   curl -X POST http://localhost:8000/api/v1/jobs/process \
     -H "Content-Type: application/json" \
     -d "{\"job_text\": \"$(cat /tmp/test-job.txt | jq -Rs .)\"}"
   
   # Monitor logs
   docker compose -f docker/docker-compose.pi.yml logs -f scout
   ```

3. **Test Vector Search**
   ```bash
   # Search for matching experiences
   curl -X POST http://localhost:8000/api/v1/profile/search \
     -H "Content-Type: application/json" \
     -d '{"query": "Python FastAPI Docker", "limit": 3}'
   
   # Verify ChromaDB is working
   ls -lh /mnt/scout-data/vectors/
   ```

### Performance Testing

1. **Benchmark Embedding Generation**
   ```bash
   # Time sentence-transformers on Pi
   docker exec scout-app python3 <<EOF
   import time
   from sentence_transformers import SentenceTransformer
   
   model = SentenceTransformer('all-MiniLM-L6-v2')
   
   test_texts = [
       "Python developer with FastAPI experience",
       "Machine learning engineer with PyTorch",
       "Full-stack developer React and Node.js"
   ] * 10  # 30 sentences
   
   start = time.time()
   embeddings = model.encode(test_texts)
   elapsed = time.time() - start
   
   print(f"Encoded {len(test_texts)} sentences in {elapsed:.2f}s")
   print(f"Average: {elapsed/len(test_texts)*1000:.0f}ms per sentence")
   EOF
   
   # Target: <150ms per sentence on Pi 5
   ```

2. **Monitor Resource Usage During Processing**
   ```bash
   # Open htop in one terminal
   htop
   
   # Submit multiple jobs in another terminal
   for i in {1..5}; do
     curl -X POST http://localhost:8000/api/v1/jobs/process \
       -H "Content-Type: application/json" \
       -d @/tmp/test-job.txt &
   done
   
   # Watch RAM, CPU, temperature
   ```

3. **Test PDF Generation**
   ```bash
   # Generate test CV
   curl -X POST http://localhost:8000/api/v1/generate/cv \
     -H "Content-Type: application/json" \
     -d '{"job_id": "test", "format": "modern"}' \
     -o /tmp/test-cv.pdf
   
   # Verify PDF was created and is valid
   file /tmp/test-cv.pdf
   # Should show: "PDF document"
   ```

### Stress Testing

1. **Simulate Concurrent Users**
   ```bash
   # Install Apache Bench on development machine
   sudo pacman -S apache
   
   # Send 100 requests with 5 concurrent
   ab -n 100 -c 5 http://scout-pi.local:8000/health
   
   # Review results
   # Target: All requests successful, <100ms average response time
   ```

2. **Temperature Monitoring Under Load**
   ```bash
   # Start load test
   while true; do
     curl -X POST http://localhost:8000/api/v1/jobs/process \
       -H "Content-Type: application/json" \
       -d @/tmp/test-job.txt
     sleep 2
   done &
   
   # Monitor temperature
   watch -n 2 vcgencmd measure_temp
   
   # Stop load test
   killall curl
   
   # Target: <75°C sustained, no throttling
   # Check throttling: vcgencmd get_throttled
   # 0x0 = no issues, any other value = throttling occurred
   ```

---

## Phase 10: Troubleshooting Guide

### Common Issues and Solutions

**Issue: Docker build fails with "killed" or OOM**
```bash
# Solution: Build with resource limits
docker compose -f docker/docker-compose.pi.yml build --memory=2g

# Alternative: Build on development machine and export
# On x86 machine with Docker:
docker buildx build --platform linux/arm64 -t scout:pi -f docker/Dockerfile.pi .
docker save scout:pi | gzip > scout-pi-image.tar.gz

# Transfer to Pi and load
scp scout-pi-image.tar.gz scout@scout-pi.local:~/
ssh scout@scout-pi.local
docker load < scout-pi-image.tar.gz
```

**Issue: sentence-transformers very slow**
```bash
# Check if using CPU vs GPU (Pi has no GPU acceleration)
docker exec scout-app python3 -c "import torch; print(torch.cuda.is_available())"
# Should print: False (expected)

# Reduce batch size in code if needed
# Edit app/services/vector_store.py
# Change: batch_size=32 → batch_size=8
```

**Issue: SSD not mounting on boot**
```bash
# Check fstab syntax
cat /etc/fstab | grep scout-data

# Test mount manually
sudo umount /mnt/scout-data
sudo mount -a

# Check for errors
dmesg | tail -20

# Verify UUID matches
sudo blkid /dev/sda1
```

**Issue: High temperature / thermal throttling**
```bash
# Check current temperature
vcgencmd measure_temp

# Check throttling history
vcgencmd get_throttled

# Improve cooling:
# 1. Ensure fan is spinning: lsusb (should show fan controller)
# 2. Adjust fan curve: sudo raspi-config → Performance → Fan
# 3. Add heatsinks to RAM chips
# 4. Improve case ventilation
```

**Issue: ChromaDB corrupted**
```bash
# Stop Scout
docker compose -f docker/docker-compose.pi.yml stop scout

# Remove vector database
rm -rf /mnt/scout-data/vectors/*

# Restart Scout (will rebuild from profile)
docker compose -f docker/docker-compose.pi.yml start scout

# Check logs
docker compose -f docker/docker-compose.pi.yml logs -f scout
```

**Issue: Can't access from network**
```bash
# Check if port is listening
sudo netstat -tlnp | grep 8000

# Check firewall rules
sudo ufw status

# Test from Pi itself
curl http://localhost:8000/health

# Check Docker network
docker network inspect bridge

# Verify container is running
docker ps
```

---

## Phase 11: Showcase Preparation

### Demo Environment Setup

1. **Create Sample Data**
   ```bash
   # Add diverse job postings to database
   cd ~/scout
   mkdir -p test-data/jobs
   
   # Create 5 varied job postings
   cat > test-data/jobs/senior-python.txt <<EOF
   Senior Python Engineer
   TechCorp - Copenhagen
   
   We're seeking an experienced Python developer...
   Requirements: 5+ years Python, FastAPI, Docker, ML experience
   EOF
   
   # Process sample jobs
   for job in test-data/jobs/*.txt; do
     curl -X POST http://localhost:8000/api/v1/jobs/process \
       -H "Content-Type: application/json" \
       -d "{\"job_text\": \"$(cat $job | jq -Rs .)\"}"
     sleep 2
   done
   ```

2. **Prepare Demo Script**
   ```bash
   cat > ~/demo-script.md <<EOF
   # Scout Demo Script
   
   ## 1. System Overview (2 min)
   - Show: htop (system resources)
   - Point: Running on Raspberry Pi 5
   - Explain: Edge deployment capability
   
   ## 2. Profile Management (3 min)
   - Show: cat /mnt/scout-data/profile.yaml
   - Demonstrate: API profile endpoint
   - Explain: Vector indexing of experience
   
   ## 3. Job Processing (5 min)
   - Show: Submit job posting via API
   - Watch: Logs show Rinser → Analyzer → Creator
   - Explain: Multi-stage pipeline architecture
   
   ## 4. Application Generation (5 min)
   - Show: Generated CV PDF
   - Highlight: ATS optimization, keyword matching
   - Explain: Template system, WeasyPrint rendering
   
   ## 5. Performance Metrics (2 min)
   - Show: Docker stats (resource usage)
   - Show: Temperature monitoring
   - Explain: Cost tracking, API budgets
   
   ## 6. Scalability Discussion (3 min)
   - Explain: Same Docker image runs on cloud
   - Show: docker-compose.yml portability
   - Discuss: Migration path to production
   EOF
   ```

3. **Create Dashboard Script**
   ```bash
   cat > ~/scout-dashboard.sh <<'EOF'
   #!/bin/bash
   
   echo "=== Scout System Dashboard ==="
   echo ""
   echo "Temperature: $(vcgencmd measure_temp)"
   echo "Uptime: $(uptime -p)"
   echo ""
   echo "=== Docker Containers ==="
   docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
   echo ""
   echo "=== Disk Usage ==="
   df -h /mnt/scout-data | tail -1
   echo ""
   echo "=== Recent Logs ==="
   docker logs --tail 10 scout-app
   EOF
   
   chmod +x ~/scout-dashboard.sh
   ```

### Documentation for Portfolio

1. **Create Deployment Summary**
   ```bash
   cat > ~/deployment-summary.md <<EOF
   # Scout PoC - Raspberry Pi Deployment
   
   **Date**: $(date +%Y-%m-%d)
   **Hardware**: Raspberry Pi 5 (8GB)
   **OS**: Raspberry Pi OS 64-bit (Debian Bookworm)
   **Storage**: 256GB USB 3.0 SSD
   
   ## Architecture
   - FastAPI application in Docker
   - ChromaDB vector database
   - Redis caching layer
   - Nginx reverse proxy (optional)
   
   ## Performance Benchmarks
   - Embedding generation: ~XXms per sentence
   - PDF generation: ~XXs per document
   - API response time: ~XXms average
   - Concurrent users: X tested successfully
   - Temperature under load: XX°C
   
   ## Cost Analysis
   - Hardware: \$XXX one-time
   - Power consumption: ~15W (£X/month)
   - API costs: \$X/month (Anthropic)
   - Total monthly: \$X vs Hetzner \$Y
   
   ## Lessons Learned
   1. ARM architecture considerations
   2. Storage strategy (SD vs SSD)
   3. Thermal management importance
   4. Resource optimization techniques
   
   ## Scalability Path
   - PoC: Raspberry Pi (1-5 users)
   - Beta: Hetzner CAX11 (10-50 users)
   - Production: Hetzner CAX31 + CDN (100+ users)
   EOF
   ```

2. **Take Screenshots**
   ```bash
   # Install screenshot utility
   sudo apt install -y scrot
   
   # Capture dashboard
   DISPLAY=:0 scrot ~/scout-dashboard.png
   
   # Transfer to development machine for portfolio
   scp scout@scout-pi.local:~/scout-dashboard.png ~/Documents/portfolio/
   ```

---

## Phase 12: Maintenance Procedures

### Daily Operations

**Morning Checklist (2 minutes):**
```bash
# Run dashboard
~/scout-dashboard.sh

# Check health
curl http://localhost:8000/health

# Review overnight logs
docker compose -f docker/docker-compose.pi.yml logs --since 12h | grep ERROR
```

### Weekly Maintenance

**Every Sunday (10 minutes):**
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Rebuild Docker images with latest base
cd ~/scout
docker compose -f docker/docker-compose.pi.yml pull
docker compose -f docker/docker-compose.pi.yml build --no-cache

# Restart services
docker compose -f docker/docker-compose.pi.yml down
docker compose -f docker/docker-compose.pi.yml up -d

# Verify backup completed
ls -lh /mnt/scout-data/backups/

# Check disk space
df -h /mnt/scout-data
ncdu /mnt/scout-data
```

### Monthly Maintenance

**First of Month (30 minutes):**
```bash
# Full system audit
sudo apt update && sudo apt upgrade -y && sudo apt autoremove -y

# Review and rotate logs
sudo logrotate -f /etc/logrotate.conf

# Check SSD health (if smartctl available)
sudo smartctl -a /dev/sda

# Export cost tracking report
curl http://localhost:8000/api/v1/costs/monthly > ~/cost-report-$(date +%Y-%m).json

# Test disaster recovery
~/backup-scout.sh
# Verify backup integrity
tar -tzf /mnt/scout-data/backups/scout_backup_*.tar.gz > /dev/null && echo "Backup OK"
```

### Updating Scout Application

**When code changes:**
```bash
# Pull latest changes
cd ~/scout
git pull origin main

# Rebuild and restart
docker compose -f docker/docker-compose.pi.yml build
docker compose -f docker/docker-compose.pi.yml down
docker compose -f docker/docker-compose.pi.yml up -d

# Watch logs for errors
docker compose -f docker/docker-compose.pi.yml logs -f
```

---

## Performance Expectations

### Realistic Benchmarks for Pi 5

| Operation | Expected Time | Notes |
|-----------|--------------|-------|
| Embedding generation (single) | 80-120ms | sentence-transformers on ARM CPU |
| Embedding generation (batch 100) | 8-12s | Parallelized where possible |
| Job analysis | 2-4s | Anthropic API latency dominant |
| CV generation | 3-5s | WeasyPrint PDF rendering |
| Vector search (10k docs) | 30-50ms | ChromaDB in-memory |
| API cold start | 15-20s | First request after container start |
| API warm response | 50-200ms | Cached profile data |

### Resource Usage

| Component | RAM | CPU (avg) | Disk I/O |
|-----------|-----|-----------|----------|
| Scout App | 800MB-1.5GB | 40-60% (spikes to 150%) | Low |
| Redis | 100-200MB | <5% | Low |
| ChromaDB | 200-500MB | 10-20% during indexing | Medium |
| System | 300-500MB | 5-10% | Low |
| **Total** | **2-3GB** | **60-90%** | **Medium** |

**Thermal Performance:**
- Idle: 45-50°C
- Light load: 55-60°C
- Heavy processing: 65-75°C
- Thermal throttling: >80°C (avoid)

---

## Summary and Next Steps

### What You've Accomplished

✅ **Production-grade deployment** of Scout on ARM64 architecture  
✅ **Secure infrastructure** with firewall, SSH hardening, fail2ban  
✅ **Reliable storage** with SSD for data persistence  
✅ **Automated monitoring** and health checks  
✅ **Backup strategy** with daily automated backups  
✅ **Docker-based deployment** matching production patterns  
✅ **Cost-effective showcase** environment (<£5/month power)

### Deployment Quality Levels

**Current State: Demo-Ready ✅**
- Functional Scout instance
- Basic security hardening
- Local network access
- Manual backup capability

**Production-Ready Checklist:**
- [ ] Nginx reverse proxy with SSL
- [ ] Automated cloud backups
- [ ] Centralized logging (rsyslog to cloud)
- [ ] Monitoring alerts (email/SMS)
- [ ] Load balancing (if scaling)
- [ ] Regular penetration testing
- [ ] Documented disaster recovery procedure
- [ ] 24/7 uptime monitoring

### Recommended Next Actions

**Immediate (This Week):**
1. Complete functional testing with real job postings
2. Document any performance bottlenecks discovered
3. Create demo script and practice presentation
4. Take screenshots for portfolio documentation

**Short-term (This Month):**
1. Implement Tailscale VPN for remote demos
2. Set up cloud backup sync (rclone to Google Drive)
3. Create comparison metrics (Pi vs Hetzner costs/performance)
4. Write blog post about deployment experience

**Long-term (Next Quarter):**
1. Migrate to Hetzner when user base grows
2. Implement horizontal scaling architecture
3. Add monitoring dashboard (Prometheus + Grafana)
4. Consider contributing ARM deployment guide to open source

### Getting Help

**Common Resources:**
- Raspberry Pi Forums: https://forums.raspberrypi.com/
- Docker ARM: https://www.docker.com/blog/tag/arm/
- Scout Issues: [Your GitHub repo]/issues

**Emergency Contacts:**
- System won't boot: Check power supply, SD card integrity
- Container won't start: Check logs, verify SSD mounted
- High temperature: Verify fan operation, check ambient temp
- Network issues: Restart router, check firewall rules

---

## Conclusion

You now have a fully functional Scout deployment on Raspberry Pi 5 that demonstrates:

**Technical Skills:**
- Docker containerization on ARM architecture
- Production-grade security practices
- System monitoring and maintenance
- Backup and disaster recovery strategies

**Strategic Value:**
- Cost-conscious infrastructure decisions
- Scalability planning from edge to cloud
- DevOps automation practices
- Real-world deployment experience

This deployment serves as both a functional PoC environment and a portfolio piece showcasing your ability to deploy complex applications on resource-constrained hardware while maintaining production-quality standards.

**Total Deployment Cost**: ~$150 hardware + £5/month power + variable API costs  
**Hetzner Alternative**: €4/month CAX11 (similar performance, no upfront cost)

The Pi deployment proves Scout's flexibility and your infrastructure competence. When ready to scale, the Docker-based architecture ensures seamless migration to cloud hosting.

Good luck with your demos! 🚀
