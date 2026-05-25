@echo off
setlocal EnableDelayedExpansion
title Game Audio Translator — Build

echo ============================================================
echo   Game Audio Translator — Dong goi thanh .exe
echo ============================================================
echo.

:: Kiem tra uv (https://docs.astral.sh/uv/)
where uv >nul 2>&1
if errorlevel 1 (
    echo [LOI] Khong tim thay uv. Cai dat: https://docs.astral.sh/uv/getting-started/installation/
    pause & exit /b 1
)

:: Dong bo moi truong (.venv) va dependencies (gom PyInstaller)
echo [1/3] Dong bo dependencies voi uv...
uv sync --group dev
if errorlevel 1 (
    echo [LOI] uv sync that bai.
    pause & exit /b 1
)

:: Build
echo [2/3] Dang dong goi ung dung...
echo.
uv run pyinstaller game_audio_translator.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [LOI] Build that bai. Xem log o tren de biet nguyen nhan.
    pause & exit /b 1
)

:: Copy .env.example sang thu muc dist de nguoi dung tham khao
echo [3/3] Chuan bi thu muc phan phoi...
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
