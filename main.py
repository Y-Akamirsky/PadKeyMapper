import os
import sys
import glob
import time
import json
import threading
import re  # Добавлено для парсинга пауз
import tkinter as tk
import customtkinter as ctk

# --- 0. НАСТРОЙКА ОКРУЖЕНИЯ (DEPENDENCY BOOTLOADER) ---
def setup_paths():
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
        if base_dir not in sys.path:
            sys.path.insert(0, base_dir)
        uinput_dir = os.path.join(base_dir, 'uinput')
        if os.path.exists(uinput_dir) and uinput_dir not in sys.path:
            sys.path.insert(0, uinput_dir)
        return

    current_file_path = os.path.abspath(__file__)
    if sys.platform.startswith('linux'):
        base_dir = os.path.dirname(current_file_path)
        local_lib = os.path.join(base_dir, 'lib')
        if os.path.exists(local_lib):
            site_packages_glob = glob.glob(os.path.join(local_lib, 'python*', 'site-packages'))
            if site_packages_glob:
                site_pkg = site_packages_glob[0]
                if site_pkg not in sys.path:
                    sys.path.insert(0, site_pkg)

setup_paths()

# БЕЗОПАСНЫЙ ИМПОРТ UINPUT
UINPUT_AVAILABLE = False
UINPUT_ERROR = None

try:
    import uinput
    UINPUT_AVAILABLE = True
except ImportError as e:
    UINPUT_ERROR = f"ImportError: {e}"
except OSError as e:
    UINPUT_ERROR = f"OSError: {e}"
except Exception as e:
    UINPUT_ERROR = f"Unknown Error: {e}"

if UINPUT_AVAILABLE:
    if not hasattr(uinput, "EV_KEY"):
        # 1 — значение EV_KEY в Linux input-event-codes.h
        setattr(uinput, "EV_KEY", 1)

import localization
import constants
from mido import get_input_names, get_output_names, open_input, open_output, Message

# --- НАСТРОЙКИ ПУТЕЙ ---
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

xdg_config_home = os.environ.get('XDG_CONFIG_HOME')
if os.environ.get('SUDO_USER') and not xdg_config_home:
    user_home = os.path.expanduser(f"~{os.environ.get('SUDO_USER')}")
    base_config_path = os.path.join(user_home, ".config")
elif xdg_config_home:
    base_config_path = xdg_config_home
else:
    base_config_path = os.path.join(os.path.expanduser("~"), ".config")

CONFIG_DIR = os.path.join(base_config_path, "padkey-mapper")
PROFILES_DIR = CONFIG_DIR
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")

if not os.path.exists(CONFIG_DIR):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
    except Exception as e:
        print(f"❌ Critical Error: Could not create config dir {CONFIG_DIR}. {e}")

# --- 1. МЕНЕДЖЕР НАСТРОЕК (App Settings) ---
class SettingsManager:
    DEFAULT_SETTINGS = {
        "language": "EN",
        "theme": "Dark",
        "legacy_colors": False,
        "last_profile": "default.json",
        "last_layout": "Launchpad Mini/S/MK2/X"
    }

    @staticmethod
    def load():
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    merged = SettingsManager.DEFAULT_SETTINGS.copy()
                    merged.update(data)
                    return merged
            except Exception as e:
                print(f"⚠️ Error loading settings: {e}")
        return SettingsManager.DEFAULT_SETTINGS.copy()

    @staticmethod
    def save(settings_dict):
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=4)
        except Exception as e:
            print(f"❌ Error saving settings: {e}")

# --- 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
COLOR_TRANSLATION_TABLE = {
    0: 0, 3: 1, 5: 3, 7: 17, 9: 48, 13: 51, 15: 16, 63: 51, 127: 51
}

def load_layouts(filename="layouts.json"):
    path = os.path.join(BASE_DIR, filename)
    layouts = {}
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                layouts = json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading layouts.json: {e}")
    return layouts

def get_available_profiles():
    files = glob.glob(os.path.join(PROFILES_DIR, "*.json"))
    profiles = [os.path.basename(f) for f in files if "settings.json" not in f]
    if not profiles:
        default_path = os.path.join(PROFILES_DIR, "default.json")
        try:
            with open(default_path, 'w') as f:
                json.dump({"mappings": []}, f)
            return ["default.json"]
        except Exception as e:
            return []
    return sorted(profiles)

def load_profile_data(filename):
    path = os.path.join(PROFILES_DIR, filename)
    key_map = {}
    cc_map = {}
    all_mappings_data = []

    if not os.path.exists(path):
        return key_map, cc_map, all_mappings_data

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return key_map, cc_map, all_mappings_data

    for mapping in data.get('mappings', []):
        m_type = mapping.get('type')
        m_id = mapping.get('id')
        m_keys_str = mapping.get('keys', [])
        m_color = mapping.get('color', 0)
        m_mode = mapping.get('mode', 'One-Shot') # Default mode

        # Парсинг клавиш для исполнителя макросов
        # Теперь мы сохраняем сырые строки для пауз ({WAIT:X}), а клавиши преобразуем
        parsed_sequence = []
        for key_str in m_keys_str:
            # Проверка на паузу
            if key_str.startswith("{WAIT:") and key_str.endswith("}"):
                parsed_sequence.append(key_str) # Сохраняем как команду
            elif key_str in constants.KEY_MAPPINGS:
                parsed_sequence.append(constants.KEY_MAPPINGS[key_str])
            elif len(key_str) == 1 and (key_str.isalpha() or key_str.isdigit()):
                try:
                    attr_name = f'KEY_{key_str.upper()}'
                    if UINPUT_AVAILABLE and hasattr(uinput, attr_name):
                        parsed_sequence.append(getattr(uinput, attr_name))
                except (AttributeError, NameError):
                    pass

        entry = {
            'type': m_type, 'id': m_id, 'keys_str': m_keys_str,
            'description': mapping.get('description', '—'),
            'color': m_color,
            'mode': m_mode
        }
        all_mappings_data.append(entry)

        # Словарь для быстрого поиска в потоке
        mapping_dict = {'keys': parsed_sequence, 'color': m_color, 'mode': m_mode}
        try:
            clean_id = int(m_id)
            if m_type == 'note': key_map[clean_id] = mapping_dict
            elif m_type == 'cc': cc_map[clean_id] = mapping_dict
        except (ValueError, TypeError):
            pass

    return key_map, cc_map, all_mappings_data

