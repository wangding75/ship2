param([int]$TimeoutMinutes = 120)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path "$PSScriptRoot/../..").Path
$project = Join-Path $repo 'client/UnityProject'
$evidence = Join-Path $repo 'releases/t03-recovery'
New-Item -ItemType Directory -Force -Path $evidence | Out-Null
$guardPath = Join-Path $evidence 'editor.guard'
$stopPath = Join-Path $evidence 'stop-editor'
$editor = $null
$guard = $null
try {
    $guard = [IO.File]::Open($guardPath, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    $existing = Get-CimInstance Win32_Process -Filter "Name='Unity.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($project) -and $_.CommandLine -notmatch 'assetImportWorker' }
    if ($existing) { throw 'Target project already has an Editor; refusing duplicate startup.' }
    $projectLock = Join-Path $project 'Temp/UnityLockfile'
    if (Test-Path $projectLock) {
        $lockProbe = [IO.File]::Open($projectLock, [IO.FileMode]::Open, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
        $lockProbe.Dispose()
    }
    Remove-Item -LiteralPath $stopPath -ErrorAction SilentlyContinue
    $exe = 'C:/Program Files/Unity/Hub/Editor/6000.6.6f1/Editor/Unity.exe'
    $log = Join-Path $evidence 'Editor.log'
    $editor = Start-Process -FilePath $exe -ArgumentList @('-batchmode', '-projectPath', ('"' + $project + '"'), '-logFile', ('"' + $log + '"')) -WindowStyle Hidden -PassThru
    [ordered]@{pid=$editor.Id;startUtc=$editor.StartTime.ToUniversalTime().ToString('o');exe=$exe;project=$project;log=$log;agent='f22db727-a17b-473a-ba27-149945878372';kind='owned-batchmode-editor';guard='exclusive FileShare.None bootstrap guard, not final resource broker'} | ConvertTo-Json | Set-Content (Join-Path $evidence 'owned-editor.json') -Encoding UTF8
    Write-Output "Owned Editor PID $($editor.Id) started; guard held."
    $deadline = [DateTime]::UtcNow.AddMinutes($TimeoutMinutes)
    while (!$editor.WaitForExit(1000)) {
        if ((Test-Path $stopPath) -or [DateTime]::UtcNow -gt $deadline) { break }
    }
} finally {
    if ($editor -and !$editor.HasExited) {
        $current = Get-Process -Id $editor.Id -ErrorAction SilentlyContinue
        if ($current -and $current.StartTime -eq $editor.StartTime -and $current.Path -eq $exe) {
            Stop-Process -Id $editor.Id
            $editor.WaitForExit()
        }
    }
    if ($editor) { Write-Output "Owned Editor exit $($editor.ExitCode)" }
    if ($guard) { $guard.Dispose() }
}
