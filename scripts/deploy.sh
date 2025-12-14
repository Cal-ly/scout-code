#!/bin/bash
#
# Deploy Scout to Raspberry Pi
#
# Usage:
#   ./deploy.sh                    # Interactive mode
#   ./deploy.sh "commit message"   # Commit with message and deploy
#   ./deploy.sh --skip-commit      # Deploy without committing
#   ./deploy.sh --no-restart       # Deploy without restarting service
#

set -e

# Configuration
PI_HOST="192.168.1.21"
PI_USER="cally"
PI_PROJECT="/home/cally/projects/scout-code"
PI_SERVICE="scout.service"
VERIFY_URL="http://localhost:8000/"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Parse arguments
COMMIT_MSG=""
SKIP_COMMIT=false
NO_PULL=false
NO_RESTART=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-commit)
            SKIP_COMMIT=true
            shift
            ;;
        --no-pull)
            NO_PULL=true
            shift
            ;;
        --no-restart)
            NO_RESTART=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS] [COMMIT_MESSAGE]"
            echo ""
            echo "Options:"
            echo "  --skip-commit    Skip git commit/push"
            echo "  --no-pull        Skip git pull on Pi"
            echo "  --no-restart     Skip service restart"
            echo "  -h, --help       Show this help"
            exit 0
            ;;
        *)
            COMMIT_MSG="$1"
            shift
            ;;
    esac
done

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${MAGENTA}============================================${NC}"
echo -e "${MAGENTA}  Scout Deployment Script${NC}"
echo -e "${MAGENTA}  Target: ${PI_USER}@${PI_HOST}${NC}"
echo -e "${MAGENTA}============================================${NC}"

# Change to project directory
cd "$PROJECT_ROOT"

# Step 1: Check for changes and commit/push
if [ "$SKIP_COMMIT" = false ]; then
    echo -e "\n${CYAN}>>> Checking for changes...${NC}"

    if [[ -n $(git status --porcelain) ]]; then
        echo -e "${GREEN}    Found uncommitted changes${NC}"
        git status --short

        # Get commit message if not provided
        if [ -z "$COMMIT_MSG" ]; then
            echo ""
            read -p "Enter commit message (or press Enter to skip): " COMMIT_MSG
        fi

        if [ -n "$COMMIT_MSG" ]; then
            echo -e "\n${CYAN}>>> Committing and pushing changes...${NC}"

            git add -A

            git commit -m "$COMMIT_MSG

Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

            git push origin main

            echo -e "${GREEN}    Changes pushed to GitHub${NC}"
        else
            echo -e "${YELLOW}    Skipping commit (no message provided)${NC}"
        fi
    else
        echo -e "${GREEN}    No local changes to commit${NC}"
    fi
fi

# Step 2: Pull on Pi
if [ "$NO_PULL" = false ]; then
    echo -e "\n${CYAN}>>> Pulling latest code on Raspberry Pi...${NC}"

    ssh "$PI_USER@$PI_HOST" "cd $PI_PROJECT && git stash --include-untracked 2>/dev/null || true; git pull origin main"

    echo -e "${GREEN}    Code updated on Pi${NC}"
fi

# Step 3: Restart service
if [ "$NO_RESTART" = false ]; then
    echo -e "\n${CYAN}>>> Restarting Scout service...${NC}"

    ssh "$PI_USER@$PI_HOST" "sudo systemctl restart $PI_SERVICE" || true

    echo "    Waiting for service to start..."
    sleep 3

    # Check service status
    SERVICE_STATUS=$(ssh "$PI_USER@$PI_HOST" "sudo systemctl is-active $PI_SERVICE" || echo "unknown")

    if [ "$SERVICE_STATUS" = "active" ]; then
        echo -e "${GREEN}    Service is running${NC}"
    else
        echo -e "${RED}    Service is not active: $SERVICE_STATUS${NC}"
        echo -e "${YELLOW}Checking logs...${NC}"
        ssh "$PI_USER@$PI_HOST" "sudo journalctl -u $PI_SERVICE -n 20 --no-pager"
        exit 1
    fi
fi

# Step 4: Verify deployment
echo -e "\n${CYAN}>>> Verifying deployment...${NC}"

HTTP_CODE=$(ssh "$PI_USER@$PI_HOST" "curl -s -o /dev/null -w '%{http_code}' $VERIFY_URL")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}    Deployment verified (HTTP 200)${NC}"
else
    echo -e "${YELLOW}    Unexpected HTTP code: $HTTP_CODE${NC}"
fi

# Done
echo -e "\n${GREEN}============================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}  Access at: http://${PI_HOST}:8000/${NC}"
echo -e "${GREEN}============================================${NC}\n"
