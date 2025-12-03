import os
import sys
import time
import json
import threading

if sys.platform.startswith('linux') and '/opt/pad-key-mapper' in os.path.abspath(__file__):
    # Определяем относительный путь до site-packages,
    # предполагая, что они лежат в /opt/pad-key-mapper/lib/pythonX.Y/site-packages

    # Получаем версию Python (например, "python3.11")
    py_version = f"python{sys.version_info.major}.{sys.version_info.minor}"

    # Формируем путь к локальной site-packages
    local_site_packages = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'lib',
        py_version,
        'site-packages'
    )

    # Добавляем этот путь в sys.path для поиска модулей
    if os.path.exists(local_site_packages):
        sys.path.append(local_site_packages)
        # print(f"DEBUG: Added custom path: {local_site_packages}") # Убрать для продакшена

# -----------------------------------------------------------------

import tkinter as tk
import uinput
import localization
import constants
from mido import get_input_names, get_output_names, open_input, open_output, Message
import customtkinter as ctk



if getattr(sys, 'frozen', False):
    # Если запущено как скомпилированный EXE/AppImage
    BASE_DIR = sys._MEIPASS
else:
    # Если запущено как скрипт
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Определение директории для пользовательского конфига
# Используем $XDG_CONFIG_HOME или ~/.config как дефолт
# Сначала пытаемся получить $XDG_CONFIG_HOME, иначе используем ~/.config
xdg_config_home = os.environ.get('XDG_CONFIG_HOME')

# Если запущены через sudo, используем $SUDO_USER для получения домашней папки
if os.environ.get('SUDO_USER') and not xdg_config_home:
    user_home = os.path.expanduser(f"~{os.environ.get('SUDO_USER')}")
    base_config_path = os.path.join(user_home, ".config")
elif xdg_config_home:
    base_config_path = xdg_config_home
else:
    # Стандартный путь: ~/.config для текущего пользователя
    base_config_path = os.path.join(os.path.expanduser("~"), ".config")

# Финальный путь: ~/.config/padkey-mapper
CONFIG_DIR = os.path.join(base_config_path, "padkey-mapper")

# Создаем папку, если ее нет
if not os.path.exists(CONFIG_DIR):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
    except Exception as e:
        # Это должно сработать, если у пользователя есть права на запись в свою папку
        print(f"❌ Критическая ошибка: Не удалось создать папку конфига {CONFIG_DIR}. Права? {e}")


# --- 1. ЛОГИКА КОНВЕРТАЦИИ ЦВЕТОВ ---

# Маппинг: Современный цвет (Velocity) -> Старый битовый цвет (Green[5-4] Clear[3] Red[1-0])
# Основано на значениях из constants.LAUNCHPAD_COLORS
COLOR_TRANSLATION_TABLE = {
    0: 0,    # Off
    3: 1,    # Red Low (Legacy: 1)
    5: 3,    # Red Full (Legacy: 3)
    7: 17,   # Amber Low (Legacy: Green Low 16 + Red Low 1 = 17)
    9: 48,   # Green Full (Legacy: 48 [110000])
    13: 51,  # Yellow Full (Legacy: Green Full 48 + Red Full 3 = 51)
    15: 16,  # Green Low (Legacy: 16 [010000])
    63: 51,  # White -> Legacy Yellow Full (Hardware limit)
    127: 51  # Max -> Legacy Yellow Full
}

# --- 2. УПРАВЛЕНИЕ КОНФИГУРАЦИЕЙ И ВВОДОМ ---

def load_layouts(filename="layouts.json"):
    path = os.path.join(BASE_DIR, filename)
    default_layout = {
        "type": "Mini",
        "cc_row_start": 104, "cc_row_end": 111,
        "side_notes": [8, 24, 40, 56, 72, 88, 104, 120],
        "grid_start_note": 0,
    }
    predefined_layouts = { "Launchpad Mini/MK2/X (Fallback)": default_layout }
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        predefined_layouts.update(data)
    except Exception as e:
        print(f"⚠️ Ошибка загрузки layouts.json: {e}")
    return predefined_layouts