def save_profile_data(mappings_data, filename):
    path = os.path.join(PROFILES_DIR, filename)
    data_to_save = {'mappings': []}
    for mapping in mappings_data:
        m_id = mapping['id']
        try: m_id = int(m_id)
        except ValueError: pass
        data_to_save['mappings'].append({
            'type': mapping['type'],
            'id': m_id,
            'keys': mapping['keys_str'],
            'description': mapping['description'],
            'color': mapping.get('color', 0),
            'mode': mapping.get('mode', 'One-Shot')
        })
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Error saving profile: {e}")
        return False

# --- 3. INPUT MANAGER & MACRO EXECUTOR ---
class InputManager:
    def __init__(self):
        self.device = None
        self.init_error = UINPUT_ERROR
        if not UINPUT_AVAILABLE or self.init_error: return

        all_keys = set()
        # 1. Keyboard keys
        for key_code in constants.KEY_MAPPINGS.values():
            all_keys.add(key_code)
        for char in 'abcdefghijklmnopqrstuvwxyz0123456789':
            attr_name = f'KEY_{char.upper()}'
            if hasattr(uinput, attr_name):
                all_keys.add(getattr(uinput, attr_name))

        # 2. Mouse Buttons & Axes
        try:
            mouse_capabilities = [
                uinput.BTN_LEFT, uinput.BTN_RIGHT, uinput.BTN_MIDDLE,
                uinput.REL_X, uinput.REL_Y, uinput.REL_WHEEL
            ]
            for cap in mouse_capabilities:
                all_keys.add(cap)
        except AttributeError:
            pass

        final_key_list = list(all_keys)
        if not final_key_list:
            self.init_error = "Key list is empty."
            return

        try:
            self.device = uinput.Device(final_key_list)
            print(f"✅ uinput device created.")
        except OSError as e:
            error_message = str(e)
            if "No such device" in error_message or "Errno 19" in error_message:
                self.init_error = localization.get_string('UINPUT_MODULE_MISSING')
            elif "Permission denied" in error_message or "Errno 13" in error_message:
                self.init_error = localization.get_string('UINPUT_PERMISSION_DENIED')
            else:
                self.init_error = f"OS Error: {e}"
        except Exception as e:
            self.init_error = str(e)

    def key_down(self, keys):
        if not self.device or not keys:
            return
        try:
            for key in keys:
                if isinstance(key, int):
                    try:
                        # Предпочитаемый формат для твоей сборки (tuple event)
                        self.device.emit((uinput.EV_KEY, key), 1)
                    except Exception:
                        # Fallback: некоторые версии ожидают (code, value)
                        self.device.emit(key, 1)
            print(f"[UINPUT] DOWN {keys}")
        except Exception as e:
            print("[UINPUT] ERROR key_down:", e)

    def key_up(self, keys):
        if not self.device or not keys:
            return
        try:
            for key in keys:
                if isinstance(key, int):
                    try:
                        self.device.emit((uinput.EV_KEY, key), 0)
                    except Exception:
                        self.device.emit(key, 0)
            print(f"[UINPUT] UP {keys}")
        except Exception as e:
            print("[UINPUT] ERROR key_up:", e)

    def send_keystroke(self, keys):
        if not self.device:
            return
        real = [k for k in keys if isinstance(k, int)]
        if not real:
            return
        self.key_down(real)
        time.sleep(0.015)
        self.key_up(real)

INPUT_MANAGER = InputManager()

