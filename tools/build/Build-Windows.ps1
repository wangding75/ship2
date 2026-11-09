$ErrorActionPreference = 'Stop'
$root = (Resolve-Path "$PSScriptRoot/../..").Path
$project = Join-Path $root 'client/UnityProject'
$evidence = Join-Path $root 'releases/t03-recovery'
New-Item -ItemType Directory -Force $evidence | Out-Null
$guard = [IO.File]::Open((Join-Path $evidence 'editor.guard'), 'OpenOrCreate', 'ReadWrite', 'None')
$process = $null
try {
    $existing = Get-CimInstance Win32_Process -Filter "Name='Unity.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($project) }
    if ($existing) { throw 'Target Editor already running; refusing duplicate.' }
    $started = [DateTime]::UtcNow.ToString('o')
    $process = Start-Process 'C:/Program Files/Unity/Hub/Editor/6000.6.6f1/Editor/Unity.exe' -WindowStyle Hidden -PassThru -ArgumentList @('-batchmode','-quit','-projectPath',('"'+$project+'"'),'-executeMethod','T03Build.Windows','-logFile',('"'+(Join-Path $evidence 'windows-build.log')+'"'))
    if (!$process.WaitForExit(1200000)) { Stop-Process -Id $process.Id; $process.WaitForExit(); throw 'Build exceeded 20 minutes.' }
    $process.Refresh()
    [ordered]@{startedUtc=$started;endedUtc=[DateTime]::UtcNow.ToString('o');pid=$process.Id;exitCode=$process.ExitCode;project=$project} | ConvertTo-Json | Set-Content (Join-Path $evidence 'build-process.json') -Encoding UTF8
    if ($process.ExitCode -ne 0) { throw "Unity exited $($process.ExitCode)" }
} finally {
    if ($process -and !$process.HasExited) { Stop-Process -Id $process.Id; $process.WaitForExit() }
    $guard.Dispose()
}
