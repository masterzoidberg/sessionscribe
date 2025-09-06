param(
    [Parameter(Mandatory=$true)]
    [string]$Root
)

# SessionScribe Auto-Approve Commands Script
Write-Host "Starting auto-approve watcher for SessionScribe..." -ForegroundColor Green
Write-Host "Root directory: $Root" -ForegroundColor Cyan

$queueFile = Join-Path $Root "scripts\commands.todo"

# Ensure the queue file exists
if (!(Test-Path $queueFile)) {
    New-Item -ItemType File -Path $queueFile -Force | Out-Null
    Write-Host "Created commands queue file: $queueFile" -ForegroundColor Yellow
}

$processedCommands = @{}
$lastFileWrite = (Get-Item $queueFile).LastWriteTime

Write-Host "Monitoring commands queue: $queueFile" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop..." -ForegroundColor Yellow
Write-Host ""

while ($true) {
    try {
        $currentFileWrite = (Get-Item $queueFile).LastWriteTime
        
        if ($currentFileWrite -gt $lastFileWrite) {
            $lastFileWrite = $currentFileWrite
            
            $commands = Get-Content $queueFile -ErrorAction SilentlyContinue
            
            if ($null -ne $commands -and $commands.Count -gt 0) {
                foreach ($command in $commands) {
                    $command = $command.Trim()
                    
                    # Skip empty lines and already processed commands
                    if ([string]::IsNullOrWhiteSpace($command) -or $processedCommands.ContainsKey($command)) {
                        continue
                    }
                    
                    Write-Host "Executing: $command" -ForegroundColor Cyan
                    
                    try {
                        # Set location to root directory
                        Push-Location $Root
                        
                        # Execute command based on type
                        if ($command.StartsWith("mkdir")) {
                            # Handle mkdir commands (convert -p to -Force for Windows)
                            $dirPath = $command -replace "mkdir -p ", "" -replace "mkdir ", ""
                            New-Item -ItemType Directory -Path $dirPath -Force | Out-Null
                            Write-Host "   Directory created: $dirPath" -ForegroundColor Green
                        }
                        elseif ($command.StartsWith("pip install")) {
                            # Handle pip install commands
                            Invoke-Expression $command
                            Write-Host "   Pip install completed" -ForegroundColor Green
                        }
                        elseif ($command.StartsWith("pnpm") -or $command.StartsWith("npm")) {
                            # Handle pnpm/npm commands
                            Invoke-Expression $command
                            Write-Host "   Package manager command completed" -ForegroundColor Green
                        }
                        else {
                            # Handle other commands
                            Invoke-Expression $command
                            Write-Host "   Command executed successfully" -ForegroundColor Green
                        }
                        
                        # Mark as processed
                        $processedCommands[$command] = $true
                        
                    } catch {
                        Write-Host "   Error executing command: $($_.Exception.Message)" -ForegroundColor Red
                    } finally {
                        Pop-Location
                    }
                    
                    Start-Sleep -Milliseconds 500
                }
            }
        }
        
        Start-Sleep -Seconds 1
        
    } catch {
        Write-Host "Error monitoring queue file: $($_.Exception.Message)" -ForegroundColor Red
        Start-Sleep -Seconds 5
    }
}