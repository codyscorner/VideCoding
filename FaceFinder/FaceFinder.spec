# -*- mode: python ; coding: utf-8 -*-
import face_recognition_models
import tkinterdnd2

# Get the path to face_recognition_models data files
models_path = face_recognition_models.__path__[0]

# Get the path to tkinterdnd2 data files (contains platform-specific DLLs)
tkdnd_path = tkinterdnd2.__path__[0]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        (models_path, 'face_recognition_models'),
        (tkdnd_path, 'tkinterdnd2'),
        ('app_icon.ico', '.'),
    ],
    hiddenimports=[
        'face_recognition',
        'face_recognition_models',
        'dlib',
        'PIL',
        'numpy',
        'tkinter',
        'tkinterdnd2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# Splash screen shown instantly during startup
splash = Splash(
    'splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(10, 230),
    text_size=10,
    text_color='white',
    text_default='Loading...',
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    splash.binaries,
    [],
    exclude_binaries=True,
    name='FaceFinder',
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FaceFinder',
)
