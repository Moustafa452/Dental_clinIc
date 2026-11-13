\
# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

# The .spec file lives in <project>\packaging\.
# SPECPATH is therefore the packaging directory; anchor everything to
# the actual project root so PyInstaller never looks for packaging\app.py.
PROJECT_ROOT = Path(SPECPATH).resolve().parent
APP_ENTRY = PROJECT_ROOT / "app.py"

hidden = collect_submodules("PySide6.QtCharts")

a = Analysis(
    [str(APP_ENTRY)],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
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
    [],
    exclude_binaries=True,
    name="DentalLab",
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DentalLab",
)
