param(
    [int]$Port = 8765,
    [string]$Domain = "",
    [string]$PythonExecutable = "python",
    [string]$OperatorExecutable = ""
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $repo "data"
$logDir = Join-Path $repo "logs"
$runtimeFile = Join-Path $runtimeDir "web-runtime.json"
$webProcess = $null
$ngrokProcess = $null

if ([string]::IsNullOrWhiteSpace($env:NLVE_WEB_API_TOKEN) -or $env:NLVE_WEB_API_TOKEN.Length -lt 32) {
    throw "Set NLVE_WEB_API_TOKEN to a private value with at least 32 characters before public exposure."
}
if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
    throw "ngrok is not installed or is not available on PATH."
}
if ($OperatorExecutable -and -not (Test-Path -LiteralPath $OperatorExecutable -PathType Leaf)) {
    throw "OperatorExecutable does not exist."
}

New-Item -ItemType Directory -Force $runtimeDir, $logDir | Out-Null
Remove-Item -LiteralPath $runtimeFile -Force -ErrorAction SilentlyContinue

try {
    $webOut = Join-Path $logDir "web-server.out.log"
    $webErr = Join-Path $logDir "web-server.err.log"
    $packagedOperator = if ($OperatorExecutable) { $OperatorExecutable } else { Join-Path $repo "NLVE-Operator\NLVE-Operator.exe" }
    if (Test-Path -LiteralPath $packagedOperator) {
        $webExecutable = $packagedOperator
        $webArguments = @("serve", "--host", "127.0.0.1", "--port", "$Port")
    } else {
        $webExecutable = $PythonExecutable
        $webArguments = @("run.py", "serve", "--host", "127.0.0.1", "--port", "$Port")
    }
    $webProcess = Start-Process -FilePath $webExecutable -ArgumentList $webArguments -WorkingDirectory $repo -WindowStyle Hidden -RedirectStandardOutput $webOut -RedirectStandardError $webErr -PassThru

    $localReady = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Milliseconds 500
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/healthz" -TimeoutSec 2
            if ($health.status -eq "ok") { $localReady = $true; break }
        } catch { }
    }
    if (-not $localReady) { throw "The local web server did not become healthy." }

    $ngrokArgs = @(
        "http", "http://127.0.0.1:$Port",
        "--inspect=false", "--log=stdout", "--log-format=json"
    )
    if (-not [string]::IsNullOrWhiteSpace($Domain)) {
        $ngrokArgs += "--url=$Domain"
    }
    $ngrokOut = Join-Path $logDir "ngrok.out.log"
    $ngrokErr = Join-Path $logDir "ngrok.err.log"
    $ngrokProcess = Start-Process -FilePath "ngrok" -ArgumentList $ngrokArgs -WorkingDirectory $repo -WindowStyle Hidden -RedirectStandardOutput $ngrokOut -RedirectStandardError $ngrokErr -PassThru

    $publicUrl = $null
    $ngrokFailure = $null
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        Start-Sleep -Milliseconds 500
        foreach ($line in (Get-Content -LiteralPath $ngrokOut -ErrorAction SilentlyContinue)) {
            try {
                $event = $line | ConvertFrom-Json
                if ($event.url -like "https://*") { $publicUrl = $event.url; break }
                if ($event.err -and $event.lvl -in @("eror", "crit")) { $ngrokFailure = $event.err }
            } catch { }
        }
        if ($publicUrl) { break }
        if ($ngrokProcess.HasExited) { break }
    }
    if (-not $publicUrl) {
        if ($ngrokFailure) { throw "ngrok did not publish an HTTPS tunnel: $ngrokFailure" }
        throw "ngrok did not publish an HTTPS tunnel. Review $ngrokErr."
    }

    $publicHealth = Invoke-RestMethod -Uri "$publicUrl/healthz" -TimeoutSec 10
    if ($publicHealth.status -ne "ok") { throw "The public ngrok health check failed." }

    @{
        public_url = $publicUrl
        local_url = "http://127.0.0.1:$Port"
        web_process_id = $webProcess.Id
        ngrok_process_id = $ngrokProcess.Id
        started_at = (Get-Date).ToUniversalTime().ToString("o")
    } | ConvertTo-Json | Set-Content -LiteralPath $runtimeFile -Encoding utf8

    Write-Output "NLvoorelkaar Reachout is available at $publicUrl"
    Write-Output "Runtime details: $runtimeFile"
} catch {
    if ($ngrokProcess -and -not $ngrokProcess.HasExited) { Stop-Process -Id $ngrokProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($webProcess -and -not $webProcess.HasExited) { Stop-Process -Id $webProcess.Id -Force -ErrorAction SilentlyContinue }
    Remove-Item -LiteralPath $runtimeFile -Force -ErrorAction SilentlyContinue
    throw
}
