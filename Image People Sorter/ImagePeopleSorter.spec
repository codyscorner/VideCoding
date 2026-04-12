# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Image People Sorter
"""

import sys
from pathlib import Path
import face_recognition_models

# Get face_recognition_models data path
models_path = Path(face_recognition_models.__file__).parent / 'models'

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        (str(models_path), 'face_recognition_models/models'),
        ('app_icon.ico', '.'),
    ],
    hiddenimports=[
        'face_recognition',
        'face_recognition_models',
        'dlib',
        'PIL',
        'PIL.Image',
        'numpy',
        'psutil',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ImagePeopleSorter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ImagePeopleSorter',
)
