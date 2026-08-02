# -*- mode: python ; coding: utf-8 -*-

import os
import sys

ROOT = os.path.abspath(SPECPATH)

if sys.platform == "win32":
    _icon = os.path.join(ROOT, "app", "ui", "logo.ico")
elif sys.platform == "darwin":
    _icon = os.path.join(ROOT, "app", "ui", "logo.icns")
else:
    _icon = None

a = Analysis(
    ['main.py'],
    pathex=['app'],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'app', 'ui', 'logo.png'), 'app/ui'),
        (os.path.join(ROOT, 'app', 'ui', 'assets'), 'app/ui/assets'),
        (os.path.join(ROOT, 'app', 'sounds'), 'app/sounds'),
        (os.path.join(ROOT, 'app', 'i18n'), 'app/i18n'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CosechaMedia',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
)
