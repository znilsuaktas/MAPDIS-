[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        throw 'Python launcher bulunamadi. Python 3.10+ kurun ve terminali yeniden acin.'
    }
    & py -3 -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'"
    if ($LASTEXITCODE -ne 0) { throw 'Python surum kontrolu basarisiz.' }
    if (-not (Test-Path '.venv/Scripts/python.exe')) {
        & py -3 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Sanal ortam olusturulamadi.' }
    }
    & ./.venv/Scripts/python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Bagimlilik kurulumu basarisiz.' }
    & ./.venv/Scripts/python.exe -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Testler basarisiz.' }
    Write-Host 'Kurulum tamamlandi. VS Code Python interpreter: .venv/Scripts/python.exe'
} finally {
    Pop-Location
}
