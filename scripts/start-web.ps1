param(
    [int]$Port = 8765,
    [string]$PythonExecutable = "python",
    [string]$OperatorExecutable = ""
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($env:NLVE_WEB_API_TOKEN) -or $env:NLVE_WEB_API_TOKEN.Length -lt 32) {
    throw "Set NLVE_WEB_API_TOKEN to a private value with at least 32 characters."
}
if ($Port -lt 1 -or $Port -gt 65535) {
    throw "Port must be between 1 and 65535."
}
if ($OperatorExecutable -and -not (Test-Path -LiteralPath $OperatorExecutable -PathType Leaf)) {
    throw "OperatorExecutable does not exist."
}

Push-Location $repo
try {
    $packagedOperator = if ($OperatorExecutable) { $OperatorExecutable } else { Join-Path $repo "NLVE-Operator\NLVE-Operator.exe" }
    if (Test-Path -LiteralPath $packagedOperator) {
        & $packagedOperator serve --host 127.0.0.1 --port $Port
    } else {
        & $PythonExecutable run.py serve --host 127.0.0.1 --port $Port
    }
} finally {
    Pop-Location
}