def load_config(filename="config.json"):
    # ИСПРАВЛЕНО: Теперь path используется для открытия файла
    path = os.path.join(CONFIG_DIR, filename)
    key_map = {}
    cc_map = {}
    all_mappings_data = []

    try:
        # Открываем по полному пути
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return key_map, cc_map, all_mappings_data

    for mapping in data.get('mappings', []):
        m_type = mapping.get('type')
        m_id = mapping.get('id')
        m_keys_str = mapping.get('keys', [])
        m_color = mapping.get('color', 0)

        keys_to_press = []
        for key_str in m_keys_str:
            if key_str in constants.KEY_MAPPINGS:
                keys_to_press.append(constants.KEY_MAPPINGS[key_str])
            elif len(key_str) == 1 and (key_str.isalpha() or key_str.isdigit()):
                try:
                    keys_to_press.append(getattr(uinput, f'KEY_{key_str.upper()}'))
                except AttributeError:
                    pass

        entry = {
            'type': m_type, 'id': m_id, 'keys_str': m_keys_str,
            'description': mapping.get('description', '—'), 'color': m_color
        }
        all_mappings_data.append(entry)

        mapping_dict = {'keys': keys_to_press, 'color': m_color}
        try:
            clean_id = int(m_id)
            if m_type == 'note': key_map[clean_id] = mapping_dict
            elif m_type == 'cc': cc_map[clean_id] = mapping_dict
        except (ValueError, TypeError):
            pass

    return key_map, cc_map, all_mappings_data

def save_config(mappings_data, filename="config.json"):
    # ИСПРАВЛЕНО: Теперь path используется для открытия файла
    path = os.path.join(CONFIG_DIR, filename)
    data_to_save = {'mappings': []}
    for mapping in mappings_data:
        m_id = mapping['id']
        try: m_id = int(m_id)
        except ValueError: pass
        data_to_save['mappings'].append({
            'type': mapping['type'], 'id': m_id, 'keys': mapping['keys_str'],
            'description': mapping['description'], 'color': mapping.get('color', 0)
        })
    try:
        # Открываем по полному пути
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения: {e}")
        return False

class InputManager:
    def __init__(self):
        self.device = None
        all_keys = list(constants.KEY_MAPPINGS.values()) + [getattr(uinput, f'KEY_{c.upper()}') for c in 'abcdefghijklmnopqrstuvwxyz0123456789']
        try: self.device = uinput.Device(all_keys)
        except Exception: self.device = None

    def key_down(self, keys):
        if not self.device or not keys: return
        for key in keys: self.device.emit(key, 1, syn=False)
        self.device.syn()

    def key_up(self, keys):
        if not self.device or not keys: return
        for key in keys: self.device.emit(key, 0, syn=False)
        self.device.syn()

    def send_keystroke(self, keys):
        if not self.device or not keys: return
        self.key_down(keys)
        time.sleep(0.01)
        self.key_up(keys)
        display_keys = [constants.REVERSE_KEY_MAPPINGS.get(key, 'UNKNOWN') for key in keys]
        print(f"-> Имитировано: {' + '.join(display_keys)}")

INPUT_MANAGER = InputManager()
key_down = INPUT_MANAGER.key_down
key_up = INPUT_MANAGER.key_up
send_keystroke = INPUT_MANAGER.send_keystroke

