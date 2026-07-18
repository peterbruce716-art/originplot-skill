param(
    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,
    [ValidateSet("fresh_extract", "validated_reuse", "validated_crop_reextract")]
    [string]$SourceDataPolicy = "fresh_extract",
    [string]$SourcePdf = $null,
    [string]$ReuseBatchRoot = $null,
    [string]$SkillRoot = $null,
    [string]$PythonExe = $null,
    [string]$LaunchOriginExe = $null
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
$extractor = Join-Path $SkillRoot "scripts\extract_aa2195_fresh_source_bundle.py"
$reuseBuilder = Join-Path $SkillRoot "scripts\build_validated_data_reuse_record.py"
$reextractor = Join-Path $SkillRoot "scripts\reextract_validated_source_bundle.py"
$candidateRoot = Join-Path $SkillRoot "examples\candidates"
$originProcessNames = @("Origin64", "Origin_64", "Origin_32", "Origin")

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdministrator)) {
    throw "E120_ENVIRONMENT_MISMATCH: run this batch from an elevated PowerShell process."
}

if ($LaunchOriginExe) {
    if ($SourceDataPolicy -ne "fresh_extract") {
        throw "E132_ORIGIN_LAUNCH_CONFLICT: batch-started Origin is limited to fresh_extract runs."
    }
    if (-not (Test-Path -LiteralPath $LaunchOriginExe -PathType Leaf)) {
        throw "E120_ENVIRONMENT_MISMATCH: LaunchOriginExe was not found."
    }
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

$sourceBundleDir = Join-Path $OutputRoot "source_bundle"
$sourceManifest = Join-Path $sourceBundleDir "source_bundle.json"
$reuseRecordPath = $null
if ($SourceDataPolicy -eq "fresh_extract") {
    if (-not $SourcePdf -or -not (Test-Path -LiteralPath $SourcePdf -PathType Leaf)) {
        throw "E127_FRESH_SOURCE_REQUIRED: fresh_extract requires SourcePdf."
    }
    & $PythonExe $extractor --source-pdf $SourcePdf --output-dir $sourceBundleDir --json-out $sourceManifest
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $sourceManifest -PathType Leaf)) {
        throw "E127_FRESH_SOURCE_REQUIRED: same-run PDF source extraction failed."
    }
} else {
    if (-not $ReuseBatchRoot -or -not (Test-Path -LiteralPath $ReuseBatchRoot -PathType Container)) {
        throw "E128_SOURCE_DATA_REUSE_REJECTED: validated_reuse requires ReuseBatchRoot."
    }
    $reuseRecordPath = Join-Path $OutputRoot "validated_data_reuse.json"
    & $PythonExe $reuseBuilder --batch-root $ReuseBatchRoot --json-out $reuseRecordPath
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $reuseRecordPath -PathType Leaf)) {
        throw "E128_SOURCE_DATA_REUSE_REJECTED: prior batch quality validation failed."
    }
    $reuseRecord = Get-Content -Raw -Encoding UTF8 -LiteralPath $reuseRecordPath | ConvertFrom-Json
    if ($SourceDataPolicy -eq "validated_crop_reextract") {
        & $PythonExe $reextractor --reuse-record $reuseRecordPath --output-dir $sourceBundleDir --json-out $sourceManifest
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $sourceManifest -PathType Leaf)) {
            throw "E128_SOURCE_DATA_REUSE_REJECTED: validated source crop re-extraction failed."
        }
    } else {
        $priorManifest = [string]$reuseRecord.source_bundle_manifest
        if (-not (Test-Path -LiteralPath $priorManifest -PathType Leaf)) {
            throw "E128_SOURCE_DATA_REUSE_REJECTED: prior source bundle manifest was not found."
        }
        $priorBundle = Get-Content -Raw -Encoding UTF8 -LiteralPath $priorManifest | ConvertFrom-Json
        $priorBundleDir = Split-Path -Parent $priorManifest
        New-Item -ItemType Directory -Path $sourceBundleDir | Out-Null
        Copy-Item -LiteralPath $priorManifest -Destination $sourceManifest
        foreach ($figure in $figures) {
            $cropName = [string]$priorBundle.figures.$figure.source_crop
            $priorCrop = Join-Path $priorBundleDir $cropName
            if (-not (Test-Path -LiteralPath $priorCrop -PathType Leaf)) {
                throw "E128_SOURCE_DATA_REUSE_REJECTED: prior source crop was not found for $figure."
            }
            Copy-Item -LiteralPath $priorCrop -Destination (Join-Path $sourceBundleDir $cropName)
        }
    }
}
$sourceBundle = Get-Content -Raw -Encoding UTF8 -LiteralPath $sourceManifest | ConvertFrom-Json
$runCandidateRoot = Join-Path $OutputRoot "candidates"
New-Item -ItemType Directory -Path $runCandidateRoot | Out-Null
foreach ($figure in $figures) {
    $baseCandidatePath = Join-Path $candidateRoot "$figure.json"
    $baseCandidate = Get-Content -Encoding UTF8 -LiteralPath $baseCandidatePath | ConvertFrom-Json
    $templateSearchRaw = [string]$baseCandidate.template_search_record
    if ($templateSearchRaw) {
        $templateSearchPath = [IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $baseCandidatePath) $templateSearchRaw))
        if (-not (Test-Path -LiteralPath $templateSearchPath -PathType Leaf)) {
            throw "E130_TEMPLATE_SEARCH_REQUIRED: template search record was not found: $templateSearchPath"
        }
        $baseCandidate.template_search_record = $templateSearchPath
    }
    $sourceRecord = $sourceBundle.figures.$figure
    $baseCandidate.source_crop = Join-Path $sourceBundleDir $sourceRecord.source_crop
    $baseCandidate | Add-Member -NotePropertyName source_data_manifest -NotePropertyValue $sourceManifest -Force
    $baseCandidate | Add-Member -NotePropertyName source_data_policy -NotePropertyValue $SourceDataPolicy -Force
    $baseCandidate | Add-Member -NotePropertyName fresh_source_required -NotePropertyValue ($SourceDataPolicy -eq "fresh_extract") -Force
    if ($SourceDataPolicy -in @("validated_reuse", "validated_crop_reextract")) {
        $baseCandidate | Add-Member -NotePropertyName source_reuse_record -NotePropertyValue $reuseRecordPath -Force
    }
    $baseCandidate | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $runCandidateRoot "$figure.json") -Encoding UTF8
}

