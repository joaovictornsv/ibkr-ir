# PyInstaller spec — build with: pyinstaller ibkr-ir.spec
# See scripts/build-binary.sh and .github/workflows/release.yml

block_cipher = None

a = Analysis(
    ["generate.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=[
        "src",
        "src.calculator",
        "src.models",
        "src.parser",
        "src.prices",
        "src.ptax",
        "src.report",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name="ibkr-ir",
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