# --- 3. MIDI THREAD ---
class MidiListenerThread(threading.Thread):
    def __init__(self, app_instance, port_name):
        super().__init__()
        self._stop_event = threading.Event()
        self.app = app_instance
        self.port_name = port_name

    def stop(self):
        self._stop_event.set()

    def run(self):
        try:
            self.app.update_status_label(localization.get_string('STATUS_INIT'))
            self.send_initial_lighting()

            with open_input(self.port_name) as port:
                self.app.update_status_label(localization.get_string('STATUS_LISTENING', port_name=self.port_name))

                while not self._stop_event.is_set():
                    msg = port.receive(block=False)
                    if msg:
                        if msg.type == 'note_on' or msg.type == 'note_off':
                            id_val = msg.note
                            keys_data = self.app.key_map.get(id_val)
                            if keys_data:
                                if msg.type == 'note_on' and msg.velocity > 0:
                                    key_down(keys_data['keys'])
                                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                                    key_up(keys_data['keys'])

                        elif msg.type == 'control_change' and msg.value > 0:
                            id_val = msg.control
                            if id_val in self.app.cc_map:
                                send_keystroke(self.app.cc_map[id_val]['keys'])
                    else:
                        time.sleep(0.005)

            self.app.update_status_label(localization.get_string('STATUS_STOPPED'))
        except Exception as e:
            self.app.update_status_label(localization.get_string('STATUS_ERROR', error=e))

    def send_initial_lighting(self):
        if not self.app.midi_output: return

        # NOTE MAPPINGS
        for note_id, data in self.app.key_map.items():
            safe_color = self.app.get_safe_color(data['color'])
            try: self.app.midi_output.send(Message('note_on', note=int(note_id), velocity=safe_color))
            except: pass

        # CC MAPPINGS
        for cc_id, data in self.app.cc_map.items():
            safe_color = self.app.get_safe_color(data['color'])
            try: self.app.midi_output.send(Message('control_change', control=int(cc_id), value=safe_color))
            except: pass

# --- 4. GUI: Key Selection & Edit Window ---

