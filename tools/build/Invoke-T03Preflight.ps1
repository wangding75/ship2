param([string]$EvidenceDirectory = 'releases/t03-preflight')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$out = [IO.Path]::GetFullPath((Join-Path $root $EvidenceDirectory))
if (-not $out.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Evidence must stay inside this checkout' }
[IO.Directory]::CreateDirectory($out) | Out-Null
$utf8 = New-Object Text.UTF8Encoding($false)
$records = @()
function Capture([string]$name, [string]$exe, [string]$arguments) {
    $start = [DateTime]::UtcNow.ToString('o')
    $info = New-Object Diagnostics.ProcessStartInfo
    $info.FileName = $exe
    $info.Arguments = $arguments
    $info.WorkingDirectory = $root
    $info.UseShellExecute = $false
    $info.CreateNoWindow = $true
    $info.RedirectStandardOutput = $true
    $info.RedirectStandardError = $true
    $info.StandardOutputEncoding = $utf8
    $info.StandardErrorEncoding = $utf8
    $p = New-Object Diagnostics.Process
    $p.StartInfo = $info
    if (-not $p.Start()) { throw "Cannot start $exe" }
    $stdout = $p.StandardOutput.ReadToEndAsync()
    $stderr = $p.StandardError.ReadToEndAsync()
    if (-not $p.WaitForExit(45000)) {
        # Only this exact read-only Unity/Git CLI child is owned by this probe.
        $p.Kill()
        $p.WaitForExit()
        throw "Probe timed out; stopped exact CLI child PID $($p.Id)"
    }
    [IO.File]::WriteAllText((Join-Path $out "$name.stdout.txt"), $stdout.Result, $utf8)
    [IO.File]::WriteAllText((Join-Path $out "$name.stderr.txt"), $stderr.Result, $utf8)
    $record = [ordered]@{name=$name; executable=$exe; arguments=$arguments; started_utc=$start; ended_utc=[DateTime]::UtcNow.ToString('o'); exit_code=$p.ExitCode; stdout="$name.stdout.txt"; stderr="$name.stderr.txt"}
    $p.Dispose()
    return $record
}
$unity = (Get-Command unity -ErrorAction Stop).Source
$git = (Get-Command git -ErrorAction Stop).Source
$records += Capture 'unity-version' $unity '--version'
$records += Capture 'unity-update' $unity 'self-update --check --format json'
$records += Capture 'unity-license' $unity 'license status --format json'
$records += Capture 'unity-running' $unity 'editors running --format json'
$records += Capture 'git-version' $git '--version'
$records += Capture 'remote-main' $git '-c http.sslBackend=openssl ls-remote https://github.com/wangding75/ship2.git'
$inventory = [ordered]@{utc=[DateTime]::UtcNow.ToString('o'); editor_path='C:/Program Files/Unity/Hub/Editor/6000.6.6f1/Editor/Unity.exe'; lease_acquired=$false; editor_started=$false; gpu_measurement_started=$false}
$binary = Get-Item $inventory.editor_path
$inventory.editor_version = $binary.VersionInfo.ProductVersion
$inventory.editor_sha256 = (Get-FileHash $binary.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
try {
    $inventory.processes = @(Get-CimInstance Win32_Process -Filter "Name = 'Unity.exe'" -ErrorAction Stop | Select-Object ProcessId,CommandLine)
    $inventory.process_inventory_status = 'OBSERVED'
} catch {
    $inventory.process_inventory_status = 'BLOCKED'
    $inventory.process_inventory_error = $_.Exception.Message
}
[IO.File]::WriteAllText((Join-Path $out 'commands.json'), (ConvertTo-Json -InputObject @($records) -Depth 8), $utf8)
[IO.File]::WriteAllText((Join-Path $out 'inventory.json'), ($inventory | ConvertTo-Json -Depth 8), $utf8)
$license = Get-Content (Join-Path $out 'unity-license.stdout.txt') -Raw -Encoding UTF8 | ConvertFrom-Json
$remoteRecord = $records | Where-Object name -eq 'remote-main'
$blocked = (-not $license.success) -or ($inventory.process_inventory_status -eq 'BLOCKED') -or ($remoteRecord.exit_code -ne 0)
$outcome = if ($blocked) { 'BLOCKED' } else { 'BASELINE_COLLECTED' }
$reason = if ($blocked) { 'Licensing, process visibility or remote query preflight did not complete successfully; see raw records' } else { 'Read-only baseline collected; exclusive resource lease still required before Editor use' }
$report = [ordered]@{status=$outcome; reason=$reason; licensing_observation=$license; remote_query_exit_code=$remoteRecord.exit_code; interpretation='License probe failure does not prove the host lacks an activated license. Empty running list does not prove no host Editor exists under sandbox restrictions.'; not_run=@('Unity project creation','Package resolution and version locks','Windows build/start/screenshot','Clean checkout build','Compile-error red/rollback green','Gate negative probes','Lease contention/release/expiry and permission isolation','Independent A04/A13 acceptance'); next_owner='A00 coordinates runtime owner; A14 resumes implementation after access is restored'; acceptance_pass_claimed=$false}
[IO.File]::WriteAllText((Join-Path $out 'preflight-result.json'), ($report | ConvertTo-Json -Depth 8), $utf8)
Write-Output "Evidence collected: $EvidenceDirectory; outcome $outcome (not an acceptance verdict)"
if ($blocked) { exit 2 }
exit 0
