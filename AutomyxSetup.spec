# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\Users\\COMPUMAX\\Documents\\AUTOMIX 2.5win, mac, rasberry pi\\installer_app.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\COMPUMAX\\Documents\\AUTOMIX 2.5win, mac, rasberry pi\\dist\\Automyx.zip', '.')],
    hiddenimports=['rich', 'rich.console', 'rich.panel', 'rich.text', 'rich.prompt', 'rich.progress', 'rich.rule', 'rich.live', 'rich.box'],
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
    name='AutomyxSetup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\COMPUMAX\\Documents\\AUTOMIX 2.5win, mac, rasberry pi\\assets\\logo.ico'],
)
