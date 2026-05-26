# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — build:
#   Windows : pyinstaller game_audio_translator.spec
#   macOS   : pyinstaller game_audio_translator.spec
#             (thêm --target-arch arm64 nếu build cho Apple Silicon)

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("src", "src"),
    ],
    hiddenimports=[
        # faster-whisper / ctranslate2
        "faster_whisper",
        "ctranslate2",
        "ctranslate2.specs",
        # Audio
        "pyaudio",
        "pyaudiowpatch",
        "webrtcvad",
        # LLM — chỉ dùng litellm cho mọi provider
        "litellm",
        # Numpy / Scipy
        "numpy",
        "numpy.core._multiarray_umath",
        "scipy",
        "scipy.signal",
        # PySide6
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        # Misc
        "queue",
        "threading",
        "logging",
        "platformdirs",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # SDK trùng chức năng với litellm — không cần
        "google",
        "google.genai",
        "google.auth",
        "openai",
        "anthropic",
        # OS keyring — không còn dùng (lưu key trong settings.json)
        "keyring",
        "keyrings",
        # UI / dev tools không dùng
        "tkinter",
        "matplotlib",
        "PIL",
        "IPython",
        "jupyter",
        "pytest",
        "setuptools",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="GameAudioTranslator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[
        "vcruntime140.dll",
        "python3*.dll",
        "api-ms-win-*.dll",
        "Qt6*.dll",         # Không nén Qt DLL — tránh crash
    ],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.ico",   # Windows
)

# macOS: đóng gói thành .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="GameAudioTranslator.app",
        # icon="assets/icon.icns",  # macOS icon
        bundle_identifier="com.gameaudiotranslator.app",
        info_plist={
            "NSMicrophoneUsageDescription": "Ứng dụng cần truy cập micro để nhận dạng giọng nói.",
            "NSHighResolutionCapable": True,
            "LSUIElement": False,
        },
    )
