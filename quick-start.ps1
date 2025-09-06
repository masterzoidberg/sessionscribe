# Quick Start Script for SessionScribe
Write-Host "SessionScribe Quick Start" -ForegroundColor Green

# Check if virtual environment exists
if (!(Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\.venv\Scripts\Activate.ps1"

# Install Python dependencies if needed
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install fastapi uvicorn[standard] websockets spacy jsonschema httpx sounddevice numpy pywin32 openai pydantic pytest

# Download spaCy model
Write-Host "Downloading spaCy model..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe -m spacy download en_core_web_sm

# Install Node dependencies
Write-Host "Installing Node.js dependencies..." -ForegroundColor Yellow
pnpm install

Write-Host ""
Write-Host "Dependencies installed! Now starting services..." -ForegroundColor Green

# Start services in background
Write-Host "Starting ASR service..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\.venv\Scripts\Activate.ps1; uvicorn services.asr.app:app --host 127.0.0.1 --port 7031" -WindowStyle Normal

Write-Host "Starting Redaction service..." -ForegroundColor Cyan  
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\.venv\Scripts\Activate.ps1; uvicorn services.redaction.app:app --host 127.0.0.1 --port 7032" -WindowStyle Normal

Write-Host "Starting Note Builder service..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\.venv\Scripts\Activate.ps1; uvicorn services.note_builder.app:app --host 127.0.0.1 --port 7034" -WindowStyle Normal

Write-Host "Starting Insights service..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\.venv\Scripts\Activate.ps1; uvicorn services.insights_bridge.app:app --host 127.0.0.1 --port 7033" -WindowStyle Normal

Start-Sleep -Seconds 3

Write-Host "Starting React dev server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; pnpm -C apps/desktop/renderer dev" -WindowStyle Normal

Start-Sleep -Seconds 2

Write-Host "Starting Electron..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; pnpm -C apps/desktop/electron dev" -WindowStyle Normal

Write-Host ""
Write-Host "All services started!" -ForegroundColor Green
Write-Host "Services: ASR(7031) Redaction(7032) Insights(7033) NoteBuilder(7034)" -ForegroundColor Gray
Write-Host "Frontend: React(3000) + Electron App" -ForegroundColor Gray
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor DarkGray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")