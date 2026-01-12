param(
    [string]$RepoRoot = (Resolve-Path -LiteralPath "$PSScriptRoot\..\")
)

$codexHome = Join-Path $RepoRoot ".codex"

$env:CODEX_HOME = $codexHome
Write-Host "CODEX_HOME set to $codexHome for this session."
Write-Host "Run Codex from this shell to use project-local skills."
