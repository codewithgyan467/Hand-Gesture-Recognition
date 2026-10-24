# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for building GestureOS standalone distributable."""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Base directories
base_dir = os.path.abspath(os.path.dirname(__file__))

datas = [
    (os.path.join(base_dir, 'models', 'hand_landmarker.task'), 'models'),
    (os.path.join(base_dir, 'profiles'), 'profiles'),
]

# Hidden imports for dynamic modules
hiddenimports = [
    'mediapipe',
    'scipy',
    'scipy.spatial.transform._rotation_groups',
    'sklearn',
    'sklearn.ensemble',
    'sklearn.utils._typedefs',
    'joblib',
    'pycaw',
    'comtypes',
    'pynput',
    'pynput.keyboard',
    'pynput.mouse',
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
]

a = Analysis(
    ['run_gestureos.py'],
    pathex=[base_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'tkinter'],
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
    name='GestureOS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # Windowed GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GestureOS',
)
