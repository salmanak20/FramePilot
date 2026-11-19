# FramePilot - one-click start for Windows.
# First run: installs Python and ffmpeg if missing (with winget), sets up a private Python folder (.venv)
# and desktop packages. Every run: opens FramePilot in its own window.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Say($msg, $color = "White") { Write-Host "  $msg" -ForegroundColor $color }
function Fail($msg) { Write-Host ""; Say $msg "Red"; Write-Host ""; exit 1 }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
function Has-Winget { [bool](Get-Command winget -ErrorAction SilentlyContinue) }

Write-Host ""
Say "=== FramePilot ===" "Green"
Write-Host ""

# ---- Long folder paths break the speech model on Windows (260 character limit)
if ($Root.Length -gt 80) {
    Say "This folder's path is long:" "Yellow"
    Say "  $Root" "Yellow"
    Say "If the speech model fails to load, move the folder to C:\FramePilot and run this again." "Yellow"
    Write-Host ""
}

# ---- Python 3.10+
function Find-Python {
    foreach ($cand in @("py -3.12", "py -3.11", "py -3.10", "py -3", "python")) {
        $parts = $cand -split " "
        $exe = $parts[0]; $args_ = @($parts | Select-Object -Skip 1)
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
        try {
            $ok = & $exe @args_ -c "import sys; print(1 if (3,10) <= sys.version_info[:2] < (3,14) else 0)" 2>$null
            if ($LASTEXITCODE -eq 0 -and "$ok".Trim() -eq "1") { return @($exe) + $args_ }
        } catch { }
    }
}

$Py = @(Find-Python)
if ($Py.Count -eq 0) {
    Say "Python 3.10-3.13 not found. Installing Python 3.12..." "Cyan"
    if (-not (Has-Winget)) {
        Start-Process "https://www.python.org/downloads/release/python-3129/"
        Fail "winget is not available. Install Python 3.12 from the page that just opened (tick 'Add python.exe to PATH'), then run this again."
    }
    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
    Refresh-Path
    $Py = @(Find-Python)
    if ($Py.Count -eq 0) { Fail "Python was installed but Windows has not picked it up yet. Close this window and double-click Start-FramePilot-Windows.bat again." }
}
$PyExe = $Py[0]; $PyArgs = @($Py | Select-Object -Skip 1)
Say ("Python: " + (& $PyExe @PyArgs --version)) "Gray"

# ---- Private Python folder + packages (only reinstalled when requirements.txt changes)
$Venv = Join-Path $Root ".venv"
$VPy = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $VPy)) {
    Say "Setting up (one time)..." "Cyan"
    & $PyExe @PyArgs -m venv $Venv
    if ($LASTEXITCODE -ne 0) { Fail "Could not create the Python environment." }
}
$Stamp = Join-Path $Venv "requirements.sha"
$Hash = (Get-FileHash (Join-Path $Root "requirements-desktop.txt") -Algorithm SHA256).Hash
if (-not (Test-Path $Stamp) -or (Get-Content $Stamp -Raw).Trim() -ne $Hash) {
    Say "Installing packages (one time, a few minutes)..." "Cyan"
    & $VPy -m pip install --upgrade pip --disable-pip-version-check -q
    & $VPy -m pip install -r requirements-desktop.txt --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) { Fail "Installing packages failed. Check your internet connection and run this again." }
    Set-Content -Path $Stamp -Value $Hash
}

# ---- Start the native desktop window
Write-Host ""
Say "Opening FramePilot. The first start downloads the speech model (about 480 MB, once)." "Green"
Say "Close the FramePilot window when you are finished." "Green"
Write-Host ""
$env:PYTHONWARNINGS = "ignore::DeprecationWarning"
& $VPy -m studio.desktop
