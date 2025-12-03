# constants.py
import uinput

# --- 1. СЛОВАРИ И ПРЕОБРАЗОВАНИЕ КЛАВИШ ---

# Основной словарь для маппинга названий клавиш в uinput коды
KEY_MAPPINGS = {
    'Key.ctrl': uinput.KEY_LEFTCTRL, 'Key.alt': uinput.KEY_LEFTALT,
    'Key.shift': uinput.KEY_LEFTSHIFT, 'Key.cmd': uinput.KEY_LEFTMETA,
    'Key.enter': uinput.KEY_ENTER, 'Key.space': uinput.KEY_SPACE,
    'Key.tab': uinput.KEY_TAB, 'Key.esc': uinput.KEY_ESC,
    'Key.backspace': uinput.KEY_BACKSPACE,
    'Key.f1': uinput.KEY_F1, 'Key.f2': uinput.KEY_F2, 'Key.f3': uinput.KEY_F3,
    'Key.f4': uinput.KEY_F4, 'Key.f5': uinput.KEY_F5, 'Key.f6': uinput.KEY_F6,
    'Key.f7': uinput.KEY_F7, 'Key.f8': uinput.KEY_F8, 'Key.f9': uinput.KEY_F9,
    'Key.f10': uinput.KEY_F10, 'Key.f11': uinput.KEY_F11, 'Key.f12': uinput.KEY_F12,
    'Key.delete': uinput.KEY_DELETE, 'Key.insert': uinput.KEY_INSERT,
    'Key.home': uinput.KEY_HOME, 'Key.end': uinput.KEY_END,
    'Key.page_up': uinput.KEY_PAGEUP, 'Key.page_down': uinput.KEY_PAGEDOWN,
    'Key.up': uinput.KEY_UP, 'Key.down': uinput.KEY_DOWN, 'Key.left': uinput.KEY_LEFT,
    'Key.right': uinput.KEY_RIGHT,
    'Key.ctrl_l': uinput.KEY_LEFTCTRL, 'Key.ctrl_r': uinput.KEY_RIGHTCTRL,
    'Key.alt_l': uinput.KEY_LEFTALT, 'Key.alt_r': uinput.KEY_RIGHTALT,
    'Key.shift_l': uinput.KEY_LEFTSHIFT, 'Key.shift_r': uinput.KEY_RIGHTSHIFT,
    'Key.cmd_l': uinput.KEY_LEFTMETA, 'Key.cmd_r': uinput.KEY_RIGHTMETA,
    'Key.caps_lock': uinput.KEY_CAPSLOCK, 'Key.num_lock': uinput.KEY_NUMLOCK,
    'Key.print_screen': uinput.KEY_SYSRQ,
    'Key.num0': uinput.KEY_KP0, 'Key.num1': uinput.KEY_KP1,
    'Key.num2': uinput.KEY_KP2, 'Key.num3': uinput.KEY_KP3,
    'Key.num4': uinput.KEY_KP4, 'Key.num5': uinput.KEY_KP5,
    'Key.num6': uinput.KEY_KP6, 'Key.num7': uinput.KEY_KP7,
    'Key.num8': uinput.KEY_KP8, 'Key.num9': uinput.KEY_KP9,
    'Key.num_dot': uinput.KEY_KPDOT, 'Key.num_plus': uinput.KEY_KPPLUS,
    'Key.num_min': uinput.KEY_KPMINUS, 'Key.num_eq': uinput.KEY_KPEQUAL,
    'Key.num_comm': uinput.KEY_KPCOMMA, 'Key.num_ast': uinput.KEY_KPASTERISK,
}

# Карта для отображения читаемых имен клавиш в GUI (ALT вместо Key.alt)
KEY_DISPLAY_MAPPINGS = {
    'Key.ctrl': 'CTRL', 'Key.alt': 'ALT',
    'Key.shift': 'SHIFT', 'Key.cmd': 'META/CMD',
    'Key.enter': 'ENTER', 'Key.space': 'SPACE',
    'Key.tab': 'TAB', 'Key.esc': 'ESC',
    'Key.backspace': 'BACKSPACE',
    'Key.delete': 'DEL', 'Key.insert': 'INSERT',
    'Key.home': 'HOME', 'Key.end': 'END',
    'Key.page_up': 'PAGE UP', 'Key.page_down': 'PAGE DOWN',
    'Key.up': '↑', 'Key.down': '↓', 'Key.left': '←', 'Key.right': '→',
    'Key.ctrl_l': 'L CTRL', 'Key.ctrl_r': 'R CTRL',
    'Key.alt_l': 'L ALT', 'Key.alt_r': 'R ALT',
    'Key.shift_l': 'L SHIFT', 'Key.shift_r': 'R SHIFT',
    'Key.cmd_l': 'L META/CMD', 'Key.cmd_r': 'R META/CMD',
    'Key.caps_lock': 'CAPS LOCK', 'Key.num_lock': 'NUM LOCK',
    'Key.print_screen': 'PRT SCR',
    'Key.num0': 'NUM 0', 'Key.num1': 'NUM 1', 'Key.num2': 'NUM 2',
    'Key.num3': 'NUM 3', 'Key.num4': 'NUM 4', 'Key.num5': 'NUM 5',
    'Key.num6': 'NUM 6', 'Key.num7': 'NUM 7', 'Key.num8': 'NUM 8',
    'Key.num9': 'NUM 9', 'Key.num_dot': 'NUM .', 'Key.num_plus': 'NUM +',
    'Key.num_min': 'NUM -', 'Key.num_eq': 'NUM =', 'Key.num_comm': 'NUM ,',
    'Key.num_ast': 'NUM *',
}
KEY_DISPLAY_MAPPINGS.update({f'Key.f{i}': f'F{i}' for i in range(1, 13)})

# Обратный маппинг: uinput код -> читаемое имя
REVERSE_KEY_MAPPINGS = {v: k.replace('Key.', '') for k, v in KEY_MAPPINGS.items()}
# Добавляем буквы и цифры
for c in 'abcdefghijklmnopqrstuvwxyz0123456789':
    try:
        REVERSE_KEY_MAPPINGS[getattr(uinput, f'KEY_{c.upper()}')] = c.upper()
    except AttributeError:
        pass

# Список цветов Launchpad с их MIDI-значениями
LAUNCHPAD_COLORS = {
    0: "Off (0)",
    3: "Red Low (3)",
    7: "Amber Low (7)",
    15: "Green Low (15)",
    5: "Red Full (5)",
    9: "Green Full (9)",
    13: "Yellow Full (13)",
    63: "White Full (63)",
    127: "Maximum Brightness (127)", # Для современных устройств
}
