param(
    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,
    [ValidateSet("fresh_extract", "validated_reuse", "validated_crop_reextract")]
    [string]$SourceDataPolicy = "fresh_extract",
    [string]$SourcePdf = $null,
    [string]$ReuseBatchRoot = $null,
    [string]$SkillRoot = $null,
    [string]$PythonExe = $null,
    [string]$LaunchOriginExe = $null,
    [ValidateRange(1, 60)]
    [int]$FigureDisplaySeconds = 3,
    [hashtable]$ExportSupersampleByFigure = @{},
    [ValidateSet("legacy", "full")]
    [string]$Fig3CanvasMode = "legacy"
)

$ErrorActionPreference = "Stop"
function Resolve-FigureExportFactors {
    param([hashtable]$Requested)

    $validated = @{}
    foreach ($entry in $Requested.GetEnumerator()) {
        $figure = $entry.Key
        $factor = $entry.Value
        if ($figure -cnotin @("fig3", "fig12", "fig14", "fig15", "fig16") -or
            ($factor -isnot [int] -and $factor -isnot [long]) -or
            $factor -lt 1 -or $factor -gt 4) {
            throw "E134_EXPORT_SUPERSAMPLE_INVALID: use named benchmark figures and integer factors from 1 to 4."
        }
        $validated[$figure] = [int]$factor
    }
    return $validated
}

$ExportSupersampleByFigure = Resolve-FigureExportFactors -Requested $ExportSupersampleByFigure
if ($Fig3CanvasMode -eq "full" -and $SourceDataPolicy -ne "fresh_extract") {
    throw "E127_FRESH_SOURCE_REQUIRED: requesting a full Fig3 canvas requires fresh_extract from the source PDF."
}
if (-not $SkillRoot) { $SkillRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath) }
$OutputRoot = [IO.Path]::GetFullPath($OutputRoot)
$pythonResolver = Join-Path $SkillRoot "scripts\resolve_python310.ps1"
$PythonExe = (& $pythonResolver -PythonExe $PythonExe).Trim()
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
$candidateRoot = Join-Path $SkillRoot "benchmarks\aa2195\examples\candidates"
$originProcessNames = @("Origin64", "Origin_64", "Origin_32", "Origin")
$originLaunchExe = $null

function Resolve-OriginGuiExecutable {
    param([Parameter(Mandatory = $true)][string]$RequestedPath)

    $resolvedRequest = [IO.Path]::GetFullPath($RequestedPath)
    if (Test-Path -LiteralPath $resolvedRequest -PathType Container) {
        $guiCandidate = Join-Path $resolvedRequest "Origin64.exe"
        if (Test-Path -LiteralPath $guiCandidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $guiCandidate).Path
        }
        $guiCandidate = Join-Path $resolvedRequest "Origin.exe"
        if (Test-Path -LiteralPath $guiCandidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $guiCandidate).Path
        }
        throw "E120_ENVIRONMENT_MISMATCH: no Origin GUI executable was found under $resolvedRequest."
    }
    if (-not (Test-Path -LiteralPath $resolvedRequest -PathType Leaf)) {
        throw "E120_ENVIRONMENT_MISMATCH: LaunchOriginExe was not found."
    }
    if ([IO.Path]::GetFileName($resolvedRequest) -ieq "Origin.exe") {
        $guiCandidate = Join-Path (Split-Path -Parent $resolvedRequest) "Origin64.exe"
        if (Test-Path -LiteralPath $guiCandidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $guiCandidate).Path
        }
    }
    return (Resolve-Path -LiteralPath $resolvedRequest).Path
}

