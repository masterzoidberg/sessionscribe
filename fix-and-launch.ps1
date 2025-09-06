# SessionScribe Fix and Launch Script
Write-Host "SessionScribe Fix and Launch" -ForegroundColor Green

$ErrorActionPreference = "Continue"

# Step 1: Kill stale servers
Write-Host "1. Killing stale uvicorn processes..." -ForegroundColor Yellow
taskkill /F /IM uvicorn.exe 2>$null
Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*uvicorn*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "   Stale processes killed" -ForegroundColor Green

# Step 2: Setup pnpm
Write-Host "2. Setting up pnpm..." -ForegroundColor Yellow
try {
    corepack enable
    corepack prepare pnpm@9 --activate
    Write-Host "   pnpm setup complete" -ForegroundColor Green
} catch {
    Write-Host "   pnpm setup failed, continuing with existing version" -ForegroundColor Yellow
}

# Step 3: Install dependencies
Write-Host "3. Installing dependencies..." -ForegroundColor Yellow
try {
    Set-Location "apps/desktop/electron"
    pnpm install
    Set-Location "../../.."
    
    Set-Location "apps/desktop/renderer"
    pnpm install
    Set-Location "../../.."
    
    Write-Host "   Dependencies installed" -ForegroundColor Green
} catch {
    Write-Host "   Error installing dependencies: $($_.Exception.Message)" -ForegroundColor Red
}

# Step 4: Build Electron components
Write-Host "4. Building Electron components..." -ForegroundColor Yellow
try {
    pnpm dlx esbuild apps/desktop/electron/main.ts --bundle --platform=node --external:electron --outfile=apps/desktop/electron/main.js
    pnpm dlx esbuild apps/desktop/electron/preload.ts --bundle --platform=node --external:electron --outfile=apps/desktop/electron/preload.js
    Write-Host "   Electron build complete" -ForegroundColor Green
} catch {
    Write-Host "   Error building Electron: $($_.Exception.Message)" -ForegroundColor Red
}

# Step 5: Start services
Write-Host "5. Starting backend services..." -ForegroundColor Yellow

$services = @(
    @{Name="ASR"; Port=7031; Module="services.asr.app:app"},
    @{Name="Redaction"; Port=7032; Module="services.redaction.app:app"},
    @{Name="Insights"; Port=7033; Module="services.insights_bridge.app:app"},
    @{Name="Note Builder"; Port=7034; Module="services.note_builder.app:app"}
)

foreach ($service in $services) {
    Write-Host "   Starting $($service.Name) service on port $($service.Port)..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList @(
        "-NoExit",
        "-Command",
        "cd '$PWD'; python -m uvicorn $($service.Module) --host 127.0.0.1 --port $($service.Port) --reload"
    ) -WindowStyle Normal
    Start-Sleep -Seconds 1
}

# Step 6: Wait and health check
Write-Host "6. Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 8

Write-Host "7. Checking service health..." -ForegroundColor Yellow
foreach ($service in $services) {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:$($service.Port)/health" -TimeoutSec 3 -ErrorAction Stop
        Write-Host "   $($service.Name) service: HEALTHY" -ForegroundColor Green
    } catch {
        Write-Host "   $($service.Name) service: NOT RESPONDING" -ForegroundColor Red
    }
}

# Step 8: Start frontend
Write-Host "8. Starting frontend..." -ForegroundColor Yellow

Write-Host "   Starting Vite dev server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$PWD'; pnpm -C apps/desktop/renderer run dev"
) -WindowStyle Normal

Start-Sleep -Seconds 3

Write-Host "   Starting Electron app..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", 
    "-Command",
    "cd '$PWD'; pnpm dlx electron apps/desktop/electron/main.js --user-data-dir='$PWD\.electron-user'"
) -WindowStyle Normal

# Summary
Write-Host ""
Write-Host "SessionScribe Launch Complete!" -ForegroundColor Green
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  ASR:        http://127.0.0.1:7031/health" -ForegroundColor Gray
Write-Host "  Redaction:  http://127.0.0.1:7032/health" -ForegroundColor Gray
Write-Host "  Insights:   http://127.0.0.1:7033/health" -ForegroundColor Gray
Write-Host "  Note Builder: http://127.0.0.1:7034/health" -ForegroundColor Gray
Write-Host "Frontend:" -ForegroundColor Cyan
Write-Host "  Vite Dev:   http://127.0.0.1:3000" -ForegroundColor Gray
Write-Host "  Electron:   Desktop app should open" -ForegroundColor Gray
Write-Host ""
Write-Host "Output Directory: $env:USERPROFILE\Documents\SessionScribe" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to continue..." -ForegroundColor DarkGray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")