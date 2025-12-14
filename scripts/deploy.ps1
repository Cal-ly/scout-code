<#
.SYNOPSIS
    Deploy Scout to Raspberry Pi

.DESCRIPTION
    Automates deployment from Windows development machine to Raspberry Pi:
    1. Commits and pushes changes to GitHub (optional)
    2. Pulls latest code on Pi
    3. Restarts Scout service
    4. Verifies deployment

.PARAMETER Message
    Git commit message. If provided, changes will be committed and pushed.

.PARAMETER SkipCommit
    Skip git commit/push, only deploy existing changes on Pi.

.PARAMETER NoPull
    Skip git pull on Pi (useful for testing local changes).

.PARAMETER NoRestart
    Skip service restart.

.EXAMPLE
    .\deploy.ps1 -Message "Fix navigation bug"
    Commits with message, pushes, and deploys to Pi.

.EXAMPLE
    .\deploy.ps1 -SkipCommit
    Deploys existing pushed changes to Pi without committing.

.EXAMPLE
    .\deploy.ps1
    Interactive mode - prompts for commit message or skips if no changes.
#>

param(
    [string]$Message = "",
    [switch]$SkipCommit,
    [switch]$NoPull,
    [switch]$NoRestart
)

# Configuration
$PI_HOST = "192.168.1.21"
$PI_USER = "cally"
$PI_PROJECT = "/home/cally/projects/scout-code"
$PI_SERVICE = "scout.service"
$VERIFY_URL = "http://localhost:8000/"

# Colors for output
function Write-Step { param($msg) Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "    $msg" -ForegroundColor Green }
function Write-Warning { param($msg) Write-Host "    $msg" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "    $msg" -ForegroundColor Red }

# Get script directory and project root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "============================================" -ForegroundColor Magenta
Write-Host "  Scout Deployment Script" -ForegroundColor Magenta
Write-Host "  Target: $PI_USER@$PI_HOST" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta

# Change to project directory
Set-Location $ProjectRoot

# Step 1: Check for changes and commit/push
if (-not $SkipCommit) {
    Write-Step "Checking for changes..."

    $status = git status --porcelain

    if ($status) {
        Write-Success "Found uncommitted changes"

        # Show what's changed
        git status --short

        # Get commit message
        if (-not $Message) {
            $Message = Read-Host "`nEnter commit message (or press Enter to skip commit)"
        }

        if ($Message) {
            Write-Step "Committing and pushing changes..."

            git add -A
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Failed to stage changes"
                exit 1
            }

            # Create commit with co-author
            $commitMsg = @"
$Message

Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
"@
            git commit -m $commitMsg
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Failed to commit"
                exit 1
            }

            git push origin main
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Failed to push"
                exit 1
            }

            Write-Success "Changes pushed to GitHub"
        } else {
            Write-Warning "Skipping commit (no message provided)"
        }
    } else {
        Write-Success "No local changes to commit"
    }
}

# Step 2: Pull on Pi
if (-not $NoPull) {
    Write-Step "Pulling latest code on Raspberry Pi..."

    $pullCmd = "cd $PI_PROJECT && git stash --include-untracked 2>/dev/null; git pull origin main"
    $result = ssh "$PI_USER@$PI_HOST" $pullCmd

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to pull on Pi"
        Write-Host $result
        exit 1
    }

    Write-Success "Code updated on Pi"
    Write-Host $result -ForegroundColor Gray
}

# Step 3: Restart service
if (-not $NoRestart) {
    Write-Step "Restarting Scout service..."

    $restartCmd = "sudo systemctl restart $PI_SERVICE"
    ssh "$PI_USER@$PI_HOST" $restartCmd

    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Service restart command returned non-zero (may still be OK)"
    }

    # Wait for service to start
    Write-Host "    Waiting for service to start..." -ForegroundColor Gray
    Start-Sleep -Seconds 3

    # Check service status
    $statusCmd = "sudo systemctl is-active $PI_SERVICE"
    $serviceStatus = ssh "$PI_USER@$PI_HOST" $statusCmd

    if ($serviceStatus -eq "active") {
        Write-Success "Service is running"
    } else {
        Write-Error "Service is not active: $serviceStatus"
        Write-Host "`nChecking logs..." -ForegroundColor Yellow
        ssh "$PI_USER@$PI_HOST" "sudo journalctl -u $PI_SERVICE -n 20 --no-pager"
        exit 1
    }
}

# Step 4: Verify deployment
Write-Step "Verifying deployment..."

$verifyCmd = "curl -s -o /dev/null -w '%{http_code}' $VERIFY_URL"
$httpCode = ssh "$PI_USER@$PI_HOST" $verifyCmd

if ($httpCode -eq "200") {
    Write-Success "Deployment verified (HTTP 200)"
} else {
    Write-Warning "Unexpected HTTP code: $httpCode"
}

# Done
Write-Host "`n============================================" -ForegroundColor Green
Write-Host "  Deployment Complete!" -ForegroundColor Green
Write-Host "  Access at: http://$PI_HOST`:8000/" -ForegroundColor Green
Write-Host "============================================`n" -ForegroundColor Green
