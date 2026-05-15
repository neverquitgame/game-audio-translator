# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file — build with: pyinstaller game_audio_translator.spec

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # Đưa toàn bộ thư mục src vào bundle
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
        # AI / Google
        "google.genai",
        "google.genai.types",
        "google.auth",
        "google.auth.transport",
        # Numpy
        "numpy",
        "numpy.core._multiarray_umath",
        # Misc
        "dotenv",
        "tkinter",
        "tkinter.ttk",
        "tkinter.messagebox",
        "queue",
        "threading",
        "logging",
        # Secure keyring
        "keyring",
        "keyring.backends",
        "keyring.backends.Windows",
        "keyring.backends.fail",
        "keyrings.alt",
        "keyrings.alt.file",
        "webbrowser",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Loại bỏ các module không cần để giảm kích thước
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
    upx=True,          # Nén bằng UPX nếu có — giảm ~30% kích thước
    upx_exclude=[
        "vcruntime140.dll",
        "python3*.dll",
        "api-ms-win-*.dll",
    ],
    runtime_tmpdir=None,
    console=False,     # Ẩn cửa sổ console — chỉ hiện GUI
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.ico",  # Bỏ comment nếu có file icon .ico
)