function Clear-OriginEmbeddingProcesses {
    $targets = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $candidate = $_
        $nativeProcess = Get-Process -Id $candidate.ProcessId -ErrorAction SilentlyContinue
        $candidate.Name -like "Origin*.exe" -and [string]$candidate.CommandLine -match "(?i)-Embedding" -and
            $nativeProcess -and $nativeProcess.MainWindowHandle -eq 0
    })
    $detected = @($targets | ForEach-Object { [int]$_.ProcessId })
    $stopped = @()
    $failures = @()
    $skipped = @()
    foreach ($target in $targets) {
        try {
            $currentTarget = Get-CimInstance Win32_Process -Filter ("ProcessId = {0}" -f $target.ProcessId) -ErrorAction Stop
            $currentProcess = Get-Process -Id $target.ProcessId -ErrorAction SilentlyContinue
            if (-not $currentTarget -or -not $currentProcess -or
                $currentTarget.Name -notlike "Origin*.exe" -or
                [string]$currentTarget.CommandLine -notmatch "(?i)-Embedding" -or
                $currentTarget.CreationDate -ne $target.CreationDate -or
                $currentProcess.MainWindowHandle -ne 0) {
                $skipped += [ordered]@{ pid = [int]$target.ProcessId; reason = "identity_or_window_changed" }
                continue
            }
            Stop-Process -Id ([int]$target.ProcessId) -Force -ErrorAction Stop
            $stopped += [int]$target.ProcessId
        } catch {
            $failures += [ordered]@{ pid = [int]$target.ProcessId; error = $_.Exception.Message }
        }
    }
    [pscustomobject]@{
        detected_pids = @($detected | Sort-Object -Unique)
        stopped_pids = @($stopped | Sort-Object -Unique)
        failures = @($failures)
        skipped = @($skipped)
    }
}

function Get-OriginProcessRecords {
    @(@(Get-Process -Name $originProcessNames -ErrorAction SilentlyContinue) | ForEach-Object {
        $process = Get-CimInstance Win32_Process -Filter ("ProcessId = {0}" -f $_.Id) -ErrorAction SilentlyContinue
        $commandLine = if ($process) { [string]$process.CommandLine } else { "" }
        [ordered]@{
            pid = $_.Id
            name = $_.ProcessName
            main_window_handle = $_.MainWindowHandle.ToInt64()
            executable_path = if ($process) { $process.ExecutablePath } else { $null }
            command_line = $commandLine
            is_embedding = $commandLine -match "(?i)-Embedding"
        }
    })
}

function Initialize-OriginWindowApi {
    if (-not ("OriginPlot.NativeWindow" -as [type])) {
        Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
namespace OriginPlot {
    public static class NativeWindow {
        [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr handle, int command);
        [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr handle);
        [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr handle);
        [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr handle);
        [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    }
}
"@
    }
}

function Get-OriginWindowState {
    param([Parameter(Mandatory = $true)][int]$ProcessId)
    Initialize-OriginWindowApi
    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    $handle = if ($process) { $process.MainWindowHandle } else { [IntPtr]::Zero }
    $visible = $handle -ne [IntPtr]::Zero -and [OriginPlot.NativeWindow]::IsWindowVisible($handle)
    $iconic = $handle -ne [IntPtr]::Zero -and [OriginPlot.NativeWindow]::IsIconic($handle)
    [pscustomobject]@{
        pid = $ProcessId
        main_window_handle = $handle.ToInt64()
        is_visible = [bool]$visible
        is_iconic = [bool]$iconic
        restored = [bool]($visible -and -not $iconic)
        foregrounded = [bool]($handle -ne [IntPtr]::Zero -and [OriginPlot.NativeWindow]::GetForegroundWindow() -eq $handle)
        observed_at = (Get-Date).ToString("o")
    }
}

function Show-OriginWindow {
    param([Parameter(Mandatory = $true)][int]$ProcessId)
    Initialize-OriginWindowApi
    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($process -and $process.MainWindowHandle -ne 0) {
        $null = [OriginPlot.NativeWindow]::ShowWindowAsync($process.MainWindowHandle, 9)
        $null = [OriginPlot.NativeWindow]::SetForegroundWindow($process.MainWindowHandle)
        # Native return values describe API calls, not the resulting state.
        Start-Sleep -Milliseconds 150
    }
    Get-OriginWindowState -ProcessId $ProcessId
}

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdministrator)) {
    throw "E120_ENVIRONMENT_MISMATCH: run this batch from an elevated PowerShell process."
}

