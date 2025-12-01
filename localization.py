# localization.py

# --- 0. ЛОКАЛИЗАЦИЯ И НАСТРОЙКИ ---
# Дефолтный язык (RU или EN)
CURRENT_LANG = 'EN'

L10N = {
    'EN': {
        'APP_TITLE': "PadKey Mapper v2.2",
        'STATUS_READY': "Ready.",
        'STATUS_INIT': "⚡ Initializing Launchpad...",
        'STATUS_LISTENING': "✅ Listening: {port_name}",
        'STATUS_STOPPED': "🛑 Stopped.",
        'STATUS_ERROR': "❌ Thread Error: {error}",
        'STATUS_MAPPING_USED': "❌ {type} {id} is already in use!",
        'STATUS_ID_ERROR': "❌ ID must be a number!",
        'STATUS_UPDATED': "✅ Settings updated (applied instantly).",
        'LAYOUT_LABEL': "Layout:",
        'MIDI_MAPPER': "PKM: MIDI Mapper",
        'START_BTN': "▶️ START",
        'STOP_BTN': "⏹️ STOP",
        'THEME_BTN': "🌓 Theme",
        'ADD_MAPPING_BTN': "➕ Add Macro",
        'MAPPING_LIST_LABEL': "Assigned Mappings List",
        'MAPPING_NEW_DESC': "New macro",
        'EDIT_TITLE': "Editor: {id}",
        'EDIT_NEW_TITLE': "New",
        'EDIT_MIDI_ID': "MIDI Type/ID:",
        'EDIT_KEYS': "Keys:",
        'EDIT_DESC': "Description:",
        'EDIT_COLOR': "Color:",
        'EDIT_VIRTUAL_PAD': "Virtual Launchpad",
        'EDIT_SAVE': "💾 Save",
        'EDIT_CANCEL': "Cancel",
        'KEY_SELECT_TITLE': "Key Selection",
        'KEY_SELECT_LABEL': "Available Keys",
        'KEY_SELECT_SYMBOLS': "--- Characters ---",
        'LANGUAGE_LABEL': "Language:",

        # --- НОВЫЕ СТРОКИ ---
        'LEGACY_COLORS_LABEL': "Legacy Colors (Mini Mk1/S)",
        'EDIT_SHOW_LABELS': "Show IDs"
    },
    'RU': {
        'APP_TITLE': "PadKey Mapper v2.2",
        'STATUS_READY': "Готов к работе.",
        'STATUS_INIT': "⚡ Инициализация Launchpad...",
        'STATUS_LISTENING': "✅ Слушаю: {port_name}",
        'STATUS_STOPPED': "🛑 Остановлено.",
        'STATUS_ERROR': "❌ Ошибка потока: {error}",
        'STATUS_MAPPING_USED': "❌ {type} {id} уже занят!",
        'STATUS_ID_ERROR': "❌ ID должен быть числом!",
        'STATUS_UPDATED': "✅ Настройки обновлены (применены на лету).",
        'LAYOUT_LABEL': "Лейаут:",
        'MIDI_MAPPER': "PKM: MIDI Маппер",
        'START_BTN': "▶️ START",
        'STOP_BTN': "⏹️ STOP",
        'THEME_BTN': "🌓 Тема",
        'ADD_MAPPING_BTN': "➕ Добавить макрос",
        'MAPPING_LIST_LABEL': "Список назначений",
        'MAPPING_NEW_DESC': "Новый макрос",
        'EDIT_TITLE': "Редактор: {id}",
        'EDIT_NEW_TITLE': "Новое",
        'EDIT_MIDI_ID': "MIDI Тип/ID:",
        'EDIT_KEYS': "Клавиши:",
        'EDIT_DESC': "Описание:",
        'EDIT_COLOR': "Цвет:",
        'EDIT_VIRTUAL_PAD': "Виртуальный Launchpad",
        'EDIT_SAVE': "💾 Сохранить",
        'EDIT_CANCEL': "Отмена",
        'KEY_SELECT_TITLE': "Выбор клавиши",
        'KEY_SELECT_LABEL': "Доступные клавиши",
        'KEY_SELECT_SYMBOLS': "--- Символы ---",
        'LANGUAGE_LABEL': "Язык:",

        # --- НОВЫЕ СТРОКИ ---
        'LEGACY_COLORS_LABEL': "Режим старых цветов (Mini Mk1/S)",
        'EDIT_SHOW_LABELS': "Показать ID"
    }
}

def get_string(key, default=None, **kwargs):
    """
    Возвращает локализованную строку для текущего языка.
    Безопасная версия: если ключ не найден, не роняет программу.
    """
    global CURRENT_LANG

    # 1. Берем словарь текущего языка, или RU как запасной
    lang_dict = L10N.get(CURRENT_LANG, L10N['RU'])

    # 2. Ищем ключ в текущем языке -> если нет, то в RU -> если нет, то берем default -> если нет, возвращаем сам ключ
    if key in lang_dict:
        val = lang_dict[key]
    elif key in L10N['RU']:
        val = L10N['RU'][key]
    else:
        return default if default else key

    # 3. Форматируем строку (вставляем переменные {var})
    try:
        return val.format(**kwargs)
    except Exception:
        return val

def get_available_languages():
    """
    Возвращает список доступных кодов языков.
    """
    return list(L10N.keys())

def set_language(lang_code):
    """
    Устанавливает глобальный текущий язык.
    """
    global CURRENT_LANG
    if lang_code in L10N:
        CURRENT_LANG = lang_code
        return True
    return False
