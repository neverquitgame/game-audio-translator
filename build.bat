@echo off
setlocal EnableDelayedExpansion
title Game Audio Translator — Build

echo ============================================================
echo   Game Audio Translator — Dong goi thanh .exe
echo ============================================================
echo.

:: Kiem tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [LOI] Khong tim thay Python. Hay cai Python 3.10+ va thu lai.
    pause & exit /b 1
)

:: Tao/kich hoat moi truong ao neu chua co
if not exist ".venv\Scripts\activate.bat" (
    echo [1/4] Tao moi truong ao...
    python -m venv .venv
) else (
    echo [1/4] Moi truong ao da ton tai.
)

call .venv\Scripts\activate.bat

:: Cai dependencies
echo [2/4] Cai dat dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [LOI] Cai dat requirements.txt that bai.
    pause & exit /b 1
)

:: Cai PyInstaller
pip install pyinstaller --quiet
if errorlevel 1 (
    echo [LOI] Cai dat PyInstaller that bai.
    pause & exit /b 1
)

:: Build
echo [3/4] Dang dong goi ung dung...
echo.
pyinstaller game_audio_translator.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [LOI] Build that bai. Xem log o tren de biet nguyen nhan.
    pause & exit /b 1
)

:: Copy .env.example sang thu muc dist de nguoi dung tham khao
echo [4/4] Chuan bi thu muc phan phoi...
if exist "dist\GameAudioTranslator.exe" (
    copy ".env.example" "dist\.env.example" >nul
    echo.
    echo ============================================================
    echo   BUILD THANH CONG!
    echo ============================================================
    echo.
    echo   File exe: dist\GameAudioTranslator.exe
    echo.
    echo   Truoc khi chay, nguoi dung can:
    echo   1. Copy file .env.example thanh .env
    echo      (trong cung thu muc voi GameAudioTranslator.exe)
    echo   2. Dien GEMINI_API_KEY vao file .env
    echo   3. Chay GameAudioTranslator.exe
    echo.
    echo   Luu y: Lan dau chay se tai Whisper model (~150 MB)
    echo ============================================================
) else (
    echo [LOI] Khong tim thay file exe sau khi build.
)

echo.
pause