class MacroExecutor:
    """
    Класс для обработки сложной логики макросов: задержки, циклы, удержания.
    """
    def __init__(self, input_manager):
        self.im = input_manager
        self.active_loops = {}   # {id: stop_event}
        self.active_toggles = {} # {id: bool_state} (True = Held down)
        self.threads = {}        # {id: thread}

    def execute(self, mapping_id, mapping_data, is_note_on):
        mode = mapping_data.get('mode', 'One-Shot')
        keys = mapping_data.get('keys', [])

        if not keys:
            return

        # --- Helper: convert items to uinput codes ---
        def _resolve_key_list(raw_keys):
            resolved = []
            for item in raw_keys:

                # 1. WAIT
                if isinstance(item, str) and item.startswith("{WAIT:"):
                    resolved.append(item)
                    continue

                # 2. New format — Key.xxx
                if isinstance(item, str) and item in constants.KEY_MAPPINGS:
                    resolved.append(constants.KEY_MAPPINGS[item])
                    continue

                # 3. Old tuple format (1, 108)
                if isinstance(item, tuple) and len(item) == 2:
                    code = item[1]
                    if isinstance(code, int):
                        resolved.append(code)
                        continue

                # 4. Already integer
                if isinstance(item, int):
                    resolved.append(item)
                    continue

                # 5. Numeric string
                if isinstance(item, str) and item.isdigit():
                    resolved.append(int(item))
                    continue

                # 6. KEY_SOMETHING
                if isinstance(item, str) and item.startswith("KEY_"):
                    if hasattr(uinput, item):
                        resolved.append(getattr(uinput, item))
                        continue

                # 7. 'a' / 'b' / '1'
                if isinstance(item, str) and len(item) == 1:
                    keyname = f"KEY_{item.upper()}"
                    if hasattr(uinput, keyname):
                        resolved.append(getattr(uinput, keyname))
                        continue

                # 8. ENTER / TAB etc
                if isinstance(item, str):
                    keyname = f"KEY_{item.upper()}"
                    if hasattr(uinput, keyname):
                        resolved.append(getattr(uinput, keyname))
                        continue

                print(f"[WARN] Unrecognized key '{item}'")

            return resolved     # ← ВОТ ТЕПЕРЬ НА СВОЁМ МЕСТЕ!

        # --- Now convert ---
        resolved_keys = _resolve_key_list(keys)
        print(f"[EXECUTE] id={mapping_id}, mode={mode}, is_on={is_note_on}, resolved={resolved_keys}")

        if not resolved_keys:
            return

        # --- MODES ---
        if mode == 'One-Shot':
            if is_note_on:
                threading.Thread(target=self._run_sequence, args=(resolved_keys,)).start()

        elif mode == 'Loop':
            if is_note_on:
                # Restart loop if exists
                if mapping_id in self.active_loops:
                    self.active_loops[mapping_id].set()

                stop_event = threading.Event()
                self.active_loops[mapping_id] = stop_event
                t = threading.Thread(target=self._run_loop, args=(resolved_keys, stop_event))
                t.start()
            else:
                if mapping_id in self.active_loops:
                    self.active_loops[mapping_id].set()
                    del self.active_loops[mapping_id]

        elif mode == 'Toggle (Hold)':
            if is_note_on:
                held = self.active_toggles.get(mapping_id, False)
                if not held:
                    self.im.key_down([k for k in resolved_keys if isinstance(k, int)])
                    self.active_toggles[mapping_id] = True
                else:
                    self.im.key_up([k for k in resolved_keys if isinstance(k, int)])
                    self.active_toggles[mapping_id] = False


    def _run_sequence(self, keys):
        """Выполняет последовательность один раз с учётом пауз.
        Ожидается, что `keys` уже содержит int (uinput-коды) и/или строковые команды {WAIT:X}.
        """
        current_chord = []

        for item in keys:
            # Команда паузы: перед паузой отправляем накопленный аккорд (если есть)
            if isinstance(item, str) and item.startswith("{WAIT:"):
                if current_chord:
                    # Отправляем текущий аккорд (список int)
                    self.im.send_keystroke(current_chord)
                    current_chord = []

                # Парсим число и ждём нужное время
                try:
                    val = float(re.search(r"[\d\.]+", item).group())
                    time.sleep(val)
                except Exception:
                    # если парсинг упал — просто пропускаем
                    pass

            # Если пришёл int (uinput-код) — добавляем в текущий аккорд
            elif isinstance(item, int):
                current_chord.append(item)

            # Защитная ветка: иногда ключи могут быть строками-числами
            elif isinstance(item, str) and item.isdigit():
                try:
                    current_chord.append(int(item))
                except:
                    pass

            # Игнорируем остальные неподдерживаемые типы/строки

        # После цикла — отсылаем остаток (если есть)
        if current_chord:
            self.im.send_keystroke(current_chord)

    def _run_loop(self, keys, stop_event):
        """Выполняет цикл пока не установлен stop_event"""
        while not stop_event.is_set():
            self._run_sequence(keys)
            # Небольшая пауза между итерациями, если в макросе нет своих пауз, чтобы не спамить CPU
            if not any(isinstance(k, str) and "WAIT" in k for k in keys):
                time.sleep(0.05)

MACRO_EXECUTOR = MacroExecutor(INPUT_MANAGER)


# --- 4. MIDI THREAD ---
class MidiListenerThread(threading.Thread):
    def __init__(self, app_instance, port_name):
        super().__init__()
        self._stop_event = threading.Event()
        self.app = app_instance
        self.port_name = port_name

    def stop(self):
        self._stop_event.set()

    def run(self):
        if INPUT_MANAGER.init_error:
            self.app.update_status_label(localization.get_string('STATUS_ERROR', error=INPUT_MANAGER.init_error), is_error=True)
            return

        try:
            self.app.update_status_label(localization.get_string('STATUS_INIT'))
            self.send_initial_lighting()

            with open_input(self.port_name) as port:
                self.app.update_status_label(localization.get_string('STATUS_LISTENING', port_name=self.port_name))

                while not self._stop_event.is_set():
                    # Обрабатываем все ожидающие сообщения (более надёжно, чем receive(block=False))
                    processed_any = False
                    for msg in port.iter_pending():
                        processed_any = True
                        # NOTE EVENTS
                        if msg.type == 'note_on' or msg.type == 'note_off':
                            raw_id = msg.note
                            # сначала ищем строковый ключ (как в config.json), затем — целочисленный запасной вариант
                            id_str = str(raw_id)
                            keys_data = self.app.key_map.get(id_str)
                            if keys_data is None:
                                keys_data = self.app.key_map.get(raw_id)

                            if keys_data:
                                is_on = (msg.type == 'note_on' and getattr(msg, 'velocity', 0) > 0)
                                # краткий debug в консоль — можно убрать после отладки
                                print(f"[MIDI] note {raw_id} -> mapping found, is_on={is_on}")
                                MACRO_EXECUTOR.execute(id_str if id_str in self.app.key_map else raw_id, keys_data, is_on)

                        # CC EVENTS
                        elif msg.type == 'control_change':
                            raw_id = msg.control
                            id_str = str(raw_id)
                            keys_data = self.app.cc_map.get(id_str)
                            if keys_data is None:
                                keys_data = self.app.cc_map.get(raw_id)

                            if keys_data:
                                is_on = (getattr(msg, 'value', 0) > 0)
                                print(f"[MIDI] cc {raw_id} -> mapping found, is_on={is_on}")
                                MACRO_EXECUTOR.execute(id_str if id_str in self.app.cc_map else raw_id, keys_data, is_on)

                    # Если ничего не было, даём небольшой отдых
                    if not processed_any:
                        time.sleep(0.005)

            self.app.update_status_label(localization.get_string('STATUS_STOPPED'))
        except Exception as e:
            self.app.update_status_label(localization.get_string('STATUS_ERROR', error=str(e)), is_error=True)

    def send_initial_lighting(self):
        if not self.app.midi_output: return
        for note_id, data in self.app.key_map.items():
            safe_color = self.app.get_safe_color(data['color'])
            try: self.app.midi_output.send(Message('note_on', note=int(note_id), velocity=safe_color))
            except: pass
        for cc_id, data in self.app.cc_map.items():
            safe_color = self.app.get_safe_color(data['color'])
            try: self.app.midi_output.send(Message('control_change', control=int(cc_id), value=safe_color))
            except: pass

# --- 5. GUI COMPONENTS ---

