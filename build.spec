"""
PyInstaller build spec for Project Recorder.
"""

import sys
import os
from pathlib import Path

blockcipher = 'kxu'

a = Analysis(
    ['main.py'],
    pathex=[str(Path(__file__).parent)],
    binaries=[
        # Include ffmpeg if we bundle it
    ],
    datas=[
        # Include any additional assets
    ],
    hiddenimports=[
        'customtkinter',
        'whisper',
        'openai',
        'PIL',
        'ffmpeg',
        'ffmpeg.python',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'IPython',
        'notebook',
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=blockcipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=blockcipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ProjectRecorder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # TODO: Add icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ProjectRecorder',
)
