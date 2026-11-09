$ErrorActionPreference = 'Stop'
$root = (Resolve-Path "$PSScriptRoot/../..").Path
$out = Join-Path $root 'releases/t03-network'
New-Item -ItemType Directory -Force $out | Out-Null
$results = @()
foreach ($route in @('proxy','direct','china-direct')) {
    $registry = if ($route -eq 'china-direct') { 'https://packages.unity.cn' } else { 'https://packages.unity.com' }
    foreach ($target in @(@{name='github';url='https://github.com/wangding75/ship2.git/info/refs?service=git-upload-pack'}, @{name='pipeline';url="$registry/com.unity.pipeline"})) {
        $body = Join-Path $out "$route-$($target.name).body"
        $err = Join-Path $out "$route-$($target.name).stderr"
        $args = @('--silent','--show-error','--location','--max-time','12','--output',$body,'--write-out','%{http_code}|%{remote_ip}|%{remote_port}|%{http_connect}')
        if ($route -eq 'proxy') { $args += @('--proxy','http://127.0.0.1:33210') } else { $args += @('--noproxy','*') }
        $started = [DateTime]::UtcNow.ToString('o')
        $stats = & curl.exe @args $target.url 2> $err
        $code = $LASTEXITCODE
        $results += [ordered]@{route=$route;target=$target.name;url=$target.url;startedUtc=$started;endedUtc=[DateTime]::UtcNow.ToString('o');exit=$code;stats="$stats";bytes=if(Test-Path $body){(Get-Item $body).Length}else{0}}
        $results | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $out 'route-results.json') -Encoding UTF8
    }
}
$results | ConvertTo-Json -Depth 6
