# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\BlackSeas\\phyton\\BS1.7\\data', 'data'), ('C:\\BlackSeas\\phyton\\BS1.7\\assets', 'assets'), ('C:\\BlackSeas\\phyton\\BS1.7\\BlackSeas.spec', 'BlackSeas.spec'), ('C:\\BlackSeas\\phyton\\BS1.7\\build.ps1', 'build.ps1'), ('C:\\BlackSeas\\phyton\\BS1.7\\build.sh', 'build.sh'), ('C:\\BlackSeas\\phyton\\BS1.7\\config.py', 'config.py'), ('C:\\BlackSeas\\phyton\\BS1.7\\flota_guardada.json', 'flota_guardada.json'), ('C:\\BlackSeas\\phyton\\BS1.7\\MiApp.spec', 'MiApp.spec'), ('C:\\BlackSeas\\phyton\\BS1.7\\prompt estetica.txt', 'prompt estetica.txt'), ('C:\\BlackSeas\\phyton\\BS1.7\\README.md.txt', 'README.md.txt'), ('C:\\BlackSeas\\phyton\\BS1.7\\requeriments.txt', 'requeriments.txt'), ('C:\\BlackSeas\\phyton\\BS1.7\\test_imports.py', 'test_imports.py'), ('C:\\BlackSeas\\phyton\\BS1.7\\test_run.ps1', 'test_run.ps1')],
    hiddenimports=['openpyxl'],
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
    name='MiApp',
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
)