if ($LaunchOriginExe) {
    $originBeforeLaunch = @(Get-Process -Name $originProcessNames -ErrorAction SilentlyContinue)
    if ($originBeforeLaunch.Count -ne 0) {
        throw "E132_ORIGIN_LAUNCH_CONFLICT: close all visible and hidden Origin processes before a batch-started run."
    }
    $startedOrigin = Start-Process -FilePath $LaunchOriginExe `
        -WorkingDirectory (Split-Path -Parent $LaunchOriginExe) `
        -PassThru
    $origin = @()
    $originLaunchDeadline = (Get-Date).AddSeconds(8)
    do {
        $origin = @(Get-Process -Name $originProcessNames -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 })
        if ($origin.Count -eq 1) { break }
        Start-Sleep -Milliseconds 100
    } while ((Get-Date) -lt $originLaunchDeadline)
} else {
    $origin = @(Get-Process -Name $originProcessNames -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 })
}
if ($origin.Count -ne 1) {
    throw "E121_ATTACH_POLICY_VIOLATION: exactly one visible supported Origin process is required."
}
$originPid = $origin[0].Id
$runs = @()
foreach ($figure in $figures) {
    $candidate = Join-Path $runCandidateRoot "$figure.json"
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
    $current = @(Get-Process -Name $originProcessNames -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 })
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

$failedRuns = @($runs | Where-Object { $_.exit_code -ne 0 -or -not $_.pid_stable })
$batch = [ordered]@{
    schema = "originplot.five_figure_live_batch.v2"
    fresh_output_root_verified = $true
    admin_preflight = $adminPreflight
    source_data_policy = $SourceDataPolicy
    source_pdf = if ($SourcePdf) { (Resolve-Path -LiteralPath $SourcePdf).Path } else { $null }
    source_bundle_manifest = $sourceManifest
    source_bundle_data_sha256 = $sourceBundle.bundle_data_sha256
    same_run_fresh_source_verified = ($SourceDataPolicy -eq "fresh_extract")
    validated_source_data_reuse_verified = ($SourceDataPolicy -in @("validated_reuse", "validated_crop_reextract"))
    validated_crop_reextract_verified = ($SourceDataPolicy -eq "validated_crop_reextract")
    validated_reuse_record = $reuseRecordPath
    python_executable = $PythonExe
    python_version = $pythonVersion
    origin_launch_mode = if ($LaunchOriginExe) { "batch_started" } else { "preexisting_visible" }
    started_visible_origin_pid = $originPid
    completed_at = (Get-Date).ToString("o")
    status = if ($runs.Count -eq 5 -and $failedRuns.Count -eq 0) { "completed" } else { "failed" }
    runs = $runs
}
$batch | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $OutputRoot "live_validation_status.json") -Encoding UTF8

& $PythonExe $audit --root $OutputRoot --json-out (Join-Path $OutputRoot "five_figure_batch_audit.json")
exit $LASTEXITCODE
