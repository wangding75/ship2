param(
    [Parameter(Mandatory=$true)][string[]]$Command,
    [Parameter(Mandatory=$true)][string]$Evidence,
    [switch]$AllowFailure
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path "$PSScriptRoot/../..").Path
$project = Join-Path $root 'client/UnityProject'
$started = [DateTime]::UtcNow.ToString('o')
$raw = & 'C:/Users/wangding/AppData/Local/Unity/bin/unity.exe' command @Command --project-path $project --caller plugin --skill unity-pipeline --format json
$code = $LASTEXITCODE
$raw | Set-Content -LiteralPath $Evidence -Encoding UTF8
[ordered]@{startedUtc=$started;endedUtc=[DateTime]::UtcNow.ToString('o');exitCode=$code;arguments=$Command;project=$project;agent='f22db727-a17b-473a-ba27-149945878372'} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath ($Evidence + '.invocation.json') -Encoding UTF8
$result = $raw | ConvertFrom-Json
if (!$AllowFailure -and ($code -ne 0 -or !$result.success -or $result.data.result.success -eq $false)) { throw "Pipeline call failed; see $Evidence" }
$result
