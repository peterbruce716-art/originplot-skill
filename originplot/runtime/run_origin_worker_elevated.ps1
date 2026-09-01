param(
    [Parameter(Mandatory = $true)][string]$PythonExe,
    [Parameter(Mandatory = $true)][string]$WorkerScript,
    [Parameter(Mandatory = $true)][string]$TaskPath,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory
)

$quotedWorker = '"' + $WorkerScript.Replace('"', '\"') + '"'
$quotedTask = '"' + $TaskPath.Replace('"', '\"') + '"'
$process = Start-Process -FilePath $PythonExe `
    -ArgumentList @($quotedWorker, '--task', $quotedTask) `
    -WorkingDirectory $WorkingDirectory `
    -Verb RunAs `
    -Wait `
    -PassThru
exit $process.ExitCode
