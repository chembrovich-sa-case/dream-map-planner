param(
    [string]$Message
)

Set-Location $PSScriptRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Horizont (Dream Map Planner) - Auto Sync to GitHub" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path "C:\dev\flutter\bin\mingit\cmd\git.exe") {
    $env:PATH = "C:\dev\flutter\bin\mingit\cmd;C:\dev\flutter\bin\mingit\mingw64\bin;$env:PATH"
}

if (-not $Message) {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $Message = "Auto update: $timestamp"
}

Write-Host "[1/3] Adding changes (git add .)..." -ForegroundColor Yellow
git add .

Write-Host "[2/3] Creating commit..." -ForegroundColor Yellow
git commit -m "$Message"

Write-Host "[3/3] Pushing to GitHub (git push origin main)..." -ForegroundColor Yellow
git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host "  [SUCCESS] All changes pushed to GitHub!" -ForegroundColor Green
    Write-Host "  Live app: https://chembrovich-sa-case.github.io/dream-map-planner/" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[ERROR] Push failed. Check your internet connection." -ForegroundColor Red
}