if ($LaunchOriginExe) {
    $originLaunchExe = Resolve-OriginGuiExecutable -RequestedPath $LaunchOriginExe
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

$originEmbeddingCleanup = Clear-OriginEmbeddingProcesses
$sourceBundleDir = Join-Path $OutputRoot "source_bundle"
$sourceManifest = Join-Path $sourceBundleDir "source_bundle.json"
$reuseRecordPath = $null
if ($SourceDataPolicy -eq "fresh_extract") {
    if (-not $SourcePdf -or -not (Test-Path -LiteralPath $SourcePdf -PathType Leaf)) {
        throw "E127_FRESH_SOURCE_REQUIRED: fresh_extract requires SourcePdf."
    }
    & $PythonExe $extractor --source-pdf $SourcePdf --output-dir $sourceBundleDir --json-out $sourceManifest --fig3-canvas-mode $Fig3CanvasMode
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
    if ($ExportSupersampleByFigure.ContainsKey($figure)) {
        $baseCandidate | Add-Member -NotePropertyName export_supersample -NotePropertyValue $ExportSupersampleByFigure[$figure] -Force
    }
    $templateSearchRaw = [string]$baseCandidate.template_search_record
    if ($templateSearchRaw) {
        $templateSearchPath = [IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $baseCandidatePath) $templateSearchRaw))
        if (-not (Test-Path -LiteralPath $templateSearchPath -PathType Leaf)) {
            throw "E130_TEMPLATE_SEARCH_REQUIRED: template search record was not found: $templateSearchPath"
        }
        $baseCandidate.template_search_record = $templateSearchPath
    }
    $sourceRecord = $sourceBundle.figures.$figure
    if ($figure -eq "fig3" -and $sourceRecord.extraction.fig3_canvas_mode) {
        $baseCandidate | Add-Member -NotePropertyName fig3_canvas_mode -NotePropertyValue $sourceRecord.extraction.fig3_canvas_mode -Force
    }
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
    $launchEmbeddingCleanup = Clear-OriginEmbeddingProcesses
    $originEmbeddingCleanup.detected_pids = @($originEmbeddingCleanup.detected_pids + $launchEmbeddingCleanup.detected_pids | Sort-Object -Unique)
    $originEmbeddingCleanup.stopped_pids = @($originEmbeddingCleanup.stopped_pids + $launchEmbeddingCleanup.stopped_pids | Sort-Object -Unique)
    $originEmbeddingCleanup.failures = @($originEmbeddingCleanup.failures + $launchEmbeddingCleanup.failures)
    $originBeforeLaunchRecords = @(Get-OriginProcessRecords)
    if ($originBeforeLaunchRecords.Count -ne 0) {
        $originConflictDetails = $originBeforeLaunchRecords | ConvertTo-Json -Compress -Depth 4
        throw "E132_ORIGIN_LAUNCH_CONFLICT: Origin processes remain after default -Embedding cleanup; release them before a batch-started run: $originConflictDetails"
    }
    $startedOrigin = Start-Process -FilePath $originLaunchExe `
        -WorkingDirectory (Split-Path -Parent $originLaunchExe) `
        -WindowStyle Normal `
        -PassThru
    $origin = @()
    $originLaunchDeadline = (Get-Date).AddSeconds(8)
    do {
        $originRecords = @(Get-OriginProcessRecords)
        $origin = @($originRecords | Where-Object { $_.main_window_handle -ne 0 -and -not $_.is_embedding })
        if ($origin.Count -eq 1) { break }
        Start-Sleep -Milliseconds 100
    } while ((Get-Date) -lt $originLaunchDeadline)
} else {
    $originRecords = @(Get-OriginProcessRecords)
    $origin = @($originRecords | Where-Object { $_.main_window_handle -ne 0 -and -not $_.is_embedding })
}
if (-not $originRecords) { $originRecords = @(Get-OriginProcessRecords) }
$hiddenOriginRecords = @($originRecords | Where-Object { $_.main_window_handle -eq 0 })
if ($originRecords.Count -ne 1 -or $origin.Count -ne 1 -or $hiddenOriginRecords.Count -ne 0) {
    throw "E121_ATTACH_POLICY_VIOLATION: exactly one visible supported Origin process is required."
}
$originPid = $origin[0].pid
$originWindowPresentation = Show-OriginWindow -ProcessId $originPid
$runs = @()
$figureIndex = 0
foreach ($figure in $figures) {
    $candidate = Join-Path $runCandidateRoot "$figure.json"
    $outputDir = Join-Path $OutputRoot $figure
    $stdout = Join-Path $OutputRoot "$figure.stdout.txt"
    $stderr = Join-Path $OutputRoot "$figure.stderr.txt"
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    $figureIndex++
    Write-Host ("[{0}/5] {1}: drawing in visible Origin PID {2}" -f $figureIndex, $figure, $originPid)
    $originWindowPresentation = Show-OriginWindow -ProcessId $originPid
    if (-not $originWindowPresentation.restored) {
        throw "E133_ORIGIN_WINDOW_NOT_VISIBLE: cannot display Origin before $figure."
    }
    $figureClock = [Diagnostics.Stopwatch]::StartNew()
    $windowSamples = @($originWindowPresentation)
    $windowRestorationCount = 0
    $workerArguments = @($worker, "--figure", $figure, "--candidate", $candidate, "--output-dir", $outputDir, "--live", "--require-live-success")
    # Start-Process joins ArgumentList with spaces; quote path-bearing tokens.
    $quotedWorkerArguments = @($workerArguments | ForEach-Object { '"' + $_ + '"' })
    $process = Start-Process -FilePath $PythonExe `
        -ArgumentList $quotedWorkerArguments `
        -WorkingDirectory $SkillRoot `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -WindowStyle Hidden `
        -PassThru
    # Sampling ends with this worker. There is no global or background monitor.
    while (-not $process.HasExited) {
        $sampleBeforeRestore = Get-OriginWindowState -ProcessId $originPid
        $windowSamples += $sampleBeforeRestore
        if (-not $sampleBeforeRestore.restored) {
            $windowRestorationCount++
            $windowSample = Show-OriginWindow -ProcessId $originPid
            $windowSamples += $windowSample
        }
        Start-Sleep -Milliseconds 500
        $process.Refresh()
    }
    $process.WaitForExit()
    $figureClock.Stop()
    $postWorkerWindow = Get-OriginWindowState -ProcessId $originPid
    $windowSamples += $postWorkerWindow
    if (-not $postWorkerWindow.restored) {
        $windowRestorationCount++
        $postWorkerWindow = Show-OriginWindow -ProcessId $originPid
        $windowSamples += $postWorkerWindow
    }
    $samplePath = Join-Path $outputDir "origin_window_samples.json"
    ConvertTo-Json -InputObject @($windowSamples) -Depth 4 | Set-Content -LiteralPath $samplePath -Encoding UTF8
    $failedSamples = @($windowSamples | Where-Object { -not $_.is_visible -or $_.is_iconic -or $_.main_window_handle -eq 0 })
    $visibilityVerified = $failedSamples.Count -eq 0
    $null = Show-OriginWindow -ProcessId $originPid
    Write-Host ("[{0}/5] {1}: exit={2}, elapsed={3:N1}s, visible samples={4}/{5}; display {6}s" -f $figureIndex, $figure, $process.ExitCode, $figureClock.Elapsed.TotalSeconds, ($windowSamples.Count - $failedSamples.Count), $windowSamples.Count, $FigureDisplaySeconds)
    Start-Sleep -Seconds $FigureDisplaySeconds
    $postDisplayWindow = Get-OriginWindowState -ProcessId $originPid
    # Capture anomalies before cleanup; stopping residue must not turn failure into success.
    $preCleanupRecords = @(Get-OriginProcessRecords)
    $preCleanupStable = $preCleanupRecords.Count -eq 1 -and $preCleanupRecords[0].pid -eq $originPid -and
        -not $preCleanupRecords[0].is_embedding -and $preCleanupRecords[0].main_window_handle -ne 0
    $runEmbeddingCleanup = Clear-OriginEmbeddingProcesses
    $originEmbeddingCleanup.detected_pids = @($originEmbeddingCleanup.detected_pids + $runEmbeddingCleanup.detected_pids | Sort-Object -Unique)
    $originEmbeddingCleanup.stopped_pids = @($originEmbeddingCleanup.stopped_pids + $runEmbeddingCleanup.stopped_pids | Sort-Object -Unique)
    $originEmbeddingCleanup.failures = @($originEmbeddingCleanup.failures + $runEmbeddingCleanup.failures)
    $currentRecords = @(Get-OriginProcessRecords)
    $current = @($currentRecords | Where-Object { $_.main_window_handle -ne 0 -and -not $_.is_embedding })
    $hiddenCurrentRecords = @($currentRecords | Where-Object { $_.main_window_handle -eq 0 })
    $pidStable = $preCleanupStable -and $currentRecords.Count -eq 1 -and $current.Count -eq 1 -and $current[0].pid -eq $originPid -and $hiddenCurrentRecords.Count -eq 0
    $evidenceManifestPath = Join-Path $outputDir "evidence\run_manifest.json"
    $evidenceRunId = $null
    if (Test-Path -LiteralPath $evidenceManifestPath -PathType Leaf) {
        $evidenceManifest = Get-Content -Raw -Encoding UTF8 -LiteralPath $evidenceManifestPath | ConvertFrom-Json
        $evidenceRunId = [string]$evidenceManifest.run_id
    }
    $runs += [ordered]@{
        figure = $figure
        run_id = $evidenceRunId
        exit_code = $process.ExitCode
        output_dir = $outputDir
        stdout = $stdout
        stderr = $stderr
        visible_origin_pid = if ($current.Count -eq 1) { $current[0].pid } else { $null }
        origin_window_presentation = $originWindowPresentation
        origin_window_after_worker = $postWorkerWindow
        origin_window_after_display = $postDisplayWindow
        origin_window_samples = $samplePath
        visibility_sample_count = $windowSamples.Count
        visibility_failed_sample_count = $failedSamples.Count
        visibility_verified = $visibilityVerified
        visibility_restore_count = $windowRestorationCount
        elapsed_seconds = [Math]::Round($figureClock.Elapsed.TotalSeconds, 3)
        figure_display_seconds = $FigureDisplaySeconds
        origin_processes_before_cleanup = $preCleanupRecords
        origin_processes_after_cleanup = $currentRecords
        origin_cleanup = $runEmbeddingCleanup
        pid_stable = $pidStable
    }
    if (-not $pidStable) {
        break
    }
}

$failedRuns = @($runs | Where-Object { $_.exit_code -ne 0 -or -not $_.pid_stable -or -not $_.visibility_verified -or -not $_.origin_window_after_display.restored })
$batch = [ordered]@{
    schema = "originplot.five_figure_live_batch.v2"
    visible_window_evidence_required = $true
    figure_display_seconds = $FigureDisplaySeconds
    fresh_output_root_verified = $true
    admin_preflight = $adminPreflight
    origin_embedding_cleanup = $originEmbeddingCleanup
    source_data_policy = $SourceDataPolicy
    export_supersample_by_figure = $ExportSupersampleByFigure
    fig3_canvas_mode = if ($sourceBundle.figures.fig3.extraction.fig3_canvas_mode) { $sourceBundle.figures.fig3.extraction.fig3_canvas_mode } else { "legacy" }
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
    origin_requested_exe = $LaunchOriginExe
    origin_launch_exe = $originLaunchExe
    origin_embedding_cleanup_stopped_pids = @($originEmbeddingCleanup.stopped_pids)
    origin_window_presentation = $originWindowPresentation
    started_visible_origin_pid = $originPid
    completed_at = (Get-Date).ToString("o")
    status = if ($runs.Count -eq 5 -and $failedRuns.Count -eq 0) { "completed" } else { "failed" }
    runs = $runs
}
$batch | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $OutputRoot "live_validation_status.json") -Encoding UTF8

& $PythonExe $audit --root $OutputRoot --require-visible-window-evidence --json-out (Join-Path $OutputRoot "five_figure_batch_audit.json")
exit $LASTEXITCODE
