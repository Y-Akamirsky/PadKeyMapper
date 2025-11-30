import sys
import time
import json
from mido import get_input_names, open_input
from pynput.keyboard import Controller, Key

# Словарь для преобразования строковых имен pynput в объекты Key
KEY_NAMES = {
    # 1. Клавиши-модификаторы и основные
    'Key.ctrl': Key.ctrl,
    'Key.alt': Key.alt,
    'Key.shift': Key.shift,
    'Key.cmd': Key.cmd,            # Super (Windows Key, Command на Mac)
    'Key.space': Key.space,
    'Key.enter': Key.enter,
    'Key.tab': Key.tab,
    'Key.esc': Key.esc,

    # 2. Функциональные клавиши
    'Key.f1': Key.f1,
    'Key.f2': Key.f2,
    'Key.f3': Key.f3,
    'Key.f4': Key.f4,
    'Key.f5': Key.f5,
    'Key.f6': Key.f6,
    'Key.f7': Key.f7,
    'Key.f8': Key.f8,
    'Key.f9': Key.f9,
    'Key.f10': Key.f10,
    'Key.f11': Key.f11,
    'Key.f12': Key.f12,

    # 3. Клавиши навигации и редактирования
    'Key.backspace': Key.backspace,
    'Key.delete': Key.delete,
    'Key.insert': Key.insert,
    'Key.home': Key.home,
    'Key.end': Key.end,
    'Key.page_up': Key.page_up,
    'Key.page_down': Key.page_down,
    'Key.up': Key.up,
    'Key.down': Key.down,
    'Key.left': Key.left,
    'Key.right': Key.right,

    # 4. Клавиши блокировки и системные
    'Key.caps_lock': Key.caps_lock,
    'Key.num_lock': Key.num_lock,
    'Key.scroll_lock': Key.scroll_lock,
    'Key.print_screen': Key.print_screen,
    'Key.pause': Key.pause,

    # 5. Мультимедиа (если поддерживается вашей клавиатурой/системой)
    'Key.media_play_pause': Key.media_play_pause,
    'Key.media_volume_up': Key.media_volume_up,
    'Key.media_volume_down': Key.media_volume_down,
    'Key.media_mute': Key.media_mute,
    'Key.media_next': Key.media_next,
    'Key.media_previous': Key.media_previous,

    # 6. Раздельные модификаторы (для специфических макросов)
    'Key.ctrl_l': Key.ctrl_l,
    'Key.ctrl_r': Key.ctrl_r,
    'Key.alt_l': Key.alt_l,
    'Key.alt_r': Key.alt_r,
    'Key.shift_l': Key.shift_l,
    'Key.shift_r': Key.shift_r,
    'Key.cmd_l': Key.cmd_l,
    'Key.cmd_r': Key.cmd_r,
}

# Инициализация контроллера клавиатуры
keyboard = Controller()

# --- 1. Загрузка Конфигурации ---
def load_config(filename="config.json"):
    """Загружает конфигурацию из JSON и формирует словари KEY_MAP и CC_MAP."""
    print(f"Загрузка конфигурации из {filename}...")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Ошибка: Файл конфигурации '{filename}' не найден.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Ошибка: Неверный формат JSON в файле '{filename}'.")
        sys.exit(1)

    # Словари для быстрого поиска
    key_map = {} # Для сообщений Note On (основная сетка)
    cc_map = {}  # Для сообщений Control Change (верхний ряд)

    for mapping in data.get('mappings', []):
        m_type = mapping.get('type')
        m_id = mapping.get('id')
        m_keys_str = mapping.get('keys', [])

        # Преобразование строковых имен клавиш в объекты pynput
        keys_to_press = []
        for key_str in m_keys_str:
            if key_str in KEY_NAMES:
                keys_to_press.append(KEY_NAMES[key_str])
            else:
                # Если это обычная буква или цифра, просто добавляем ее как строку
                keys_to_press.append(key_str)

        if m_type == 'note':
            key_map[m_id] = keys_to_press
        elif m_type == 'cc':
            cc_map[m_id] = keys_to_press

    print("✅ Конфигурация успешно загружена.")
    return key_map, cc_map


# --- 2. Функция Отправки Нажатия Клавиш ---
def send_keystroke(keys):
    """Имитирует нажатие и отпускание указанной комбинации клавиш."""

    # 1. Нажать все клавиши в списке
    for key in keys:
        keyboard.press(key)

    # 2. Отпустить все клавиши
    for key in keys:
        keyboard.release(key)

    # Конвертируем обратно для красивого вывода в консоль
    display_keys = [getattr(k, 'name', str(k)) for k in keys]
    print(f"-> Имитировано нажатие: {' + '.join(display_keys)}")


# --- 3. Главная Функция Прослушивания MIDI ---
def midi_listener(KEY_MAP, CC_MAP):
    """Находит MIDI-контроллер и начинает слушать входящие сообщения."""

    print("\n--- MIDI Hotkey Listener (LPHK-VIBE) ---")

    # ... (Оставьте код поиска порта без изменений) ...
    # Получаем список всех доступных MIDI-устройств
    input_ports = get_input_names()

    if not input_ports:
        print("❌ Не найдено ни одного активного MIDI-входа.")
        sys.exit(1)

    # Пытаемся найти Launchpad, иначе берем первый
    try:
        port_name = next(name for name in input_ports if "launchpad" in name.lower())
    except StopIteration:
        port_name = input_ports[0]

    print(f"\n✅ Выбран порт: {port_name}")

    try:
        with open_input(port_name) as port:
            print("Готов! Ожидаю нажатий... (Ctrl+C для выхода)")

            # Главный цикл прослушивания
            while True:
                msg = port.receive(block=False)

                if msg:
                    # A. Обработка Сообщений Note On (Основная сетка)
                    if msg.type == 'note_on' and msg.velocity > 0:
                        note = msg.note
                        if note in KEY_MAP:
                            send_keystroke(KEY_MAP[note])
                        else:
                            # print(f"   (Нота {note} не назначена)")
                            pass # Убираем лишний вывод


                    # B. Обработка Сообщений Control Change (Верхний ряд)
                    elif msg.type == 'control_change':
                        control = msg.control
                        value = msg.value

                        if value > 0 and control in CC_MAP:
                            send_keystroke(CC_MAP[control])
                        else:
                            # print(f"   (CC {control} не назначен)")
                            pass # Убираем лишний вывод

                time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n👋 Программа остановлена пользователем.")
    except Exception as e:
        print(f"\n❌ Произошла ошибка: {e}")


# --- 4. Запуск программы ---
if __name__ == "__main__":
    # Загружаем конфигурацию перед запуском слушателя
    key_map, cc_map = load_config()

    # Передаем загруженные словари в слушатель
    midi_listener(key_map, cc_map)
