# -*- mode: python -*-

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

added_files = [
    ('resources/OSMtag.yaml', '.'),
    ('resources/chameleon.png', '.'),
    ('resources/version.txt', '.')
]

added_files += collect_data_files('geopandas')
added_files += collect_data_files('osm2geojson')
added_files += collect_data_files('fiona')
added_files += collect_data_files('shapely')


a = Analysis(
    ['chameleon/main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'fiona._shim',
        'fiona.schema',
        'pandas._libs.tslibs.timedeltas',
        'pyproj.datadir',
        'pytest',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'ptvsd',
        'rtree'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False)
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Chameleon',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, icon='resources/chameleon.icns'
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='Chameleon'
)
app = BUNDLE(
    coll,
    name='Chameleon.app',
    icon='resources/chameleon.icns',
    bundle_identifier=None,
    info_plist={
        'NSHighResolutionCapable': 'True',
    },
)
