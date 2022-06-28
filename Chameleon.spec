# -*- mode: python -*-

import platform
import re
from os.path import isfile

is_mac = platform.system().lower() == "darwin"

block_cipher = None

VERSION_FILE = "chameleon/resources/version.txt"
FILTER_FILE = "chameleon/resources/filter.yaml"

added_files = [
    ("chameleon/resources/chameleon.png", "."),
    ("chameleon/resources/extracolumns.yaml", "."),
    ("chameleon/resources/OSMtag.txt", "."),
]
if isfile(FILTER_FILE):
    added_files.append(
        (FILTER_FILE, "."),
    )
try:
    with open(VERSION_FILE, "r") as fp:
        version_string = fp.read()
except OSError:
    APP_VERSION = "0.0.0"
else:
    added_files.append((VERSION_FILE, "."))

    version_split = version_string[1:].split(".")
    version_re = re.compile(r"(?<=\d)([A-z])[A-z]+(?=\d)*")
    # shortens words like "alpha" or "beta" to first character
    version_split = [version_re.sub(r"\1", i) for i in version_split]
    APP_VERSION = ".".join(version_split)


a = Analysis(
    ["chameleon/qt/qt.py"],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        "chameleon.qt.design",
        "cmath",
        "pandas._libs.tslibs.timedeltas",
        "pytest",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["ptvsd"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
items = (
    []
    if is_mac
    else [
        a.binaries,
        a.zipfiles,
        a.datas,
    ]
)
exe = EXE(
    pyz,
    a.scripts,
    *items,
    [],
    exclude_binaries=is_mac,
    name="Chameleon",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    icon="chameleon/resources/chameleon.icns" if is_mac else None,
)
if is_mac:
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
        bundle_identifier="com.kaart.chameleon",
        info_plist={
            "NSHighResolutionCapable": "True",
            "CFBundleVersion": APP_VERSION,
            "CFBundleShortVersionString": APP_VERSION,
        },
    )
