# SessionScribe Deployment Readiness Assessment
# Orchestrates discovery, runtime checks, and artifact capture

param(
    [switch]$SkipRuntime,
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

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

function New-AssessmentDir {
    param([string]$Path)
    if (!(Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

# Create assessment directories
New-AssessmentDir "docs/observability/baseline"
New-AssessmentDir "docs/security"
New-AssessmentDir "docs/assessment"

Write-Status "SessionScribe Deployment Readiness Assessment" "INFO"
Write-Status "Starting comprehensive evaluation..." "INFO"

# 1. Repo Discovery & Delta Map
Write-Status "=== 1. REPO DISCOVERY ===" "INFO"

Write-Status "Generating repository inventory..."
$repoTree = @"
## Repository Structure
$(tree /f /a 2>$null | Out-String)
"@

$repoTree | Out-File "docs/assessment/repo_tree.txt" -Encoding UTF8

# Python dependencies
Write-Status "Inventorying Python dependencies..."
try {
    $pythonDeps = @()
    Get-ChildItem -Recurse -Name "requirements*.txt", "pyproject.toml", "setup.py" | ForEach-Object {
        $pythonDeps += "Found: $_"
    }
    $pythonDeps -join "`n" | Out-File "docs/assessment/python_deps.txt" -Encoding UTF8
    Write-Status "Python dependencies captured" "SUCCESS"
} catch {
    Write-Status "Failed to inventory Python dependencies: $($_.Exception.Message)" "WARNING"
}

# Node.js dependencies
Write-Status "Inventorying Node.js dependencies..."
try {
    $nodeDeps = @()
    Get-ChildItem -Recurse -Name "package.json" | ForEach-Object {
        $nodeDeps += "Found: $_"
        $content = Get-Content $_ -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($content.name) {
            $nodeDeps += "  Name: $($content.name)"
            $nodeDeps += "  Version: $($content.version)"
        }
        $nodeDeps += ""
    }
    $nodeDeps -join "`n" | Out-File "docs/assessment/node_deps.txt" -Encoding UTF8
    Write-Status "Node.js dependencies captured" "SUCCESS"
} catch {
    Write-Status "Failed to inventory Node.js dependencies: $($_.Exception.Message)" "WARNING"
}

# Extract IPC contracts
Write-Status "Extracting IPC contracts..."
try {
    $ipcContracts = @()
    if (Test-Path "apps/desktop/electron/src/preload") {
        Get-ChildItem -Recurse "apps/desktop/electron/src/preload" -Filter "*.ts" | ForEach-Object {
            $content = Get-Content $_.FullName -Raw
            if ($content -match "contextBridge\.exposeInMainWorld|ipcRenderer\.invoke") {
                $ipcContracts += "File: $($_.FullName)"
                $ipcContracts += $content
                $ipcContracts += "---"
            }
        }
    }
    $ipcContracts -join "`n" | Out-File "docs/assessment/ipc_contracts.txt" -Encoding UTF8
    Write-Status "IPC contracts extracted" "SUCCESS"
} catch {
    Write-Status "Failed to extract IPC contracts: $($_.Exception.Message)" "WARNING"
}

# Extract HTTP routes
Write-Status "Extracting HTTP routes..."
try {
    $httpRoutes = @()
    Get-ChildItem -Recurse "services" -Filter "*.py" | ForEach-Object {
        $content = Get-Content $_.FullName -Raw
        if ($content -match "@app\.(get|post|put|delete)\(") {
            $httpRoutes += "File: $($_.FullName)"
            # Extract route definitions
            $matches = [regex]::Matches($content, '@app\.(get|post|put|delete)\([^)]+\)')
            foreach ($match in $matches) {
                $httpRoutes += "  Route: $($match.Value)"
            }
            $httpRoutes += "---"
        }
    }
    $httpRoutes -join "`n" | Out-File "docs/assessment/http_routes.txt" -Encoding UTF8
    Write-Status "HTTP routes extracted" "SUCCESS"
} catch {
    Write-Status "Failed to extract HTTP routes: $($_.Exception.Message)" "WARNING"
}

if ($SkipRuntime) {
    Write-Status "Skipping runtime validation (--SkipRuntime specified)" "WARNING"
} else {
    # 2. Runtime Validation
    Write-Status "=== 2. RUNTIME VALIDATION ===" "INFO"
    
    Write-Status "Checking if services are already running..."
    $runningServices = @()
    $ports = @(7032, 7033, 7034, 7035)
    
    foreach ($port in $ports) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:$port/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                $runningServices += $port
                Write-Status "Service on port $port is running" "SUCCESS"
            }
        } catch {
            # Service not running, which is expected
        }
    }
    
    if ($runningServices.Count -gt 0) {
        Write-Status "Found running services on ports: $($runningServices -join ', ')" "INFO"
    } else {
        Write-Status "No services currently running, would need to start stack" "WARNING"
    }
    
    # Health check collection
    Write-Status "Collecting health status from running services..."
    $healthResults = @()
    foreach ($port in $runningServices) {
        try {
            # Try /v1/health first, fallback to /health
            $healthUrl = "http://127.0.0.1:$port/v1/health"
            try {
                $response = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 5
                $healthResults += "=== Port $port (/v1/health) ==="
            } catch {
                $healthUrl = "http://127.0.0.1:$port/health"
                $response = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 5
                $healthResults += "=== Port $port (/health) ==="
            }
            
            $healthResults += "Status: $($response.StatusCode)"
            $healthResults += "Content: $($response.Content)"
            $healthResults += ""
        } catch {
            $healthResults += "=== Port $port ==="
            $healthResults += "ERROR: $($_.Exception.Message)"
            $healthResults += ""
        }
    }
    $healthResults -join "`n" | Out-File "docs/observability/baseline/health_responses.txt" -Encoding UTF8
    
    # Metrics collection
    Write-Status "Collecting metrics from running services..."
    $metricsResults = @()
    foreach ($port in $runningServices) {
        try {
            # Try /v1/metrics first, fallback to /metrics
            $metricsUrl = "http://127.0.0.1:$port/v1/metrics"
            try {
                $response = Invoke-WebRequest -Uri $metricsUrl -TimeoutSec 5
                $metricsResults += "=== Port $port (/v1/metrics) ==="
            } catch {
                $metricsUrl = "http://127.0.0.1:$port/metrics"
                $response = Invoke-WebRequest -Uri $metricsUrl -TimeoutSec 5
                $metricsResults += "=== Port $port (/metrics) ==="
            }
            
            $metricsResults += "Status: $($response.StatusCode)"
            $metricsResults += "Content: $($response.Content)"
            $metricsResults += ""
        } catch {
            $metricsResults += "=== Port $port ==="
            $metricsResults += "ERROR: $($_.Exception.Message)"
            $metricsResults += ""
        }
    }
    $metricsResults -join "`n" | Out-File "docs/observability/baseline/metrics_responses.txt" -Encoding UTF8
}

# 3. Security & PHI Posture
Write-Status "=== 3. SECURITY & PHI POSTURE ===" "INFO"

Write-Status "Analyzing security configuration..."

# Check for secrets in code
Write-Status "Scanning for hardcoded secrets..."
try {
    $secretPatterns = @(
        "api[_-]?key\s*=\s*['\"][^'\"]+['\"]",
        "password\s*=\s*['\"][^'\"]+['\"]",
        "secret\s*=\s*['\"][^'\"]+['\"]",
        "token\s*=\s*['\"][^'\"]+['\"]"
    )
    
    $secretFindings = @()
    Get-ChildItem -Recurse -Include "*.py", "*.js", "*.ts" | ForEach-Object {
        $content = Get-Content $_.FullName -Raw
        foreach ($pattern in $secretPatterns) {
            $matches = [regex]::Matches($content, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
            foreach ($match in $matches) {
                $secretFindings += "File: $($_.FullName)"
                $secretFindings += "Pattern: $($match.Value)"
                $secretFindings += "---"
            }
        }
    }
    
    if ($secretFindings.Count -gt 0) {
        $secretFindings -join "`n" | Out-File "docs/security/secret_scan_findings.txt" -Encoding UTF8
        Write-Status "Found potential hardcoded secrets - see docs/security/secret_scan_findings.txt" "WARNING"
    } else {
        "No hardcoded secrets found" | Out-File "docs/security/secret_scan_findings.txt" -Encoding UTF8
        Write-Status "No hardcoded secrets detected" "SUCCESS"
    }
} catch {
    Write-Status "Failed to scan for secrets: $($_.Exception.Message)" "ERROR"
}

# Check credential manager usage
Write-Status "Checking credential manager integration..."
try {
    $credentialUsage = @()
    Get-ChildItem -Recurse -Include "*.py", "*.js", "*.ts" | ForEach-Object {
        $content = Get-Content $_.FullName -Raw
        if ($content -match "keytar|keyring|credential_manager") {
            $credentialUsage += "File: $($_.FullName)"
            $credentialUsage += "Uses credential manager: YES"
            $credentialUsage += "---"
        }
    }
    $credentialUsage -join "`n" | Out-File "docs/security/credential_usage.txt" -Encoding UTF8
    Write-Status "Credential manager usage documented" "SUCCESS"
} catch {
    Write-Status "Failed to check credential manager usage: $($_.Exception.Message)" "WARNING"
}

# 4. Quality, Tests, Build
Write-Status "=== 4. QUALITY, TESTS, BUILD ===" "INFO"

# Check for test files
Write-Status "Inventorying test files..."
try {
    $testFiles = @()
    Get-ChildItem -Recurse -Include "*test*.py", "*test*.js", "*test*.ts", "test_*.py" | ForEach-Object {
        $testFiles += $_.FullName
    }
    $testFiles -join "`n" | Out-File "docs/assessment/test_inventory.txt" -Encoding UTF8
    Write-Status "Found $($testFiles.Count) test files" "INFO"
} catch {
    Write-Status "Failed to inventory test files: $($_.Exception.Message)" "WARNING"
}

# Check build configurations
Write-Status "Checking build configurations..."
try {
    $buildConfigs = @()
    Get-ChildItem -Recurse -Include "*.json", "*.toml", "*.cfg", "*.ini" | Where-Object { 
        $_.Name -match "(build|config|setup|package)" 
    } | ForEach-Object {
        $buildConfigs += $_.FullName
    }
    $buildConfigs -join "`n" | Out-File "docs/assessment/build_configs.txt" -Encoding UTF8
    Write-Status "Build configurations documented" "SUCCESS"
} catch {
    Write-Status "Failed to check build configurations: $($_.Exception.Message)" "WARNING"
}

Write-Status "=== ASSESSMENT COMPLETE ===" "SUCCESS"
Write-Status "Results saved to docs/assessment/ and docs/observability/baseline/" "INFO"
Write-Status "Next: Run 'python scripts/generate_report.py' to synthesize findings" "INFO"