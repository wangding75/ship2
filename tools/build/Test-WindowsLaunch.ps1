param([int]$Width=1920,[int]$Height=1080)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path "$PSScriptRoot/../..").Path
$evidence = Join-Path $root "releases/t03-recovery/launch-$Width-$Height"
New-Item -ItemType Directory -Force $evidence | Out-Null
$process = $null
try {
    $process = Start-Process (Join-Path $root 'releases/windows/S1T03.exe') -WindowStyle Hidden -PassThru -ArgumentList @('-batchmode','-screen-width',"$Width",'-screen-height',"$Height",'-screen-fullscreen','0','-t03-smoke',('"'+$evidence+'"'),'-logFile',('"'+(Join-Path $evidence 'Player.log')+'"'))
    if (!$process.WaitForExit(120000)) { Stop-Process -Id $process.Id; $process.WaitForExit(); throw 'Player launch timeout' }
    $process.Refresh()
    [ordered]@{utc=[DateTime]::UtcNow.ToString('o');pid=$process.Id;exitCode=$process.ExitCode;width=$Width;height=$Height} | ConvertTo-Json | Set-Content (Join-Path $evidence 'process.json') -Encoding UTF8
    if ($process.ExitCode -ne 0) { throw 'Player failed' }
    $record = Get-Content (Join-Path $evidence 'launch.json') -Raw | ConvertFrom-Json
    if (!$record.success -or $record.frames -lt 90 -or $record.width -ne $Width -or $record.height -ne $Height) { throw 'Invalid launch evidence' }
    $record
} finally {
    if ($process -and !$process.HasExited) { Stop-Process -Id $process.Id; $process.WaitForExit() }
}
