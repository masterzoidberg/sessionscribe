# SessionScribe Health Check
Write-Host "SessionScribe Health Check" -ForegroundColor Green
Write-Host ""

$services = @(
    @{Name="ASR Service"; Port=7031},
    @{Name="Redaction Service"; Port=7032},
    @{Name="Insights Bridge"; Port=7033},
    @{Name="Note Builder"; Port=7034}
)

$allHealthy = $true

foreach ($service in $services) {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:$($service.Port)/health" -TimeoutSec 3 -ErrorAction Stop
        Write-Host "$($service.Name): " -NoNewline
        Write-Host "HEALTHY" -ForegroundColor Green
    } catch {
        Write-Host "$($service.Name): " -NoNewline
        Write-Host "NOT RESPONDING" -ForegroundColor Red
        $allHealthy = $false
    }
}

Write-Host ""

# Check Vite dev server
try {
    $viteResponse = Invoke-WebRequest -Uri "http://127.0.0.1:3000" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "Vite Dev Server: " -NoNewline
    Write-Host "RUNNING" -ForegroundColor Green
} catch {
    Write-Host "Vite Dev Server: " -NoNewline
    Write-Host "NOT RUNNING" -ForegroundColor Red
    $allHealthy = $false
}

Write-Host ""

if ($allHealthy) {
    Write-Host "All services are healthy!" -ForegroundColor Green
    Write-Host "SessionScribe is ready to use." -ForegroundColor Green
} else {
    Write-Host "Some services are not responding." -ForegroundColor Yellow
    Write-Host "Try running fix-and-launch.ps1 to restart services." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Service URLs:" -ForegroundColor Cyan
foreach ($service in $services) {
    Write-Host "  $($service.Name): http://127.0.0.1:$($service.Port)/health" -ForegroundColor Gray
}
Write-Host "  Vite Dev Server: http://127.0.0.1:3000" -ForegroundColor Gray