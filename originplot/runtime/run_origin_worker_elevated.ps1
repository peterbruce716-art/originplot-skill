param(
    [Parameter(Mandatory = $true)][string]$PythonExe,
    [Parameter(Mandatory = $true)][string]$WorkerModule,
    [Parameter(Mandatory = $true)][string]$TaskPath,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory
)

$quotedTask = '"' + $TaskPath.Replace('"', '\"') + '"'
$process = Start-Process -FilePath $PythonExe `
    -ArgumentList @('-m', $WorkerModule, '--task', $quotedTask) `
    -WorkingDirectory $WorkingDirectory `
    -Verb RunAs `
    -Wait `
    -PassThru
exit $process.ExitCode