class VirtualPadVisualizer(ctk.CTkFrame):
    """
    Универсальный виджет для отображения Launchpad.
    ИСПРАВЛЕНИЯ: Квадратные кнопки, отсутствие растягивания текста.
    """
    def __init__(self, master, layout_config, button_callback=None, btn_size=40, **kwargs):
        super().__init__(master, **kwargs)
        self.layout_config = layout_config
        self.button_callback = button_callback
        self.btn_size = btn_size
        self.buttons = {}

        self.render()

    def render(self):
        for widget in self.winfo_children(): widget.destroy()
        self.buttons = {}

        layout_type = self.layout_config.get("type", "Mini")

        # Настройка сетки: не используем uniform, чтобы контролировать размер вручную
        # или используем frame-контейнер для центрирования

        # Основной контейнер сетки (центрируем его внутри self)
        grid_frame = ctk.CTkFrame(self, fg_color="transparent")
        grid_frame.pack(anchor="center")

        def add_btn(row, col, label, m_type, m_id, radius, is_side=False):
            default_color = MAIN_GRID_COLOR
            if is_side:
                default_color = SIDE_GRID_COLOR

            # Создаем фрейм-обертку, чтобы задать жесткий размер
            # CTkButton имеет баг/особенность, где текст может расширять кнопку.
            container = ctk.CTkFrame(grid_frame, width=self.btn_size, height=self.btn_size, fg_color="transparent")
            container.grid_propagate(False) # Запрещаем менять размер от содержимого
            container.grid(row=row, column=col, padx=1, pady=1)

            btn = ctk.CTkButton(
                container,
                text=label,
                width=self.btn_size,
                height=self.btn_size,
                corner_radius=radius,
                fg_color=default_color,
                font=("Arial", 9),
                hover_color="gray50"
            )

            if self.button_callback:
                btn.configure(command=lambda t=m_type, i=m_id: self.button_callback(i, t))
            else:
                btn.configure(state="disabled", text_color_disabled="white")

            # Размещаем кнопку внутри жесткого контейнера.
            # sticky="" (по умолчанию) центрирует её.
            btn.place(relx=0.5, rely=0.5, anchor="center", relwidth=1, relheight=1)

            self.buttons[(m_type, m_id)] = btn

        SQUARE_RADIUS = 4
        ROUND_RADIUS = SQUARE_RADIUS

        MAIN_GRID_COLOR = "gray30"
        SIDE_GRID_COLOR = "gray28"

        if layout_type == "Mini":
            cc_start = self.layout_config.get("cc_row_start", 104)
            cc_end = self.layout_config.get("cc_row_end", 111)
            side_notes = self.layout_config.get("side_notes", [])

            for idx, cc_id in enumerate(range(cc_start, cc_end + 1)):
                add_btn(0, idx, f"{cc_id}", 'cc', cc_id, ROUND_RADIUS)

            for r in range(8):
                for c in range(8):
                    note_id = r * 16 + c
                    add_btn(r+1, c, "", 'note', note_id, SQUARE_RADIUS)
                if r < len(side_notes):
                    s_id = side_notes[r]
                    add_btn(r+1, 8, f"{s_id}", 'note', s_id, ROUND_RADIUS, is_side=True)

        elif layout_type == "Pro":
             top = self.layout_config.get("top_notes", [])
             left = self.layout_config.get("left_notes", [])
             right = self.layout_config.get("right_notes", [])
             bottom = self.layout_config.get("bottom_notes", [])
             grid_start = self.layout_config.get("grid_start_note", 11)

             for c, n_id in enumerate(top):
                 add_btn(0, c+1, f"{n_id}", 'note', n_id, ROUND_RADIUS)

             for r in range(8):
                 if r < len(left):
                     add_btn(r+1, 0, f"{left[r]}", 'note', left[r], ROUND_RADIUS, is_side=True)
                 for c in range(8):
                     note_id = grid_start + (7-r) * 10 + c
                     add_btn(r+1, c+1, "", 'note', note_id, SQUARE_RADIUS)
                 if r < len(right):
                     add_btn(r+1, 9, f"{right[r]}", 'note', right[r], ROUND_RADIUS, is_side=True)

             for c, n_id in enumerate(bottom):
                 add_btn(9, c+1, f"{n_id}", 'note', n_id, ROUND_RADIUS)

        elif layout_type == "Universal":
            notes = self.layout_config.get("notes", [])
            ccs = self.layout_config.get("cc", [])
            row, col = 0, 0
            for i in ccs:
                add_btn(row, col, str(i), 'cc', i, ROUND_RADIUS, is_side=True)
                col += 1
                if col > 15: col = 0; row += 1
            row += 1
            col = 0
            for i in notes:
                add_btn(row, col, str(i), 'note', i, SQUARE_RADIUS)
                col += 1
                if col > 15: col = 0; row += 1

    def update_states(self, mappings_data, current_selection=None):
        layout_type = self.layout_config.get("type", "Mini")
        for (m_type, m_id), btn in self.buttons.items():
            base_color = "gray30"
            if m_type == 'cc' or (layout_type == "Mini" and m_id % 16 == 8): base_color = "gray20"

            # Проверяем, есть ли текст ID, который нужно показать
            show_text = ""
            if layout_type != "Mini" or m_type == 'cc' or m_id % 16 == 8:
                show_text = str(m_id)

            btn.configure(fg_color=base_color, text=show_text)

        for idx, m in enumerate(mappings_data):
            if m['id'] == 'NEW': continue
            try:
                mid = int(m['id'])
                mtype = m['type']
                if (mtype, mid) in self.buttons:
                    btn = self.buttons[(mtype, mid)]
                    btn.configure(text=str(idx + 1), fg_color="teal" if mtype=='note' else "darkorange")
            except: pass

        if current_selection:
            cs_id = current_selection.get('id')
            cs_type = current_selection.get('type')
            try: cs_id = int(cs_id)
            except: pass
            if (cs_type, cs_id) in self.buttons:
                self.buttons[(cs_type, cs_id)].configure(fg_color="red")

