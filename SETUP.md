# SessionScribe Setup Guide

## Prerequisites

1. **Windows 10/11**
2. **Python 3.11+** - Download from [python.org](https://python.org)
3. **Node.js 18+** - Download from [nodejs.org](https://nodejs.org)  
4. **pnpm** - Install with: `npm install -g pnpm`

## PowerShell Setup

If you encounter PowerShell execution policy errors, run this command as Administrator:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Quick Start

### Option 1: Auto-Approve Workflow (Recommended for Development)

1. **Start the auto-approver:**
   ```powershell
   .\scripts\AutoApprove-Commands.ps1 -Root "G:\Projects\SessionScribe"
   ```

2. **In another terminal, run development setup:**
   ```powershell
   .\scripts\dev.ps1
   ```

### Option 2: Manual Setup

1. **Install dependencies:**
   ```bash
   pnpm install
   pip install -r requirements-test.txt
   ```

2. **Start services:**
   ```bash
   # Terminal 1: All services
   make dev
   
   # Terminal 2: React renderer
   pnpm -C apps/desktop/renderer dev
   
   # Terminal 3: Electron main
   pnpm -C apps/desktop/electron dev
   ```

### Option 3: Batch File (Windows)

Simply double-click `start-dev.bat` or run:
```cmd
start-dev.bat
```

## Environment Configuration

1. **Copy environment file:**
   ```bash
   copy .env.example .env
   ```

2. **Edit `.env` with your settings:**
   ```env
   OPENAI_API_KEY=your_api_key_here
   SS_OFFLINE=false
   SS_OUTPUT_DIR=%USERPROFILE%\Documents\SessionScribe
   ```

## Troubleshooting

### Python Issues
- Ensure Python is in PATH: `python --version`
- Install required packages: `pip install fastapi uvicorn`

### Node.js Issues  
- Ensure Node.js is in PATH: `node --version`
- Install pnpm globally: `npm install -g pnpm`

### PowerShell Issues
- Check execution policy: `Get-ExecutionPolicy`
- Allow scripts: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Port Conflicts
Services run on these ports:
- ASR Service: 7031
- Redaction Service: 7032  
- Insights Bridge: 7033
- Note Builder: 7034
- React Dev Server: 3000

## File Outputs

SessionScribe saves files to `%USERPROFILE%\Documents\SessionScribe\`:
- `session_*_audio.wav` - Stereo audio recording
- `session_*_original.txt` - Raw transcript
- `session_*_redacted.txt` - PHI-redacted transcript  
- `session_*_note.txt` - Clinical DAP note

## Testing

```bash
# Run all tests
make test

# Python unit tests only
pytest

# React component tests only  
pnpm -C apps/desktop/renderer test

# End-to-end tests
pnpm -C apps/desktop/renderer e2e
```

## Building for Production

```bash
# Build everything
make build

# Create Windows installer
pnpm -C apps/desktop/electron build
```

The installer will be created in `apps/desktop/electron/dist-installer/`.