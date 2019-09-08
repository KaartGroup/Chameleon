# -*- mode: python -*-

block_cipher = None

added_files = [
                ('resources/OSMtag.yaml', 'data'),
                ('resources/chameleonalpha.png', '.')
             ]

a = Analysis(['chameleon2/main.py'],
             pathex=['/Users/primaryuser/chameleon-2'],
             binaries=[],
             datas= added_files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='Chameleon 2',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False , icon=None)