class KeySelectionWindow(ctk.CTkToplevel):
    def __init__(self, master, target_entry):
        super().__init__(master)
        self.title(localization.get_string('KEY_SELECT_TITLE'))
        self.geometry("300x500")
        self.target_entry = target_entry
        self.attributes("-topmost", True)
        self.transient(master)

        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text=localization.get_string('KEY_SELECT_LABEL'))
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)

        sorted_keys = sorted(constants.KEY_MAPPINGS.keys())
        for key_name in sorted_keys:
            display_name = constants.KEY_DISPLAY_MAPPINGS.get(key_name, key_name)
            btn = ctk.CTkButton(self.scroll_frame, text=display_name,
                                command=lambda k=key_name: self.insert_key(k),
                                height=25, anchor="w")
            btn.pack(fill="x", pady=2)

        ctk.CTkLabel(self.scroll_frame, text=localization.get_string('KEY_SELECT_SYMBOLS')).pack(pady=5)
        for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
            btn = ctk.CTkButton(self.scroll_frame, text=char,
                                command=lambda k=char: self.insert_key(k),
                                height=25, anchor="w", fg_color="transparent", border_width=1)
            btn.pack(fill="x", pady=2)

    def insert_key(self, key_value):
        current_text = self.target_entry.get().strip()
        key_to_insert = key_value
        if current_text and not current_text.endswith("+") and not current_text.endswith(" "):
            new_text = f"{current_text} + {key_to_insert}"
        else:
            new_text = f"{current_text}{key_to_insert}"
        self.target_entry.delete(0, 'end')
        self.target_entry.insert(0, new_text)
        self.destroy()

