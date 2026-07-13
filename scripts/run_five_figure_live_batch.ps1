param(
    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,
    [string]$SkillRoot = $null,
    [string]$PythonExe = $null
)

$ErrorActionPreference = "Stop"
if (-not $SkillRoot) { $SkillRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath) }
if (-not $PythonExe) {
    $PythonExe = (& py -3.10 -c "import sys; print(sys.executable)").Trim()
}
if (-not $PythonExe -or -not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    throw "E120_ENVIRONMENT_MISMATCH: Python 3.10 executable was not found."
}
$pythonVersion = (& $PythonExe -c "import platform; print(platform.python_version())").Trim()
if ($LASTEXITCODE -ne 0 -or -not $pythonVersion.StartsWith("3.10.")) {
    throw "E120_ENVIRONMENT_MISMATCH: five-figure live batch requires Python 3.10."
}
$figures = @("fig3", "fig12", "fig14", "fig15", "fig16")
$worker = Join-Path $SkillRoot "scripts\origin_candidate_worker.py"
$audit = Join-Path $SkillRoot "scripts\audit_five_figure_batch.py"
$preflight = Join-Path $SkillRoot "scripts\assert_admin_preflight.py"
$candidateRoot = Join-Path $SkillRoot "examples\candidates"

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdministrator)) {
    throw "E120_ENVIRONMENT_MISMATCH: run this batch from an elevated PowerShell process."
}

if (Test-Path -LiteralPath $OutputRoot) {
    if (-not (Test-Path -LiteralPath $OutputRoot -PathType Container)) {
        throw "E126_STALE_OUTPUT_ROOT: OutputRoot must be a new or empty directory."
    }
    $existingOutput = @(Get-ChildItem -LiteralPath $OutputRoot -Force)
    if ($existingOutput.Count -ne 0) {
        throw "E126_STALE_OUTPUT_ROOT: OutputRoot is not empty; use a new directory so old run artifacts cannot enter the batch."
    }
} else {
    New-Item -ItemType Directory -Path $OutputRoot | Out-Null
}

$adminPreflight = Join-Path $OutputRoot "admin_preflight.json"
& $PythonExe $preflight --json-out $adminPreflight
if ($LASTEXITCODE -ne 0) {
    throw "E120_ENVIRONMENT_MISMATCH: administrator preflight failed."
}

$origin = @(Get-Process -Name Origin64 -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 })
if ($origin.Count -ne 1) {
    throw "E121_ATTACH_POLICY_VIOLATION: exactly one visible Origin64 process is required."
}
$originPid = $origin[0].Id
$runs = @()
foreach ($figure in $figures) {
    $candidate = Join-Path $candidateRoot "$figure.json"
    $outputDir = Join-Path $OutputRoot $figure
    $stdout = Join-Path $OutputRoot "$figure.stdout.txt"
    $stderr = Join-Path $OutputRoot "$figure.stderr.txt"
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    $process = Start-Process -FilePath $PythonExe `
        -ArgumentList @($worker, "--figure", $figure, "--candidate", $candidate, "--output-dir", $outputDir, "--live") `
        -WorkingDirectory $SkillRoot `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -WindowStyle Hidden `
        -PassThru `
        -Wait
    $current = @(Get-Process -Name Origin64 -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 })
    $pidStable = $current.Count -eq 1 -and $current[0].Id -eq $originPid
    $runs += [ordered]@{
        figure = $figure
        exit_code = $process.ExitCode
        output_dir = $outputDir
        stdout = $stdout
        stderr = $stderr
        visible_origin_pid = if ($current.Count -eq 1) { $current[0].Id } else { $null }
        pid_stable = $pidStable
    }
    if (-not $pidStable) {
        break
    }
}

$batch = [ordered]@{
    schema = "originplot.five_figure_live_batch.v1"
    fresh_output_root_verified = $true
    admin_preflight = $adminPreflight
    python_executable = $PythonExe
    python_version = $pythonVersion
    started_visible_origin_pid = $originPid
    completed_at = (Get-Date).ToString("o")
    status = if ($runs.Count -eq 5 -and ($runs | Where-Object { -not $_.pid_stable }).Count -eq 0) { "completed" } else { "failed" }
    runs = $runs
}
$batch | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $OutputRoot "live_validation_status.json") -Encoding UTF8

& $PythonExe $audit --root $OutputRoot --json-out (Join-Path $OutputRoot "five_figure_batch_audit.json")
exit $LASTEXITCODE
