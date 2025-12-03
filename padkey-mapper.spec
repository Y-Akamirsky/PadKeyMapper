# padkey-mapper.spec
# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import glob
from PyInstaller.utils.hooks import collect_all

# =========================================================================
UINPUT_DIR = '/home/akamirsky/Some-scripts/Python/MIDIHK/venv/lib/python3.13/site-packages/uinput'
UINPUT_SO_PATH = '/home/akamirsky/Some-scripts/Python/MIDIHK/venv/lib/python3.13/site-packages/_libsuinput.cpython-313-x86_64-linux-gnu.so'
# =========================================================================


# --- 1. Файлы данных (datas) ---
datas = [
    ('layouts.json', '.'),
    ('PKMICON2.png', '.'),
    ('pad-key-mapper.desktop', '.')
]

# !!! РОБУСТНОЕ РЕШЕНИЕ ДЛЯ UINPUT (ТОЛЬКО .py) !!!
# (Это гарантирует, что Python-файлы uinput не теряются)
try:
    UINPUT_PYTHON_FILES = glob.glob(os.path.join(UINPUT_DIR, '*.py'))
    datas += [(f, 'uinput') for f in UINPUT_PYTHON_FILES]
except Exception as e:
    print(f"Ошибка ручного сбора uinput .py файлов: {e}")


# --- 2. Хуки и явная коллекция ресурсов ---
# !!! КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: ДОБАВЛЯЕМ TKINTER !!!
# Убираем 'uinput' из hiddenimports, чтобы не конфликтовать с ручным сбором.
hiddenimports = ['sysconfig', 'distutils', 'tkinter']

# Явно собираем customtkinter (должно также включать Tcl/Tk)
try:
    tmp_ret = collect_all('customtkinter')
    datas += tmp_ret[0]
    hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"Ошибка сбора customtkinter: {e}")

# Явно собираем mido
try:
    tmp_ret = collect_all('mido')
    hiddenimports += ['mido.backends.rtmidi']
    datas += tmp_ret[0]
    hiddenimports += tmp_ret[2]
except Exception as e:
    print(f"Ошибка сбора mido: {e}")

# --- 3. Analysis and build (binaries) ---
a = Analysis(
    ['main.py', 'constants.py', 'localization.py'],
    pathex=[],
    # !!! ДОБАВЛЯЕМ C-расширение UINPUT (.so) !!!
    # Целевая папка 'uinput' соответствует, куда мы скопировали .py файлы.
    binaries=[(UINPUT_SO_PATH, 'uinput')],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Убираем 'excludes' для tkinter, так как мы его явно импортируем!
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PadKeyMapper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PadKeyMapper',
)