class EditMappingWindow(ctk.CTkToplevel):
    def __init__(self, master, mapping_data, index, layout_config):
        super().__init__(master)
        title_id = mapping_data['id'] if mapping_data['id'] != 'NEW' else localization.get_string('EDIT_NEW_TITLE')
        self.title(localization.get_string('EDIT_TITLE', id=title_id))

        if layout_config.get('type') == 'Universal':
            self.geometry("900x850")
        else:
            self.geometry("600x800")

        self.mapping_data = mapping_data
        self.index = index
        self.master_app = master
        self.layout_config = layout_config

        self.grid_columnconfigure(1, weight=1)
        self.create_widgets()
        self.grab_set()
        self.transient(master)
        self.after(100, lambda: self.attributes("-topmost", True))

    def open_key_menu(self):
        KeySelectionWindow(self, self.keys_entry)

    def insert_delay(self):
        current_text = self.keys_entry.get().strip()
        delay_tag = "{WAIT:0.1}"
        if current_text and not current_text.endswith("+") and not current_text.endswith(" "):
            new_text = f"{current_text} + {delay_tag}"
        else:
            new_text = f"{current_text}{delay_tag}"
        self.keys_entry.delete(0, 'end')
        self.keys_entry.insert(0, new_text)

    def map_midi_pad(self, midi_id, midi_type):
        self.type_var.set(midi_type)
        self.id_entry.delete(0, 'end')
        self.id_entry.insert(0, str(midi_id))
        self.visualizer.update_states(self.master_app.mappings_data,
                                      current_selection={'type': midi_type, 'id': midi_id})

    def create_widgets(self):
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=10, pady=10)
        input_frame.grid_columnconfigure(1, weight=1)

        row = 0
        ctk.CTkLabel(input_frame, text=localization.get_string('EDIT_MIDI_ID'), font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w")
        self.type_var = ctk.StringVar(value=self.mapping_data['type'])
        ctk.CTkOptionMenu(input_frame, values=["note", "cc"], variable=self.type_var, width=80).grid(row=row, column=1, sticky="w", padx=5)
        self.id_entry = ctk.CTkEntry(input_frame, placeholder_text="ID", width=80)
        curr_id = str(self.mapping_data['id']) if self.mapping_data['id'] != 'NEW' else ''
        self.id_entry.insert(0, curr_id)
        self.id_entry.grid(row=row, column=1, padx=(100, 0), sticky="w")

        # --- KEYS ROW ---
        row += 1
        ctk.CTkLabel(input_frame, text=localization.get_string('EDIT_KEYS'), font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w", pady=5)
        keys_str = " + ".join(self.mapping_data['keys_str'])
        self.keys_entry = ctk.CTkEntry(input_frame, placeholder_text="Click button ->")
        self.keys_entry.insert(0, keys_str)
        self.keys_entry.grid(row=row, column=1, sticky="ew", padx=5, pady=5)

        # Keys Buttons Frame
        keys_btn_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        keys_btn_frame.grid(row=row, column=2, sticky="e")
        ctk.CTkButton(keys_btn_frame, text="⏱️ Delay", width=60, command=self.insert_delay, fg_color="gray40").pack(side="left", padx=2)
        ctk.CTkButton(keys_btn_frame, text="⌨️", width=40, command=self.open_key_menu).pack(side="left")

        # --- MODE & DESC ---
        row += 1
        ctk.CTkLabel(input_frame, text="Mode:", font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w", pady=5)
        self.mode_var = ctk.StringVar(value=self.mapping_data.get('mode', 'One-Shot'))
        ctk.CTkOptionMenu(input_frame, values=["One-Shot", "Loop", "Toggle (Hold)"], variable=self.mode_var).grid(row=row, column=1, sticky="w", padx=5)

        row += 1
        ctk.CTkLabel(input_frame, text=localization.get_string('EDIT_DESC'), font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w", pady=5)
        self.desc_entry = ctk.CTkEntry(input_frame)
        self.desc_entry.insert(0, self.mapping_data['description'])
        self.desc_entry.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5)

        # --- COLOR ---
        row += 1
        ctk.CTkLabel(input_frame, text=localization.get_string('EDIT_COLOR'), font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, sticky="w", pady=5)
        color_sub_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        color_sub_frame.grid(row=row, column=1, columnspan=2, sticky="ew", padx=5)

        initial_color = self.mapping_data.get('color', 0)
        color_names = list(constants.LAUNCHPAD_COLORS.values())
        initial_color_name = next((v for k, v in constants.LAUNCHPAD_COLORS.items() if k == initial_color), localization.get_string('COLOR_CUSTOM'))

        self.color_var = ctk.StringVar(value=initial_color_name)
        self.color_select = ctk.CTkOptionMenu(color_sub_frame, values=color_names, variable=self.color_var, width=150, command=self._on_preset_color_select)
        self.color_select.pack(side="left")
        self.manual_color_entry = ctk.CTkEntry(color_sub_frame, width=50, placeholder_text="0-127")
        self.manual_color_entry.insert(0, str(initial_color))
        self.manual_color_entry.pack(side="left", padx=5)

        # Separator
        ctk.CTkFrame(self, height=2, fg_color="gray40").pack(fill="x", padx=10, pady=5)

        # Virtual Pad
        ctk.CTkLabel(self, text=localization.get_string('EDIT_VIRTUAL_PAD', layout=self.layout_config.get('type')), font=ctk.CTkFont(weight="bold")).pack(pady=5)

        pad_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        pad_container.pack(fill="both", expand=True, padx=25)

        self.visualizer = VirtualPadVisualizer(
            pad_container,
            self.layout_config,
            button_callback=self.map_midi_pad,
            btn_size=50 if self.layout_config.get('type') != 'Universal' else 25
        )
        self.visualizer.pack()
        self.visualizer.update_states(self.master_app.mappings_data, current_selection={'type': self.mapping_data['type'], 'id': self.mapping_data['id']})

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frame, text=localization.get_string('EDIT_SAVE'), command=self.save_and_close).pack(side="left", expand=True, padx=10)
        ctk.CTkButton(btn_frame, text=localization.get_string('EDIT_CANCEL'), command=self.destroy, fg_color="gray").pack(side="left", expand=True, padx=10)

    def _on_preset_color_select(self, choice):
        for k, v in constants.LAUNCHPAD_COLORS.items():
            if v == choice:
                self.manual_color_entry.delete(0, 'end')
                self.manual_color_entry.insert(0, str(k))
                return

    def save_and_close(self):
        try: new_id_val = int(self.id_entry.get().strip())
        except ValueError:
            self.master_app.update_status_label(localization.get_string('STATUS_ID_ERROR'), is_error=True)
            return

        new_type = self.type_var.get()
        new_desc = self.desc_entry.get().strip()
        new_mode = self.mode_var.get()
        new_keys_raw = self.keys_entry.get().strip()
        new_keys_list = [k.strip() for k in new_keys_raw.replace(' ', '').split('+') if k.strip()]

        try:
            new_color = int(self.manual_color_entry.get().strip())
            if not 0 <= new_color <= 127: raise ValueError
        except ValueError:
            self.master_app.update_status_label(localization.get_string('STATUS_COLOR_ERROR'), is_error=True)
            return

        current_id_str = str(self.mapping_data['id'])
        if current_id_str != str(new_id_val) or current_id_str == 'NEW':
            if self.master_app.is_duplicate_mapping(new_type, new_id_val, self.index):
                self.master_app.update_status_label(localization.get_string('STATUS_MAPPING_USED', type=new_type.upper(), id=new_id_val), is_error=True)
                return

        self.master_app.mappings_data[self.index].update({
            'id': new_id_val, 'type': new_type, 'keys_str': new_keys_list,
            'description': new_desc, 'color': new_color, 'mode': new_mode
        })
        self.master_app.update_mappings()
        self.destroy()

class MappingTableFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, app_instance, mappings_data, **kwargs):
        super().__init__(master, label_text=localization.get_string('MAPPING_LIST_LABEL'), **kwargs)
        self.app_master = app_instance
        self.grid_columnconfigure(3, weight=1)
        self.create_widgets(mappings_data)

    def refresh_table(self, mappings_data):
        for widget in self.winfo_children(): widget.destroy()
        self.create_widgets(mappings_data)

    def create_widgets(self, mappings_data):
        ctk.CTkButton(self, text=localization.get_string('ADD_MAPPING_BTN'), command=self.app_master.add_new_mapping).grid(row=0, column=0, columnspan=7, sticky="ew", pady=5)

        headers = ["#", "MIDI", "Keys", "Mode", "Desc", "", ""]
        for i, h in enumerate(headers):
            ctk.CTkLabel(self, text=h, font=("Arial", 12, "bold")).grid(row=1, column=i, padx=5, sticky="w")

        for i, m in enumerate(mappings_data):
            if m['id'] == 'NEW': continue
            r = i + 2
            ctk.CTkLabel(self, text=f"{i+1}").grid(row=r, column=0, padx=5)
            ctk.CTkLabel(self, text=f"{m['type'][0].upper()}:{m['id']}").grid(row=r, column=1, padx=5, sticky="w")

            display_keys = []
            for k in m['keys_str']:
                if "WAIT" in k: display_keys.append("🕒")
                else: display_keys.append(constants.KEY_DISPLAY_MAPPINGS.get(k, k))

            key_text = " + ".join(display_keys)
            if len(key_text) > 20: key_text = key_text[:17] + "..."
            ctk.CTkLabel(self, text=key_text).grid(row=r, column=2, padx=5, sticky="w")

            # Mode Label
            mode_short = m.get('mode', 'One-Shot')
            if mode_short == "Toggle (Hold)": mode_short = "Toggle"
            ctk.CTkLabel(self, text=mode_short, text_color="gray70", font=("Arial", 10)).grid(row=r, column=3, padx=5, sticky="w")

            desc = m['description']
            if len(desc) > 20: desc = desc[:17] + "..."
            ctk.CTkLabel(self, text=desc).grid(row=r, column=4, padx=5, sticky="w")

            ctk.CTkButton(self, text="✎", width=30, command=lambda x=i: self.app_master.open_edit_window(x)).grid(row=r, column=5, padx=2)
            ctk.CTkButton(self, text="🗑️", width=30, fg_color="firebrick", command=lambda x=i: self.app_master.delete_mapping(x)).grid(row=r, column=6, padx=2)

# --- 6. MAIN APP ---

class App(ctk.CTk):
    def __init__(self, port_name, output_port_name):
        super().__init__()

        self.settings = SettingsManager.load()
        ctk.set_appearance_mode(self.settings.get("theme", "Dark"))
        localization.set_language(self.settings.get("language", "EN"))

        self.lang_options = localization.get_available_languages()
        self.language_var = ctk.StringVar(value=localization.CURRENT_LANG)
        self.language_var.trace_add("write", self.change_language)

        self.layouts = load_layouts()
        self.current_layout_name = self.settings.get("last_layout", next(iter(self.layouts.keys()), "Universal (All MIDI IDs)"))
        if self.current_layout_name not in self.layouts:
             self.current_layout_name = next(iter(self.layouts.keys()), "Universal (All MIDI IDs)")

        self.current_profile_name = self.settings.get("last_profile", "default.json")
        self.profiles_list = get_available_profiles()
        if self.current_profile_name not in self.profiles_list and self.profiles_list:
             self.current_profile_name = self.profiles_list[0]
        elif not self.profiles_list:
             self.current_profile_name = "default.json"

        self.key_map, self.cc_map, self.mappings_data = load_profile_data(self.current_profile_name)

        self.port_name = port_name
        self.output_port_name = output_port_name
        self.listener_thread = None
        self.midi_output = self.open_midi_output()

        self.title(localization.get_string('APP_TITLE'))
        self.geometry("1100x700")

        self.legacy_mode_var = ctk.BooleanVar(value=self.settings.get("legacy_colors", False))

        # --- GRID CONFIGURATION FOR MAIN WINDOW FILL ---
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=1) # Content (Must expand)
        self.grid_columnconfigure(0, weight=1)

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        if INPUT_MANAGER.init_error:
            self.after(100, lambda: self.update_status_label(localization.get_string('STATUS_ERROR', error=INPUT_MANAGER.init_error), is_error=True))

    def save_app_settings(self):
        self.settings.update({
            "language": self.language_var.get(),
            "theme": ctk.get_appearance_mode(),
            "legacy_colors": self.legacy_mode_var.get(),
            "last_profile": self.current_profile_name,
            "last_layout": self.current_layout_name
        })
        SettingsManager.save(self.settings)

    def get_safe_color(self, color_value):
        if self.legacy_mode_var.get():
            return COLOR_TRANSLATION_TABLE.get(color_value, color_value)
        return color_value

    def refresh_lights(self):
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.send_initial_lighting()
        self.save_app_settings()

    def create_widgets(self):
        for widget in self.winfo_children(): widget.destroy()

        # --- HEADER (Top) ---
        header_frame = ctk.CTkFrame(self, height=50, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=10)

        ctk.CTkLabel(header_frame, text=localization.get_string('MIDI_MAPPER'), font=("Arial", 20, "bold")).pack(side="left")

        settings_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        settings_frame.pack(side="right")

        ctk.CTkLabel(settings_frame, text=localization.get_string('PROFILE_LABEL')).pack(side="left", padx=5)
        self.profile_var = ctk.StringVar(value=self.current_profile_name)
        self.profiles_list = get_available_profiles()
        profile_options = self.profiles_list + ["---", localization.get_string('PROFILE_NEW')]
        ctk.CTkOptionMenu(settings_frame, values=profile_options, variable=self.profile_var, command=self.change_profile, width=150).pack(side="left")

        ctk.CTkLabel(settings_frame, text=localization.get_string('LAYOUT_LABEL')).pack(side="left", padx=(15, 5))
        self.layout_var = ctk.StringVar(value=self.current_layout_name)
        ctk.CTkOptionMenu(settings_frame, values=list(self.layouts.keys()), variable=self.layout_var, command=self.change_layout, width=150).pack(side="left")

        # --- MAIN CONTENT AREA (2 Columns) ---
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        # FIX: Ensure content frame expands correctly
        content_frame.grid_columnconfigure(0, weight=0) # Left (Pad) - fixed logic
        content_frame.grid_columnconfigure(1, weight=1) # Right (Table) - expands
        content_frame.grid_rowconfigure(0, weight=1)    # Vertical expand

        # LEFT COLUMN: Virtual Pad Visualizer
        # We assume 450px is enough for the pad visualizer
        left_frame = ctk.CTkFrame(content_frame, width=450)
        left_frame.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
        left_frame.grid_propagate(False) # Force width
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left_frame, text="Active Mapping View", font=("Arial", 14, "bold")).grid(row=0, column=0, pady=10)

        # Container for visualizer to center it
        pad_container = ctk.CTkFrame(left_frame, fg_color="transparent")
        pad_container.grid(row=1, column=0, sticky="nsew")
        pad_container.grid_rowconfigure(0, weight=1)
        pad_container.grid_columnconfigure(0, weight=1)

        layout_config = self.layouts.get(self.current_layout_name, {})

        self.main_visualizer = VirtualPadVisualizer(
            pad_container,
            layout_config,
            btn_size=35 if layout_config.get('type') != 'Universal' else 20
        )
        # Visualizer centers itself via pack(anchor=center) inside render
        self.main_visualizer.grid(row=0, column=0)
        self.main_visualizer.update_states(self.mappings_data)

        # RIGHT COLUMN: Mapping Table & Controls
        right_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew")

        # FIX: Right frame expansion
        right_frame.grid_rowconfigure(1, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # Status Bar
        self.status_label = ctk.CTkLabel(right_frame, text=localization.get_string('STATUS_READY'), fg_color="gray20", corner_radius=5, anchor="w", padx=10)
        self.status_label.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # Table
        self.mapping_table = MappingTableFrame(right_frame, self, self.mappings_data)
        self.mapping_table.grid(row=1, column=0, sticky="nsew")

        # Bottom Controls
        ctrl_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        ctrl_frame.grid(row=2, column=0, sticky="ew", pady=10)

        start_text = localization.get_string('START_BTN')
        fg_color = "green"
        if self.listener_thread and self.listener_thread.is_alive():
            start_text = localization.get_string('STOP_BTN')
            fg_color = "red"
        state = "normal" if not INPUT_MANAGER.init_error else "disabled"

        self.toggle_btn = ctk.CTkButton(ctrl_frame, text=start_text, command=self.toggle_listener, fg_color=fg_color, state=state, height=40)
        self.toggle_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        misc_frame = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        misc_frame.pack(side="right")

        self.legacy_switch = ctk.CTkSwitch(misc_frame, text=localization.get_string('LEGACY_COLORS_LABEL'), variable=self.legacy_mode_var, command=self.refresh_lights)
        self.legacy_switch.pack(side="left", padx=10)

        ctk.CTkButton(misc_frame, text=localization.get_string('THEME_BTN'), width=60, command=self.toggle_theme).pack(side="left", padx=5)

        ctk.CTkOptionMenu(misc_frame, values=self.lang_options, variable=self.language_var, width=70).pack(side="left")


    def change_language(self, *args):
        new_lang = self.language_var.get()
        if localization.set_language(new_lang):
            self.save_app_settings()
            self.create_widgets()

    def change_layout(self, choice):
        self.current_layout_name = choice
        self.save_app_settings()
        self.create_widgets()

    def create_new_profile(self):
        dialog = ctk.CTkInputDialog(text=localization.get_string('PROFILE_NEW_PROMPT'), title=localization.get_string('PROFILE_NEW'))
        new_name = dialog.get_input()
        if new_name:
            filename = f"{new_name.strip().replace(' ', '_').replace('.json', '')}.json"
            if filename in self.profiles_list:
                self.update_status_label(localization.get_string('STATUS_PROFILE_EXISTS'), is_error=True)
                return
            new_path = os.path.join(PROFILES_DIR, filename)
            try:
                with open(new_path, 'w', encoding='utf-8') as f:
                    json.dump({"mappings": []}, f, indent=4)
                self.current_profile_name = filename
                self.profiles_list = get_available_profiles()
                self.change_profile(filename, is_new=True)
            except Exception as e:
                self.update_status_label(localization.get_string('STATUS_ERROR', error=f"New profile save failed: {e}"), is_error=True)

    def change_profile(self, choice, is_new=False):
        if choice == localization.get_string('PROFILE_NEW'):
            self.create_new_profile()
            return
        if choice == "---" or choice == self.current_profile_name:
            self.profile_var.set(self.current_profile_name)
            return

        self.current_profile_name = choice
        self.save_app_settings()
        self.key_map, self.cc_map, self.mappings_data = load_profile_data(self.current_profile_name)

        self.mapping_table.refresh_table(self.mappings_data)
        self.main_visualizer.update_states(self.mappings_data)
        self.profile_var.set(self.current_profile_name)

        status_msg = f"Profile loaded: {choice}" if not is_new else f"Profile created: {choice}"
        self.update_status_label(status_msg)
        if self.listener_thread and self.listener_thread.is_alive():
             self.refresh_lights()

    def open_midi_output(self):
        try: return open_output(self.output_port_name) if self.output_port_name else None
        except: return None

    def add_new_mapping(self):
        self.mappings_data.append({
            'type': 'note', 'id': 'NEW', 'keys_str': [],
            'description': localization.get_string('MAPPING_NEW_DESC'), 'color': 3, 'mode': 'One-Shot'
        })
        self.open_edit_window(len(self.mappings_data) - 1)

    def open_edit_window(self, index):
        current_layout = self.layouts.get(self.current_layout_name, {})
        EditMappingWindow(self, self.mappings_data[index], index, current_layout)

    def delete_mapping(self, index):
        del self.mappings_data[index]
        self.update_mappings()

    def update_mappings(self):
        self.mappings_data = [m for m in self.mappings_data if m['id'] != 'NEW']
        save_profile_data(self.mappings_data, self.current_profile_name)
        self.mapping_table.refresh_table(self.mappings_data)
        self.main_visualizer.update_states(self.mappings_data)

        self.key_map = {}
        self.cc_map = {}
        # Перезагружаем через load_profile logic чтобы распарсить паузы корректно
        # Можно оптимизировать, но так надежнее для единообразия
        temp_km, temp_ccm, _ = load_profile_data(self.current_profile_name)
        self.key_map = temp_km
        self.cc_map = temp_ccm

        if self.listener_thread and self.listener_thread.is_alive():
             self.update_status_label(localization.get_string('STATUS_UPDATED'))
             self.refresh_lights()

    def is_duplicate_mapping(self, m_type, m_id, current_index):
        for i, m in enumerate(self.mappings_data):
            if i == current_index: continue
            if m['type'] == m_type and str(m['id']) == str(m_id): return True
        return False

    def toggle_listener(self):
        if INPUT_MANAGER.init_error:
             self.update_status_label(f"❌ Cannot Start: {INPUT_MANAGER.init_error}", is_error=True)
             return

        if not self.listener_thread or not self.listener_thread.is_alive():
            self.listener_thread = MidiListenerThread(self, self.port_name)
            self.listener_thread.start()
            self.toggle_btn.configure(text=localization.get_string('STOP_BTN'), fg_color="red")
        else:
            self.listener_thread.stop()
            self.clear_launchpad()
            self.toggle_btn.configure(text=localization.get_string('START_BTN'), fg_color="green")

    def clear_launchpad(self):
        if self.midi_output:
            try:
                for m in self.mappings_data:
                    try:
                        mid_id = int(m['id'])
                        if m['type'] == 'note': self.midi_output.send(Message('note_on', note=mid_id, velocity=0))
                        elif m['type'] == 'cc': self.midi_output.send(Message('control_change', control=mid_id, value=0))
                    except (ValueError, TypeError): pass
            except Exception as e: print(f"Clear Error: {e}")

    def update_status_label(self, text, is_error=False):
        color = "firebrick" if is_error else "gray20"
        self.status_label.configure(text=text, fg_color=color)

    def toggle_theme(self):
        curr = ctk.get_appearance_mode()
        new_theme = "Light" if curr=="Dark" else "Dark"
        ctk.set_appearance_mode(new_theme)
        self.save_app_settings()
        self.create_widgets()

    def on_closing(self):
        self.save_app_settings()
        self.clear_launchpad()
        if self.listener_thread: self.listener_thread.stop()
        if self.midi_output: self.midi_output.close()
        self.destroy()

if __name__ == "__main__":
    ins = get_input_names()
    outs = get_output_names()
    in_port = next((n for n in ins if "launchpad" in n.lower()), None)
    out_port = next((n for n in outs if "launchpad" in n.lower()), None)
    if not in_port and ins: in_port = ins[0]
    if not out_port and outs: out_port = outs[0]

    app = App(in_port, out_port)
    app.mainloop()
