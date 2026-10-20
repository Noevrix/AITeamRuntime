param(
    [string]$Python = 'python',
    [string]$DshBin = ''
)
$ErrorActionPreference = 'Stop'
$probeScript = Join-Path $PSScriptRoot 'dsh_plan_probe.py'

# This preflight imports code only. It cannot submit a model request.
& $Python $probeScript --preflight
if ($LASTEXITCODE -ne 0) { throw 'Local dependencies unavailable. No model called.' }

$previousKey = $env:DEEPSEEK_API_KEY
$previousBin = $env:AI_TEAM_DSH_BIN
$secureInput = $null
$probeExit = 1
try {
    if ($DshBin) {
        if (-not (Test-Path -LiteralPath $DshBin -PathType Leaf)) { throw 'DSH launcher not found.' }
        $env:AI_TEAM_DSH_BIN = $DshBin
    }
    Write-Host 'This submits ONE planning turn through DSHAdapter. No Codex or full workflow.'
    $secureInput = Read-Host 'Enter DeepSeek API Key locally (hidden)' -AsSecureString
    if ($secureInput.Length -eq 0) { throw 'Empty input. No model called.' }
    # Process environment only; the key is not an argument, file, or history entry.
    $env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new('', $secureInput).Password
    & $Python $probeScript
    $probeExit = $LASTEXITCODE
} finally {
    if ($null -ne $secureInput) { $secureInput.Dispose() }
    if ($null -eq $previousKey) { Remove-Item Env:DEEPSEEK_API_KEY -ErrorAction SilentlyContinue }
    else { $env:DEEPSEEK_API_KEY = $previousKey }
    if ($null -eq $previousBin) { Remove-Item Env:AI_TEAM_DSH_BIN -ErrorAction SilentlyContinue }
    else { $env:AI_TEAM_DSH_BIN = $previousBin }
    Remove-Variable previousKey -ErrorAction SilentlyContinue
}
if ($probeExit -ne 0) { throw 'Probe did not pass. Do not retry automatically; share only the summary status.' }
