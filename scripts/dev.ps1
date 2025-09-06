# SessionScribe Development Startup Script
Write-Host "Starting SessionScribe Development Environment..." -ForegroundColor Green

# Check if Python is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Check if Node.js/pnpm is available
try {
    $nodeVersion = node --version 2>&1
    $pnpmVersion = pnpm --version 2>&1
    Write-Host "✓ Node.js found: $nodeVersion" -ForegroundColor Green
    Write-Host "✓ pnpm found: v$pnpmVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js or pnpm not found. Please install Node.js and pnpm" -ForegroundColor Red
    exit 1
}

# Install dependencies if needed
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pnpm install

# Install Python dependencies for services
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
if (Test-Path "requirements-test.txt") {
    pip install -r requirements-test.txt
}

foreach ($service in @("services/asr", "services/redaction", "services/insights_bridge", "services/note_builder")) {
    if (Test-Path "$service/requirements.txt") {
        pip install -r "$service/requirements.txt"
    }
}

# Set environment variables for development
$env:SS_OFFLINE = "true"
$env:SS_REDACT_BEFORE_SEND = "true" 
$env:SS_OUTPUT_DIR = "$env:USERPROFILE\Documents\SessionScribe"
$env:SS_DASHBOARD_PROVIDER = "openai_api"
$env:SS_NOTE_MODEL = "gpt-4o-mini"
$env:SS_NOTE_TEMPERATURE = "0.2"

# Create output directory
if (!(Test-Path "$env:SS_OUTPUT_DIR")) {
    New-Item -ItemType Directory -Path "$env:SS_OUTPUT_DIR" -Force
    Write-Host "✓ Created output directory: $env:SS_OUTPUT_DIR" -ForegroundColor Green
}

Write-Host ""
Write-Host "Environment configured. Starting services..." -ForegroundColor Green
Write-Host ""

# Start services
Start-Process powershell -ArgumentList "uvicorn services.asr.app:app --reload --port 7031"
Start-Process powershell -ArgumentList "uvicorn services.redaction.app:app --reload --port 7032"
Start-Process powershell -ArgumentList "uvicorn services.note_builder.app:app --reload --port 7034"
Start-Process powershell -ArgumentList "uvicorn services.insights_bridge.app:app --reload --port 7033"

Write-Host "✓ Started FastAPI services on ports 7031, 7032, 7033, 7034" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Start React renderer: pnpm -C apps/desktop/renderer dev" -ForegroundColor Yellow
Write-Host "  2. Start Electron main:   pnpm -C apps/desktop/electron dev" -ForegroundColor Yellow
Write-Host ""