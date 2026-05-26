@echo off
setlocal EnableDelayedExpansion
title Game Audio Translator - Build

echo ============================================================
echo   Game Audio Translator - Dong goi thanh .exe
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
    echo [1/3] Tao moi truong ao...
    python -m venv .venv
) else (
    echo [1/3] Moi truong ao da ton tai.
)

call .venv\Scripts\activate.bat

:: Cai dependencies (bao gom pyinstaller)
echo [2/3] Cai dat dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [LOI] Cai dat requirements.txt that bai.
    pause & exit /b 1
)

:: Build
echo [3/3] Dang dong goi ung dung...
echo.
pyinstaller game_audio_translator.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [LOI] Build that bai. Xem log o tren de biet nguyen nhan.
    pause & exit /b 1
)

if exist "dist\GameAudioTranslator.exe" (
    echo.
    echo ============================================================
    echo   BUILD THANH CONG!
    echo ============================================================
    echo.
    echo   File exe: dist\GameAudioTranslator.exe
    echo.
    echo   Lan dau chay:
    echo   - Wizard se huong dan nhap API key (Gemini/OpenAI/Anthropic)
    echo     hoac dung Ollama chay local
    echo   - Whisper model duoc tai ve tu dong (~150 MB cho 'base')
    echo.
    echo   Cau hinh duoc luu tai:
    echo     %%APPDATA%%\GameAudioTranslator\settings.json
    echo ============================================================
) else (
    echo [LOI] Khong tim thay file exe sau khi build.
)

echo.
pause
