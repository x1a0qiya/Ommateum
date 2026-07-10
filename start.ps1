#Requires -Version 5.1
# Ommateum — 视觉缺陷检测平台启动脚本 (PowerShell)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Ommateum — 视觉缺陷检测平台启动脚本" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ---- Step 1: Install ommateum package ----
Write-Host "[1/3] 检查 ommateum 包..." -ForegroundColor Yellow
$pkg = pip show ommateum 2>$null
if (-not $pkg) {
    Write-Host "  → 未安装，正在安装..." -ForegroundColor Gray
    pip install -e .
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [错误] ommateum 安装失败，请检查网络" -ForegroundColor Red
        Read-Host "按回车退出"
        exit 1
    }
    Write-Host "  ✓ 安装完成" -ForegroundColor Green
} else {
    Write-Host "  ✓ 已安装" -ForegroundColor Green
}

# ---- Step 2: Install API dependencies ----
Write-Host ""
Write-Host "[2/3] 安装 API 服务器依赖..." -ForegroundColor Yellow
Set-Location (Join-Path $ScriptDir "skills\ommateum-api")
pip install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [错误] 依赖安装失败" -ForegroundColor Red
    Read-Host "按回车退出"
    exit 1
}
Write-Host "  ✓ 依赖安装完成" -ForegroundColor Green

# ---- Step 3: Start server ----
Write-Host ""
Write-Host "[3/3] 启动 API 服务器..." -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  启动成功！" -ForegroundColor Green
Write-Host "  前端地址: http://localhost:5000" -ForegroundColor White
Write-Host "  API 地址: http://localhost:5000/api" -ForegroundColor White
Write-Host "  按 Ctrl+C 停止服务" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

python app.py
