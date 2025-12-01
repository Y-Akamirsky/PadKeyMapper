# pkm.spec

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Добавляем все основные файлы проекта как 'data'
a = Analysis(['main.py'],
             pathex=['.'], # Текущая директория
             binaries=[],
             datas=[
                 ('localization.py', '.'),
                 ('constants.py', '.'),
                 ('layouts.json', '.'),
                 ('config.json', '.'), # Включаем дефолтный config
             ],
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
          name='pkm-mapper', # Имя исполняемого файла
          debug=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True ) # Оставляем console=True для отображения ошибок MIDI/uinput
