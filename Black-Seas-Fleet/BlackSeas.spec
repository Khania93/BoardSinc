# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = (
    collect_submodules("pandas")
    + collect_submodules("openpyxl")
    + collect_submodules("PIL")
)

datas = [
    ("assets", "assets"),
    ("data", "data"),
    ("pdf", "pdf"),
    ("saves", "saves"),
]

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter.test",
        "test",
        "tests",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="BlackSeas",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="assets/iconos/icon.ico",   # Cambia si el icono tiene otro nombre
)