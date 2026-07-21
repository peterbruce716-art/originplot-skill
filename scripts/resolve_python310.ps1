param(
    [string]$PythonExe = $null
)

$ErrorActionPreference = "Stop"
$candidates = [System.Collections.Generic.List[string]]::new()
if ($PythonExe) {
    $candidates.Add($PythonExe)
} else {
    try {
        $launcherResult = (& py -3.10 -c "import sys; print(sys.executable)" 2>$null).Trim()
        if ($LASTEXITCODE -eq 0 -and $launcherResult) {
            $candidates.Add($launcherResult)
        }
    } catch {
        # Continue to deterministic installation paths.
    }
    if ($env:LOCALAPPDATA) {
        $candidates.Add((Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"))
    }
    if ($env:ProgramFiles) {
        $candidates.Add((Join-Path $env:ProgramFiles "Python310\python.exe"))
    }
}

foreach ($candidate in $candidates) {
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        continue
    }
    $resolved = (Resolve-Path -LiteralPath $candidate).Path
    $version = (& $resolved -c "import platform; print(platform.python_version())").Trim()
    if ($LASTEXITCODE -eq 0 -and $version.StartsWith("3.10.")) {
        Write-Output $resolved
        exit 0
    }
}

throw "E120_ENVIRONMENT_MISMATCH: Python 3.10 executable was not found."
