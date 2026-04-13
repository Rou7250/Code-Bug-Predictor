[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Stop-ProcessesSafe {
    param([string[]]$Names)

    foreach ($name in $Names) {
        $processes = @(Get-Process -Name $name -ErrorAction SilentlyContinue)

        if ($processes.Count -eq 0) {
            Write-Host "No running $name process found."
            continue
        }

        foreach ($process in $processes) {
            try {
                Stop-Process -Id $process.Id -Force -ErrorAction Stop
                Write-Host "Stopped $($process.ProcessName) (PID $($process.Id))."
            }
            catch {
                Write-Warning "Could not stop $($process.ProcessName) (PID $($process.Id)): $($_.Exception.Message)"
            }
        }
    }
}

function Remove-VenvSafe {
    param(
        [string]$ProjectRoot,
        [string]$RelativePath
    )

    $venvPath = Join-Path $ProjectRoot $RelativePath

    if (-not (Test-Path -LiteralPath $venvPath)) {
        Write-Host "No existing venv folder found."
        return
    }

    $projectRootFull = [System.IO.Path]::GetFullPath($ProjectRoot)
    $venvPathFull = [System.IO.Path]::GetFullPath($venvPath)
    $venvLeaf = Split-Path -Leaf $venvPathFull

    if (
        $venvLeaf -ne "venv" -or
        -not $venvPathFull.StartsWith($projectRootFull, [System.StringComparison]::OrdinalIgnoreCase)
    ) {
        throw "Refusing to delete unexpected path: $venvPathFull"
    }

    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            Remove-Item -LiteralPath $venvPathFull -Recurse -Force -ErrorAction Stop
            Write-Host "Deleted venv folder."
            return
        }
        catch {
            if ($attempt -eq 3) {
                throw
            }

            Write-Warning "Delete attempt $attempt failed. Retrying in 2 seconds..."
            Start-Sleep -Seconds 2
        }
    }
}

try {
    $projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    Set-Location -LiteralPath $projectRoot

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python was not found on PATH. Install Python, then run this script again."
    }

    $requirementsPath = Join-Path $projectRoot "requirements.txt"
    if (-not (Test-Path -LiteralPath $requirementsPath)) {
        throw "requirements.txt was not found in $projectRoot"
    }

    $backendModule = if (Test-Path -LiteralPath (Join-Path $projectRoot "backend.py")) {
        "backend:app"
    }
    else {
        throw "Could not find backend.py for the backend entrypoint."
    }

    $frontendScript = if (Test-Path -LiteralPath (Join-Path $projectRoot "frontend.py")) {
        "frontend.py"
    }
    else {
        throw "Could not find frontend.py for the frontend entrypoint."
    }

    Write-Step "Stopping Python-related processes"
    Stop-ProcessesSafe -Names @("python", "uvicorn", "streamlit")
    Start-Sleep -Seconds 2

    Write-Step "Removing old virtual environment"
    Remove-VenvSafe -ProjectRoot $projectRoot -RelativePath "venv"

    Write-Step "Creating a fresh virtual environment"
    & python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create the virtual environment."
    }

    $activateScript = Join-Path $projectRoot "venv\Scripts\Activate.ps1"
    $venvPython = Join-Path $projectRoot "venv\Scripts\python.exe"

    if (-not (Test-Path -LiteralPath $activateScript)) {
        throw "Activation script not found at $activateScript"
    }

    Write-Step "Activating venv"
    . $activateScript

    Write-Step "Installing dependencies"
    & $venvPython -m pip install -r $requirementsPath
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }

    Write-Step "Starting frontend in a new PowerShell window"
    $powershellExe = (Get-Command powershell.exe -ErrorAction SilentlyContinue).Source
    if (-not $powershellExe) {
        $powershellExe = Join-Path $PSHOME "powershell.exe"
    }

    $escapedProjectRoot = $projectRoot.Replace("'", "''")
    $escapedActivateScript = $activateScript.Replace("'", "''")
    $escapedFrontendScript = $frontendScript.Replace("'", "''")
    $frontendCommand = "& { Set-Location -LiteralPath '$escapedProjectRoot'; . '$escapedActivateScript'; streamlit run '$escapedFrontendScript' }"

    Start-Process -FilePath $powershellExe -ArgumentList @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-Command", $frontendCommand
    ) | Out-Null

    Write-Step "Starting backend in this window"
    Write-Host "Backend: uvicorn $backendModule --reload"
    Write-Host "Frontend: streamlit run $frontendScript"
    & $venvPython -m uvicorn $backendModule --reload
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
