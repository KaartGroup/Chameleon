# -*- mode: python -*-

block_cipher = None

added_files = [
    ("chameleon/resources/chameleon.png", "."),
    ("chameleon/resources/extracolumns.yaml", "."),
    ("chameleon/resources/OSMtag.txt", "."),
    ("resources/version.txt", "."),
]


a = Analysis(
    ["chameleon/qt/qt.py"],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        "chameleon.qt.design",
        "pandas._libs.tslibs.timedeltas",
        "pytest",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["ptvsd",],
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
    name="Chameleon",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="chameleon/resources/chameleon.icns",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="Chameleon",
)
app = BUNDLE(
    coll,
    name="Chameleon.app",
    icon="chameleon/resources/chameleon.icns",
    bundle_identifier=None,
    info_plist={"NSHighResolutionCapable": "True",},
)