class KeySelectionWindow(ctk.CTkToplevel):
    def __init__(self, master, target_entry):
        super().__init__(master)
        self.title(localization.get_string('KEY_SELECT_TITLE'))
        self.geometry("300x500")
        self.target_entry = target_entry
        self.attributes("-topmost", True)

        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text=localization.get_string('KEY_SELECT_LABEL'))
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.scroll_frame.bind_all("<Button-4>", self._on_mouse_wheel)
        self.scroll_frame.bind_all("<Button-5>", self._on_mouse_wheel)
        self.scroll_frame.bind_all("<MouseWheel>", self._on_mouse_wheel)

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

    def _on_mouse_wheel(self, event):
        if hasattr(self.scroll_frame, '_parent_canvas'):
            canvas = self.scroll_frame._parent_canvas
            if event.num == 4 or event.delta > 0: canvas.yview_scroll(-1, "units")
            elif event.num == 5 or event.delta < 0: canvas.yview_scroll(1, "units")

    def insert_key(self, key_value):
        current_text = self.target_entry.get().strip()
        key_to_insert = key_value if key_value in constants.KEY_MAPPINGS else key_value
        if current_text and not (current_text.endswith("+") or current_text.endswith(" ")):
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
        self.minsize(600, 780)

        self.mapping_data = mapping_data
        self.index = index
        self.master_app = master
        self.layout_config = layout_config

        # Список кнопок для обновления меток (btn_object, id_text)
        self.virtual_buttons = []

        self.grid_columnconfigure(1, weight=1)
        self.create_widgets()
        self.grab_set()
        self.after(100, lambda: self.attributes("-topmost", True))

    def open_key_menu(self):
        KeySelectionWindow(self, self.keys_entry)

    def map_midi_pad(self, midi_id, midi_type):
        self.type_var.set(midi_type)
        self.id_entry.delete(0, 'end')
        self.id_entry.insert(0, str(midi_id))

    def toggle_labels(self):
        """Переключает видимость текста (ID) на кнопках"""
        show = self.labels_var.get()
        for btn, label_text in self.virtual_buttons:
            btn.configure(text=label_text if show else "")

    def create_widgets(self):
        row = 0
        ctk.CTkLabel(self, text=localization.get_string('EDIT_MIDI_ID'), font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, padx=10, pady=10, sticky="w")

        self.type_var = ctk.StringVar(value=self.mapping_data['type'])
        type_options = ["note"]
        if self.layout_config.get("type", "Mini") == "Mini": type_options.append("cc")
        ctk.CTkOptionMenu(self, values=type_options, variable=self.type_var, width=80).grid(row=row, column=1, padx=10, sticky="w")

        self.id_entry = ctk.CTkEntry(self, placeholder_text="ID", width=80)
        curr_id = str(self.mapping_data['id']) if self.mapping_data['id'] != 'NEW' else ''
        self.id_entry.insert(0, curr_id)
        self.id_entry.grid(row=row, column=1, padx=(100, 0), sticky="w")

        row += 1
        ctk.CTkLabel(self, text=localization.get_string('EDIT_KEYS'), font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, padx=10, pady=10, sticky="w")
        keys_str = " + ".join(self.mapping_data['keys_str'])
        self.keys_entry = ctk.CTkEntry(self, placeholder_text="Click button ->")
        self.keys_entry.insert(0, keys_str)
        self.keys_entry.grid(row=row, column=1, padx=(10, 50), pady=10, sticky="ew")
        ctk.CTkButton(self, text="⌨️", width=40, command=self.open_key_menu).grid(row=row, column=1, padx=(0, 10), sticky="e")

        row += 1
        ctk.CTkLabel(self, text=localization.get_string('EDIT_DESC'), font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, padx=10, pady=10, sticky="w")
        self.desc_entry = ctk.CTkEntry(self)
        self.desc_entry.insert(0, self.mapping_data['description'])
        self.desc_entry.grid(row=row, column=1, padx=10, sticky="ew")

        row += 1
        ctk.CTkLabel(self, text=localization.get_string('EDIT_COLOR'), font=ctk.CTkFont(weight="bold")).grid(row=row, column=0, padx=10, pady=10, sticky="w")
        initial_color = self.mapping_data.get('color', 0)
        initial_color_name = next((v for k, v in constants.LAUNCHPAD_COLORS.items() if k == initial_color), f"Custom ({initial_color})")
        self.color_var = ctk.StringVar(value=initial_color_name)
        self.color_select = ctk.CTkOptionMenu(self, values=list(constants.LAUNCHPAD_COLORS.values()), variable=self.color_var)
        self.color_select.grid(row=row, column=1, padx=10, sticky="ew")

        row += 1
        # Хедер для виртуального пада с переключателем ID
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=row, column=0, columnspan=2, pady=(20, 0), sticky="ew", padx=10)
        ctk.CTkLabel(header_frame, text=localization.get_string('EDIT_VIRTUAL_PAD'), font=ctk.CTkFont(weight="bold")).pack(side="left")

        # Переключатель показа ID
        self.labels_var = ctk.BooleanVar(value=False)
        self.labels_switch = ctk.CTkSwitch(header_frame, text=localization.get_string('EDIT_SHOW_LABELS', default="Show IDs"),
                                           variable=self.labels_var, command=self.toggle_labels, width=50)
        self.labels_switch.pack(side="right")

        self.midi_frame = ctk.CTkFrame(self)
        self.midi_frame.grid(row=row+1, column=0, columnspan=2, padx=10, pady=10)

        self.draw_virtual_grid()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row+2, column=0, columnspan=2, pady=10)
        ctk.CTkButton(btn_frame, text=localization.get_string('EDIT_SAVE'), command=self.save_and_close).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text=localization.get_string('EDIT_CANCEL'), command=self.destroy, fg_color="gray").pack(side="left", padx=5)

    def draw_virtual_grid(self):
        layout_type = self.layout_config.get("type", "Mini")
        ROUND_RADIUS = 20
        SQUARE_RADIUS = 5

        def create_pad_btn(row, col, label, m_type, m_id, radius, is_side=False):
            is_active = (self.mapping_data['type'] == m_type and str(self.mapping_data['id']) == str(m_id))
            if is_active: color = "darkorange" if m_type == 'cc' else ("purple" if is_side else "teal")
            else: color = "gray60" if (m_type == 'cc' or is_side) else "gray40"

            # Текст изначально пустой, если не включен свитч (но мы его обновим в конце метода)
            btn = ctk.CTkButton(self.midi_frame, text="", width=40, height=40, corner_radius=radius,
                                fg_color=color,
                                command=lambda id=m_id, t=m_type: self.map_midi_pad(id, t))
            btn.grid(row=row, column=col, padx=2 if not is_side else 5, pady=2)
            self.virtual_buttons.append((btn, label))

        if layout_type == "Mini":
            cc_start = self.layout_config.get("cc_row_start", 104)
            cc_end = self.layout_config.get("cc_row_end", 111)
            side_notes = self.layout_config.get("side_notes", [])

            for idx, cc_id in enumerate(range(cc_start, cc_end + 1)):
                create_pad_btn(0, idx, f"CC{cc_id}", 'cc', cc_id, ROUND_RADIUS)
            for r in range(8):
                row_offset = r * 16
                for c in range(8):
                    note_id = row_offset + c
                    create_pad_btn(r+1, c, f"{note_id}", 'note', note_id, SQUARE_RADIUS)
                if r < len(side_notes):
                    s_id = side_notes[r]
                    create_pad_btn(r+1, 8, f"S{s_id}", 'note', s_id, ROUND_RADIUS, is_side=True)

        elif layout_type == "Pro":
            top_notes = self.layout_config.get("top_notes", [])
            left_notes = self.layout_config.get("left_notes", [])
            right_notes = self.layout_config.get("right_notes", [])
            bottom_notes = self.layout_config.get("bottom_notes", [])
            grid_start = self.layout_config.get("grid_start_note", 11)

            for c, n_id in enumerate(top_notes):
                create_pad_btn(0, c+1, f"T{n_id}", 'note', n_id, ROUND_RADIUS)
            for r in range(8):
                if r < len(left_notes):
                    create_pad_btn(r+1, 0, f"L{left_notes[r]}", 'note', left_notes[r], ROUND_RADIUS, is_side=True)
                for c in range(8):
                    note_id = grid_start + (7-r) * 10 + c
                    create_pad_btn(r+1, c+1, f"{note_id}", 'note', note_id, SQUARE_RADIUS)
                if r < len(right_notes):
                    create_pad_btn(r+1, 9, f"R{right_notes[r]}", 'note', right_notes[r], ROUND_RADIUS, is_side=True)
            for c, n_id in enumerate(bottom_notes):
                create_pad_btn(9, c+1, f"B{n_id}", 'note', n_id, ROUND_RADIUS)

        self.toggle_labels()

    def save_and_close(self):
        try: new_id_val = int(self.id_entry.get().strip())
        except ValueError:
            self.master_app.update_status_label(localization.get_string('STATUS_ID_ERROR'))
            return

        new_type = self.type_var.get()
        new_desc = self.desc_entry.get().strip()
        new_keys_raw = self.keys_entry.get().strip()
        new_keys_list = [k.strip() for k in new_keys_raw.replace(' ', '').split('+') if k.strip()]

        col_str = self.color_select.get()
        try: new_color = int(col_str[col_str.find('(')+1 : col_str.find(')')])
        except: new_color = 0

        current_id_str = str(self.mapping_data['id'])
        if current_id_str != str(new_id_val) or current_id_str == 'NEW':
            if self.master_app.is_duplicate_mapping(new_type, new_id_val, self.index):
                self.master_app.update_status_label(localization.get_string('STATUS_MAPPING_USED', type=new_type.upper(), id=new_id_val))
                return

        self.master_app.mappings_data[self.index].update({
            'id': new_id_val, 'type': new_type, 'keys_str': new_keys_list,
            'description': new_desc, 'color': new_color
        })
        self.master_app.update_mappings()
        self.destroy()

class MappingTableFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, mappings_data, **kwargs):
        super().__init__(master, label_text=localization.get_string('MAPPING_LIST_LABEL'), **kwargs)
        self.app_master = master
        self.grid_columnconfigure(2, weight=1)
        self.create_widgets(mappings_data)
        self.bind_all("<Button-4>", self._on_mouse_wheel)
        self.bind_all("<Button-5>", self._on_mouse_wheel)
        self.bind_all("<MouseWheel>", self._on_mouse_wheel)

    def _on_mouse_wheel(self, event):
        if hasattr(self, '_parent_canvas'):
            if event.num == 4 or event.delta > 0: self._parent_canvas.yview_scroll(-1, "units")
            elif event.num == 5 or event.delta < 0: self._parent_canvas.yview_scroll(1, "units")

    def refresh_table(self, mappings_data):
        for widget in self.winfo_children(): widget.destroy()
        self.create_widgets(mappings_data)

    def create_widgets(self, mappings_data):
        ctk.CTkButton(self, text=localization.get_string('ADD_MAPPING_BTN'), command=self.app_master.add_new_mapping).grid(row=0, column=0, columnspan=5, sticky="ew", pady=5)
        for i, m in enumerate(mappings_data):
            if m['id'] == 'NEW': continue
            r = i + 1
            ctk.CTkLabel(self, text=f"{m['type'].upper()}: {m['id']}").grid(row=r, column=0, padx=5, sticky="w")
            ctk.CTkLabel(self, text=" + ".join([constants.KEY_DISPLAY_MAPPINGS.get(k, k) for k in m['keys_str']])).grid(row=r, column=1, padx=5, sticky="w")
            ctk.CTkLabel(self, text=m['description']).grid(row=r, column=2, padx=5, sticky="w")
            ctk.CTkButton(self, text="✎", width=30, command=lambda x=i: self.app_master.open_edit_window(x)).grid(row=r, column=3, padx=2)
            ctk.CTkButton(self, text="🗑️", width=30, fg_color="firebrick", command=lambda x=i: self.app_master.delete_mapping(x)).grid(row=r, column=4, padx=2)

