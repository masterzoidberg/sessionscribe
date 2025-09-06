# SessionScribe Launch Script
Write-Host "Launching SessionScribe..." -ForegroundColor Green
Write-Host ""

$rootPath = $PSScriptRoot

# Function to start a service in a new window
function Start-Service {
    param(
        [string]$ServiceName,
        [string]$Command,
        [int]$Port
    )
    
    Write-Host "Starting $ServiceName on port $Port..." -ForegroundColor Cyan
    
    $processArgs = @{
        FilePath = "powershell.exe"
        ArgumentList = @(
            "-NoExit",
            "-Command",
            "cd '$rootPath'; .\.venv\Scripts\Activate.ps1; $Command"
        )
        WindowStyle = "Normal"
    }
    
    Start-Process @processArgs
    Start-Sleep -Seconds 2
}

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python not found" -ForegroundColor Red
    exit 1
}

try {
    $nodeVersion = node --version 2>&1
    Write-Host "Node.js found: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "Node.js not found" -ForegroundColor Red
    exit 1
}

# Activate virtual environment and check packages
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv\Scripts\Activate.ps1") {
    & ".\.venv\Scripts\Activate.ps1"
    Write-Host "Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "Virtual environment not found, using global Python" -ForegroundColor Yellow
}

Write-Host ""

# Start backend services
Write-Host "Starting Backend Services..." -ForegroundColor Green
Start-Service "ASR Service" "uvicorn services.asr.app:app --host 127.0.0.1 --port 7031" 7031
Start-Service "Redaction Service" "uvicorn services.redaction.app:app --host 127.0.0.1 --port 7032" 7032
Start-Service "Note Builder" "uvicorn services.note_builder.app:app --host 127.0.0.1 --port 7034" 7034
Start-Service "Insights Bridge" "uvicorn services.insights_bridge.app:app --host 127.0.0.1 --port 7033" 7033

Write-Host ""
Write-Host "Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Test service health
Write-Host "Checking service health..." -ForegroundColor Green
$services = @(
    @{Name="ASR"; Url="http://127.0.0.1:7031/health"},
    @{Name="Redaction"; Url="http://127.0.0.1:7032/health"},
    @{Name="Note Builder"; Url="http://127.0.0.1:7034/health"},
    @{Name="Insights"; Url="http://127.0.0.1:7033/health"}
)

foreach ($service in $services) {
    try {
        $response = Invoke-RestMethod -Uri $service.Url -TimeoutSec 3 -ErrorAction Stop
        Write-Host "$($service.Name) service is healthy" -ForegroundColor Green
    } catch {
        Write-Host "$($service.Name) service not responding" -ForegroundColor Yellow
    }
}

Write-Host ""

# Start frontend
Write-Host "Starting Frontend..." -ForegroundColor Green

# Start React dev server
Write-Host "Starting React renderer..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command", 
    "cd '$rootPath'; pnpm -C apps/desktop/renderer dev"
) -WindowStyle Normal

Start-Sleep -Seconds 3

# Start Electron
Write-Host "Starting Electron main process..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$rootPath'; pnpm -C apps/desktop/electron dev"
) -WindowStyle Normal

Write-Host ""
Write-Host "SessionScribe is launching!" -ForegroundColor Green
Write-Host ""
Write-Host "Services running on:" -ForegroundColor Cyan
Write-Host "  ASR Service:        http://127.0.0.1:7031" -ForegroundColor Gray
Write-Host "  Redaction Service:  http://127.0.0.1:7032" -ForegroundColor Gray  
Write-Host "  Note Builder:       http://127.0.0.1:7034" -ForegroundColor Gray
Write-Host "  Insights Bridge:    http://127.0.0.1:7033" -ForegroundColor Gray
Write-Host "  React Dev Server:   http://127.0.0.1:3000" -ForegroundColor Gray
Write-Host ""
Write-Host "Output directory: $env:USERPROFILE\Documents\SessionScribe" -ForegroundColor Cyan
Write-Host ""
Write-Host "The Electron app should open automatically." -ForegroundColor Yellow
Write-Host "If not, check the Electron terminal for any errors." -ForegroundColor Yellow
Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor DarkGray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")