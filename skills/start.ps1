# Ommateum 一键启动脚本 (PowerShell)
# 启动 Flask 后端 + nginx 前端

$ErrorActionPreference = "Stop"
$ROOT = "c:\Users\ZCY\Desktop\skills"
$API_DIR = Join-Path $ROOT "ommateum-api"
$NGINX_DIR = Join-Path $ROOT "nginx-1.31.2"

Write-Host ""
Write-Host "  Ommateum Visual Defect Detection Platform" -ForegroundColor Cyan
Write-Host "  ===========================================" -ForegroundColor DarkGray
Write-Host ""

# ---- 1. Check Python ----
Write-Host "[1/4] 检查 Python..." -ForegroundColor Yellow
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>$null
        if ($LASTEXITCODE -eq 0) { $python = $cmd; break }
    } catch {}
}
if (-not $python) {
    Write-Host "  ✗ 未找到 Python，请安装 Python 3.8+" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ $python $(& $python --version 2>&1)" -ForegroundColor Green

# ---- 2. Install dependencies ----
Write-Host "[2/4] 安装后端依赖..." -ForegroundColor Yellow
Push-Location $API_DIR
& $python -m pip install -r requirements.txt --quiet
Pop-Location
Write-Host "  ✓ 依赖就绪" -ForegroundColor Green

# ---- 3. Start Flask backend ----
Write-Host "[3/4] 启动 Flask 后端 (:5000)..." -ForegroundColor Yellow
$apiJob = Start-Job -ScriptBlock {
    param($dir, $py)
    Set-Location $dir
    & $py app.py
} -ArgumentList $API_DIR, $python

# Wait for backend to be ready
Start-Sleep -Seconds 3
$ready = $false
for ($i = 0; $i -lt 10; $i++) {
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/health" -TimeoutSec 2 -ErrorAction Stop
        $ready = $true; break
    } catch { Start-Sleep -Seconds 1 }
}
if ($ready) {
    Write-Host "  ✓ Flask 后端已就绪 (http://127.0.0.1:5000/api)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ 后端启动较慢，请稍候..." -ForegroundColor DarkYellow
}

# ---- 4. Start nginx ----
Write-Host "[4/4] 启动 nginx (:80)..." -ForegroundColor Yellow
# Ensure required directories exist
New-Item -ItemType Directory -Force -Path (Join-Path $NGINX_DIR "logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $NGINX_DIR "temp") | Out-Null
# Stop existing nginx
try { Push-Location $NGINX_DIR; & ".\nginx.exe" -s stop 2>$null; Pop-Location } catch {}
Start-Sleep -Seconds 1
Push-Location $NGINX_DIR
Start-Process -FilePath ".\nginx.exe" -WorkingDirectory $NGINX_DIR -WindowStyle Hidden
Pop-Location
Start-Sleep -Seconds 1
Write-Host "  ✓ nginx 已启动 (http://localhost)" -ForegroundColor Green

Write-Host ""
Write-Host "  ===========================================" -ForegroundColor DarkGray
Write-Host "  平台已启动！" -ForegroundColor Cyan
Write-Host "  前端:  http://localhost" -ForegroundColor White
Write-Host "  API:   http://localhost/api" -ForegroundColor White
Write-Host "  ===========================================" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  按 Ctrl+C 停止后端。停止 nginx:  cd nginx-1.31.2; .\nginx.exe -s stop" -ForegroundColor DarkGray
Write-Host ""

# Keep script running; stop backend on exit
try {
    Receive-Job $apiJob -Wait
} finally {
    Stop-Job $apiJob -ErrorAction SilentlyContinue
    Remove-Job $apiJob -ErrorAction SilentlyContinue
}