# --- 5. MAIN APP ---

class App(ctk.CTk):
    def __init__(self, port_name, output_port_name):
        super().__init__()

        self.lang_options = localization.get_available_languages()
        self.language_var = ctk.StringVar(value=localization.CURRENT_LANG)
        self.language_var.trace_add("write", self.change_language)

        self.layouts = load_layouts()
        self.current_layout_name = next(iter(self.layouts.keys()))
        self.key_map, self.cc_map, self.mappings_data = load_config()

        self.port_name = port_name
        self.output_port_name = output_port_name
        self.listener_thread = None
        self.midi_output = self.open_midi_output()

        self.title(localization.get_string('APP_TITLE'))
        self.geometry("650x600")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Переменная для режима Legacy Colors
        self.legacy_mode_var = ctk.BooleanVar(value=False)

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def get_safe_color(self, color_value):
        """Возвращает сконвертированный цвет, если включен режим Legacy, иначе оригинал"""
        if self.legacy_mode_var.get():
            return COLOR_TRANSLATION_TABLE.get(color_value, color_value)
        return color_value

    def refresh_lights(self):
        """Принудительно обновляет подсветку (если поток запущен)"""
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.send_initial_lighting()

    def create_widgets(self):
        for widget in self.winfo_children(): widget.destroy()

        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        ctk.CTkLabel(top_frame, text=localization.get_string('MIDI_MAPPER'), font=("Arial", 20, "bold")).pack(side="left")

        layout_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        layout_frame.pack(side="right", padx=(10, 0))
        ctk.CTkLabel(layout_frame, text=localization.get_string('LAYOUT_LABEL')).pack(side="left", padx=5)
        self.layout_var = ctk.StringVar(value=self.current_layout_name)
        layout_menu = ctk.CTkOptionMenu(layout_frame, values=list(self.layouts.keys()),
                                        variable=self.layout_var, command=self.change_layout)
        layout_menu.pack(side="left")

        lang_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        lang_frame.pack(side="right")
        ctk.CTkLabel(lang_frame, text=localization.get_string('LANGUAGE_LABEL')).pack(side="left", padx=5)
        ctk.CTkOptionMenu(lang_frame, values=self.lang_options, variable=self.language_var).pack(side="left")

        self.status_label = ctk.CTkLabel(self, text=localization.get_string('STATUS_READY'), fg_color="gray20", corner_radius=5, anchor="w", padx=10)
        self.status_label.grid(row=1, column=0, sticky="ew", padx=20, pady=5)

        self.mapping_table = MappingTableFrame(self, self.mappings_data)
        self.mapping_table.grid(row=3, column=0, sticky="nsew", padx=20, pady=5)

        # Нижняя панель управления
        ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=10)

        # Кнопка Start/Stop
        start_text = localization.get_string('START_BTN')
        fg_color = "green"
        if self.listener_thread and self.listener_thread.is_alive():
            start_text = localization.get_string('STOP_BTN')
            fg_color = "red"
        self.toggle_btn = ctk.CTkButton(ctrl_frame, text=start_text, command=self.toggle_listener, fg_color=fg_color)
        self.toggle_btn.pack(side="left", fill="x", expand=True, padx=5)

        # Настройки справа внизу
        right_ctrl = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        right_ctrl.pack(side="right")

        # Переключатель Legacy Colors
        legacy_txt = localization.get_string('LEGACY_COLORS_LABEL', default="Legacy Colors")
        self.legacy_switch = ctk.CTkSwitch(right_ctrl, text=legacy_txt, variable=self.legacy_mode_var, command=self.refresh_lights)
        self.legacy_switch.pack(side="left", padx=10)

        ctk.CTkButton(right_ctrl, text=localization.get_string('THEME_BTN'), width=50, command=self.toggle_theme).pack(side="left")

    def change_language(self, *args):
        new_lang = self.language_var.get()
        if localization.set_language(new_lang):
            self.create_widgets()
            self.update_status_label(localization.get_string('STATUS_READY'))

    def change_layout(self, choice):
        self.current_layout_name = choice
        self.update_status_label(localization.get_string('LAYOUT_LABEL') + f" {choice}")

    def open_midi_output(self):
        try: return open_output(self.output_port_name) if self.output_port_name else None
        except: return None

    def add_new_mapping(self):
        self.mappings_data.append({
            'type': 'note', 'id': 'NEW', 'keys_str': [],
            'description': localization.get_string('MAPPING_NEW_DESC'), 'color': 3
        })
        self.open_edit_window(len(self.mappings_data) - 1)

    def open_edit_window(self, index):
        EditMappingWindow(self, self.mappings_data[index], index, self.layouts[self.current_layout_name])

    def delete_mapping(self, index):
        del self.mappings_data[index]
        self.update_mappings()

    def update_mappings(self):
        self.mappings_data = [m for m in self.mappings_data if m['id'] != 'NEW']
        save_config(self.mappings_data)
        self.mapping_table.refresh_table(self.mappings_data)

        self.key_map = {}
        self.cc_map = {}
        for m in self.mappings_data:
            try:
                midi_id = int(m['id'])
                keys = []
                for k in m['keys_str']:
                    if k in constants.KEY_MAPPINGS: keys.append(constants.KEY_MAPPINGS[k])
                    elif len(k)==1:
                        try: keys.append(getattr(uinput, f'KEY_{k.upper()}'))
                        except: pass
                entry = {'keys': keys, 'color': m['color']}
                if m['type'] == 'note': self.key_map[midi_id] = entry
                elif m['type'] == 'cc': self.cc_map[midi_id] = entry
            except: pass

        if self.listener_thread and self.listener_thread.is_alive():
             self.update_status_label(localization.get_string('STATUS_UPDATED'))
             self.refresh_lights()

    def is_duplicate_mapping(self, m_type, m_id, current_index):
        for i, m in enumerate(self.mappings_data):
            if i == current_index: continue
            if m['type'] == m_type and str(m['id']) == str(m_id): return True
        return False

    def toggle_listener(self):
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
            except Exception as e: print(f"Ошибка при очистке: {e}")

    def update_status_label(self, text):
        self.status_label.configure(text=text)

    def toggle_theme(self):
        ctk.set_appearance_mode("Light" if ctk.get_appearance_mode()=="Dark" else "Dark")

    def on_closing(self):
        self.clear_launchpad()
        if self.listener_thread: self.listener_thread.stop()
        if self.midi_output: self.midi_output.close()
        self.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ins = get_input_names()
    outs = get_output_names()
    if not ins:
        print(localization.get_string("STATUS_ERROR", error="Нет MIDI устройств!"))
        sys.exit()
    in_port = next((n for n in ins if "launchpad" in n.lower()), ins[0])
    out_port = next((n for n in outs if "launchpad" in n.lower()), None)

    app = App(in_port, out_port)
    app.mainloop()
