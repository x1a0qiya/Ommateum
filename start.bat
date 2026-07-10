@echo off
chcp 65001 >nul
title Ommateum 启动脚本

echo ============================================
echo   Ommateum — 视觉缺陷检测平台启动脚本
echo ============================================
echo.

:: 获取脚本所在目录
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

:: ---------- 第一步：安装 ommateum 包 ----------
echo [1/3] 检查 ommateum 包...
pip show ommateum >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   → 未安装，正在安装...
    pip install -e .
    if %ERRORLEVEL% NEQ 0 (
        echo   [错误] ommateum 安装失败，请检查网络
        pause
        exit /b 1
    )
    echo   ✓ 安装完成
) else (
    echo   ✓ 已安装
)

:: ---------- 第二步：安装 API 依赖 ----------
echo.
echo [2/3] 安装 API 服务器依赖...
cd /d "%SCRIPT_DIR%skills\ommateum-api"
pip install -r requirements.txt -q
if %ERRORLEVEL% NEQ 0 (
    echo   [错误] 依赖安装失败
    pause
    exit /b 1
)
echo   ✓ 依赖安装完成

:: ---------- 第三步：启动服务器 ----------
echo.
echo [3/3] 启动 API 服务器...
echo.
echo ============================================
echo   启动成功！
echo   前端地址: http://localhost:5000
echo   API 地址: http://localhost:5000/api
echo   按 Ctrl+C 停止服务
echo ============================================
echo.

python app.py

pause
