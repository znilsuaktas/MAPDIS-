[CmdletBinding()]
param(
    [Alias('Profile')]
    [ValidateSet('oil_spill','plastic','mucilage','all','marine_pollution')]
    [string]$SearchProfile = 'marine_pollution',
    [ValidateRange(1,100)][int]$MaxQueries = 2,
    [ValidateRange(1,20)][int]$Pages = 1,
    [string]$ReplayInput = '',
    [switch]$OpenDashboard
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    $PythonExecutable = Join-Path $ProjectRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path $PythonExecutable)) { throw 'Once scripts/Setup-Local.ps1 calistirin.' }
    $OutputFolder = Join-Path $ProjectRoot ('output/local_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
    $Operation = 'run'
    if ($ReplayInput) { $Operation = 'replay' }
    $CommandArgs = @('-m','mapdis_research',$Operation,'--config','config/advanced.json','--profile',$SearchProfile,'--max-queries',"$MaxQueries",'--pages',"$Pages",'--output',$OutputFolder)
    if ($ReplayInput) { $CommandArgs += @('--input',$ReplayInput) }
    & $PythonExecutable @CommandArgs
    if ($LASTEXITCODE -ne 0) { throw "Tarama kismen veya tamamen basarisiz. Varsa run.json ve search_log.json dosyalarini inceleyin: $OutputFolder" }
    Write-Host "Ciktilar: $OutputFolder"
    if ($OpenDashboard) { Start-Process (Join-Path $OutputFolder 'dashboard.html') }
} finally {
    Pop-Location
}
