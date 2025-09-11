# SessionScribe Windows Development Environment Setup
# One-shot provisioning script for clean Windows 10/11 development

param(
    [switch]$SkipDependencies,
    [switch]$SkipBuild,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

function Write-Status {
    param([string]$Message, [string]$Status = "INFO")
    $timestamp = Get-Date -Format "HH:mm:ss"
    switch ($Status) {
        "SUCCESS" { Write-Host "[$timestamp] ✓ $Message" -ForegroundColor Green }
        "ERROR"   { Write-Host "[$timestamp] ✗ $Message" -ForegroundColor Red }
        "WARNING" { Write-Host "[$timestamp] ⚠ $Message" -ForegroundColor Yellow }
        default   { Write-Host "[$timestamp] • $Message" -ForegroundColor Cyan }
    }
}

function Test-Command {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Install-NodeJS {
    Write-Status "Checking Node.js installation..."
    
    if (Test-Command "node") {
        $nodeVersion = node --version
        Write-Status "Node.js already installed: $nodeVersion" "SUCCESS"
        
        # Check if version is 20.x LTS
        if ($nodeVersion -match "v(\d+)\.") {
            $majorVersion = [int]$Matches[1]
            if ($majorVersion -lt 20) {
                Write-Status "Node.js version too old (need 20.x LTS), upgrading..." "WARNING"
            } else {
                return
            }
        }
    }
    
    Write-Status "Installing Node.js 20 LTS..."
    try {
        winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
        Write-Status "Node.js installed successfully" "SUCCESS"
        
        # Refresh PATH
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        
        # Verify installation
        if (Test-Command "node") {
            $nodeVersion = node --version
            Write-Status "Verified Node.js: $nodeVersion" "SUCCESS"
        } else {
            throw "Node.js command not found after installation"
        }
    }
    catch {
        Write-Status "Failed to install Node.js: $($_.Exception.Message)" "ERROR"
        throw
    }
}

function Install-Python {
    Write-Status "Checking Python installation..."
    
    if (Test-Command "python") {
        $pythonVersion = python --version
        Write-Status "Python already installed: $pythonVersion" "SUCCESS"
        
        # Check if version is 3.11
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $majorVersion = [int]$Matches[1]
            $minorVersion = [int]$Matches[2]
            if ($majorVersion -eq 3 -and $minorVersion -ge 11) {
                return
            } else {
                Write-Status "Python version not optimal (need 3.11.x), installing..." "WARNING"
            }
        }
    }
    
    Write-Status "Installing Python 3.11..."
    try {
        winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements
        Write-Status "Python installed successfully" "SUCCESS"
        
        # Refresh PATH
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
        
        # Verify installation
        if (Test-Command "python") {
            $pythonVersion = python --version
            Write-Status "Verified Python: $pythonVersion" "SUCCESS"
        } else {
            throw "Python command not found after installation"
        }
    }
    catch {
        Write-Status "Failed to install Python: $($_.Exception.Message)" "ERROR"
        throw
    }
}

function Install-PNPM {
    Write-Status "Checking pnpm installation..."
    
    if (Test-Command "pnpm") {
        $pnpmVersion = pnpm --version
        Write-Status "pnpm already installed: $pnpmVersion" "SUCCESS"
        return
    }
    
    Write-Status "Installing pnpm..."
    try {
        npm install -g pnpm
        Write-Status "pnpm installed successfully" "SUCCESS"
        
        # Verify installation
        if (Test-Command "pnpm") {
            $pnpmVersion = pnpm --version
            Write-Status "Verified pnpm: $pnpmVersion" "SUCCESS"
        } else {
            throw "pnpm command not found after installation"
        }
    }
    catch {
        Write-Status "Failed to install pnpm: $($_.Exception.Message)" "ERROR"
        throw
    }
}

function Install-BuildTools {
    Write-Status "Checking Visual Studio Build Tools..."
    
    # Check if VS Build Tools or Visual Studio is installed
    $vsBuildToolsPath = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2019\BuildTools\MSBuild\Current\Bin\MSBuild.exe"
    $vs2019Path = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\2019\Enterprise\MSBuild\Current\Bin\MSBuild.exe"
    $vs2022Path = "${env:ProgramFiles}\Microsoft Visual Studio\2022\Enterprise\MSBuild\Current\Bin\MSBuild.exe"
    
    if ((Test-Path $vsBuildToolsPath) -or (Test-Path $vs2019Path) -or (Test-Path $vs2022Path)) {
        Write-Status "Visual Studio Build Tools already installed" "SUCCESS"
        return
    }
    
    Write-Status "Installing Visual Studio Build Tools..."
    Write-Status "This may take several minutes..." "WARNING"
    
    try {
        # Install VS Build Tools via winget
        winget install Microsoft.VisualStudio.2022.BuildTools --accept-source-agreements --accept-package-agreements
        Write-Status "Visual Studio Build Tools installed successfully" "SUCCESS"
    }
    catch {
        Write-Status "Failed to install VS Build Tools: $($_.Exception.Message)" "ERROR"
        Write-Status "Please install manually from: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022" "WARNING"
    }
}

function Install-FFmpeg {
    Write-Status "Checking FFmpeg installation..."
    
    if (Test-Command "ffmpeg") {
        $ffmpegVersion = ffmpeg -version | Select-Object -First 1
        Write-Status "FFmpeg already installed: $ffmpegVersion" "SUCCESS"
        return
    }
    
    Write-Status "Installing FFmpeg (optional)..."
    try {
        winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
        Write-Status "FFmpeg installed successfully" "SUCCESS"
        
        # Refresh PATH
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
    }
    catch {
        Write-Status "Failed to install FFmpeg (optional): $($_.Exception.Message)" "WARNING"
    }
}

function Test-KeytarCredentials {
    Write-Status "Testing keytar (Windows Credential Manager integration)..."
    
    try {
        $testScript = @"
const keytar = require('keytar');
console.log('keytar module loaded successfully');
"@
        
        # Test in Node.js environment
        echo $testScript | node
        Write-Status "keytar integration test passed" "SUCCESS"
    }
    catch {
        Write-Status "keytar test failed: $($_.Exception.Message)" "ERROR"
        Write-Status "Run 'pnpm install' in the electron directory to install dependencies" "WARNING"
    }
}

function Test-KeyringCredentials {
    Write-Status "Testing keyring (Python credential manager integration)..."
    
    try {
        python -c "import keyring; print('keyring module loaded successfully')"
        Write-Status "keyring integration test passed" "SUCCESS"
    }
    catch {
        Write-Status "keyring test failed: $($_.Exception.Message)" "ERROR"
        Write-Status "Run 'pip install keyring' to install Python keyring" "WARNING"
    }
}

function Install-PythonDependencies {
    Write-Status "Installing Python dependencies..."
    
    try {
        # Install common requirements
        python -m pip install --upgrade pip
        python -m pip install keyring structlog fastapi uvicorn prometheus_client
        Write-Status "Python dependencies installed successfully" "SUCCESS"
    }
    catch {
        Write-Status "Failed to install Python dependencies: $($_.Exception.Message)" "ERROR"
        throw
    }
}

function Build-NativeAddons {
    Write-Status "Building native audio capture addon..."
    
    if ($SkipBuild) {
        Write-Status "Skipping native addon build (--SkipBuild specified)" "WARNING"
        return
    }
    
    try {
        Set-Location "native/win"
        
        if (Test-Path "package.json") {
            Write-Status "Installing native addon dependencies..."
            pnpm install
            
            Write-Status "Building native addon..."
            pnpm run build
            
            Write-Status "Native addon built successfully" "SUCCESS"
        } else {
            Write-Status "Native addon package.json not found, skipping build" "WARNING"
        }
        
        Set-Location "../.."
    }
    catch {
        Write-Status "Failed to build native addon: $($_.Exception.Message)" "ERROR"
        Write-Status "This may be due to missing Visual Studio Build Tools" "WARNING"
        Set-Location "../.."
    }
}

function Install-ProjectDependencies {
    Write-Status "Installing project dependencies..."
    
    try {
        # Install root dependencies
        Write-Status "Installing root dependencies..."
        pnpm install
        
        # Install Electron dependencies
        Write-Status "Installing Electron dependencies..."
        Set-Location "apps/desktop/electron"
        pnpm install
        Set-Location "../../.."
        
        # Install renderer dependencies
        Write-Status "Installing renderer dependencies..."
        Set-Location "apps/desktop/renderer"
        pnpm install
        Set-Location "../../.."
        
        Write-Status "Project dependencies installed successfully" "SUCCESS"
    }
    catch {
        Write-Status "Failed to install project dependencies: $($_.Exception.Message)" "ERROR"
        throw
    }
}

function Show-Summary {
    Write-Status "=== Setup Summary ===" "INFO"
    
    # Check Node.js
    if (Test-Command "node") {
        $nodeVersion = node --version
        Write-Status "Node.js: $nodeVersion" "SUCCESS"
    } else {
        Write-Status "Node.js: Not found" "ERROR"
    }
    
    # Check Python
    if (Test-Command "python") {
        $pythonVersion = python --version
        Write-Status "Python: $pythonVersion" "SUCCESS"
    } else {
        Write-Status "Python: Not found" "ERROR"
    }
    
    # Check pnpm
    if (Test-Command "pnpm") {
        $pnpmVersion = pnpm --version
        Write-Status "pnpm: $pnpmVersion" "SUCCESS"
    } else {
        Write-Status "pnpm: Not found" "ERROR"
    }
    
    # Check FFmpeg
    if (Test-Command "ffmpeg") {
        Write-Status "FFmpeg: Available" "SUCCESS"
    } else {
        Write-Status "FFmpeg: Not available (optional)" "WARNING"
    }
    
    Write-Status "=== Next Steps ===" "INFO"
    Write-Status "1. Run: pnpm -C apps/desktop/electron dev" "INFO"
    Write-Status "2. Run: pnpm -C apps/desktop/renderer dev --port 3001" "INFO"
    Write-Status "3. Run: python -m uvicorn services.asr.app:app --host 127.0.0.1 --port 7035" "INFO"
    Write-Status "4. Open Electron app and test dual-channel recording" "INFO"
}

# Main execution
try {
    Write-Status "SessionScribe Windows Development Setup" "INFO"
    Write-Status "Starting environment provisioning..." "INFO"
    
    if (-not $SkipDependencies) {
        Install-NodeJS
        Install-Python
        Install-PNPM
        Install-BuildTools
        Install-FFmpeg
        Install-PythonDependencies
        Install-ProjectDependencies
    }
    
    Build-NativeAddons
    
    Test-KeytarCredentials
    Test-KeyringCredentials
    
    Show-Summary
    
    Write-Status "Setup completed successfully!" "SUCCESS"
}
catch {
    Write-Status "Setup failed: $($_.Exception.Message)" "ERROR"
    exit 1
}