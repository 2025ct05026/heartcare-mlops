param(
    [ValidateSet('setup','train','verify','serve','tracking')]
    [string]$Action = 'verify'
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
function Invoke-ProjectStep {
    param([string[]]$Arguments)
    & $projectPython @Arguments
    if ($LASTEXITCODE -ne 0) { throw ('Step failed: python ' + ($Arguments -join ' ')) }
}
if ($Action -eq 'setup') {
    if (-not (Test-Path -LiteralPath $projectPython)) {
        & py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 and retry setup.' }
    }
    Invoke-ProjectStep -Arguments @('-m','pip','install','-r','requirements.txt')
    exit
}
if (-not (Test-Path -LiteralPath $projectPython)) { throw 'First run .\run.ps1 setup' }
switch ($Action) {
    'train' {
        Invoke-ProjectStep -Arguments @('-m','heartcare.data')
        Invoke-ProjectStep -Arguments @('-m','heartcare.eda')
        Invoke-ProjectStep -Arguments @('-m','heartcare.train')
    }
    'verify' {
        Invoke-ProjectStep -Arguments @('-m','ruff','check','heartcare','test','scripts')
        Invoke-ProjectStep -Arguments @('-m','pytest','-q')
    }
    'serve' { Invoke-ProjectStep -Arguments @('-m','uvicorn','heartcare.api:app','--host','127.0.0.1','--port','8000') }
    'tracking' { Invoke-ProjectStep -Arguments @('-m','mlflow','ui','--backend-store-uri','sqlite:///mlflow.db','--host','127.0.0.1','--port','5000') }
}

