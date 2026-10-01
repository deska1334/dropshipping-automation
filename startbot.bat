@echo off
chcp 65001 >nul
title Bot Dropshipping Automatise
cd /d "%~dp0"

echo ==============================================================
echo           DEMARRAGE DU BOT DROPSHIPPING AUTOMATISE           
echo ==============================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou pas accessible dans le PATH.
    echo Veuillez installer Python depuis https://www.python.org/
    pause
    exit /b 1
)

python startbot.py %*
if %errorlevel% neq 0 (
    pause
)
