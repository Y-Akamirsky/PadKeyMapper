# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import glob
from PyInstaller.utils.hooks import collect_all

# --- 1. АВТОМАТИЧЕСКИЙ ПОИСК БИБЛИОТЕК ---

# 1.1 Поиск uinput (Усиленный поиск .so файла)
try:
    import uinput
    # Путь к папке пакета 'uinput' (e.g., .../site-packages/uinput)
    UINPUT_DIR = os.path.dirname(uinput.__file__)
    # Путь к папке site-packages (родитель UINPUT_DIR)
    SITE_PACKAGES_DIR = os.path.dirname(UINPUT_DIR)

    # --- Ищем .so файл (начинается с _libsuinput) ---

    # 1. Ищем в корне site-packages (стандартное место для python-uinput)
    so_files = glob.glob(os.path.join(SITE_PACKAGES_DIR, '_libsuinput*.so'))

    # 2. Если не нашли, ищем в папке пакета uinput (на всякий случай)
    if not so_files:
        so_files = glob.glob(os.path.join(UINPUT_DIR, '_libsuinput*.so'))

    # 3. Если все еще не нашли, ищем по более широкой маске в site-packages
    if not so_files:
        so_files = glob.glob(os.path.join(SITE_PACKAGES_DIR, '*.so'))

    if not so_files:
         # <-- Здесь была ошибка. Теперь бросаем ее после всех попыток.
         raise FileNotFoundError("Не найден .so файл для uinput. Проверьте, что пакет python-uinput установлен корректно.")

    UINPUT_SO_PATH = so_files[0]
    print(f"✅ Found uinput package at: {UINPUT_DIR}")
    print(f"✅ Found uinput .so lib at: {UINPUT_SO_PATH}")
except ImportError:
    print("❌ Uinput not found! Please install it in this venv.")
    sys.exit(1)

# 1.2 Поиск CustomTkinter
try:
    import customtkinter
    ctk_path = os.path.dirname(customtkinter.__file__)
    print(f"✅ Found CustomTkinter at: {ctk_path}")
except ImportError:
    print("❌ CustomTkinter not found! Run: pip install customtkinter")
    sys.exit(1)


# --- 2. СБОР ДАННЫХ (DATAS) ---
datas = [
    ('layouts.json', '.'),
    ('icons/PR-PKMICON.png', '.'),
    ('pad-key-mapper.desktop', '.'),

    # ПРИНУДИТЕЛЬНО КОПИРУЕМ CUSTOMTKINTER ЦЕЛИКОМ
    (ctk_path, 'customtkinter'),

    # КОПИРУЕМ UINPUT PYTHON ФАЙЛЫ
    (os.path.join(UINPUT_DIR, '*.py'), 'uinput')
]


# --- 3. СКРЫТЫЕ ИМПОРТЫ (HIDDENIMPORTS) ---
hiddenimports = [
    'sysconfig',
    'distutils',
    'tkinter',
    'PIL._tkinter_finder',
    # Важные зависимости CTk, которые иногда теряются
    'customtkinter',
    'darkdetect',
    'packaging',
    'packaging.version',
    'packaging.specifiers',
    'packaging.requirements'
]

# Собираем данные Mido
tmp_mido = collect_all('mido')
hiddenimports += ['mido.backends.rtmidi']
datas += tmp_mido[0]
hiddenimports += tmp_mido[2]


# --- 4. БИНАРНИКИ ---
# Uinput .so кладем в корень (для загрузчика) и в папку пакета (для питона)
binaries = [
    (UINPUT_SO_PATH, '.'),       # Кладем в корень сборки (dist/PadKeyMapper/)
    (UINPUT_SO_PATH, 'uinput')   # Кладем в папку пакета (dist/PadKeyMapper/uinput)
]

block_cipher = None

a = Analysis(
    ['main.py', 'constants.py', 'localization.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='PadKeyMapper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, # Оставь True для отладки
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
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
