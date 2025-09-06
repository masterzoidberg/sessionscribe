@echo off
echo Starting SessionScribe Development Environment...

REM Check if PowerShell execution policy allows scripts
powershell -Command "if ((Get-ExecutionPolicy) -eq 'Restricted') { Write-Host 'PowerShell execution policy is restricted. Run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser' -ForegroundColor Red; pause; exit 1 }"

REM Run the PowerShell development script
powershell -ExecutionPolicy Bypass -File "scripts\dev.ps1"

pause