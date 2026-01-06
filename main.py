import os
import sys
import glob
import time
import json
import threading
import re

# --- QT IMPORTS ---
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout, QLabel, QPushButton,
                             QComboBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QAbstractItemView, QDialog,
                             QLineEdit, QCheckBox, QScrollArea, QFrame, QMessageBox,
                             QSizePolicy, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSize, QTimer
from PyQt6.QtGui import QColor, QFont, QAction

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
    if not hasattr(uinput, "EV_KEY"): setattr(uinput, "EV_KEY", 1)
    if not hasattr(uinput, "EV_REL"): setattr(uinput, "EV_REL", 2)
    if not hasattr(uinput, "EV_ABS"): setattr(uinput, "EV_ABS", 3)
except ImportError as e:
    UINPUT_ERROR = f"ImportError: {e}"
except OSError as e:
    UINPUT_ERROR = f"OSError: {e}"
except Exception as e:
    UINPUT_ERROR = f"Unknown Error: {e}"

if UINPUT_AVAILABLE:
    if not hasattr(uinput, "EV_KEY"):
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

    user_path = os.path.join(CONFIG_DIR, "layouts_user.json")
    if os.path.exists(user_path):
        try:
            with open(user_path, 'r', encoding='utf-8') as f:
                user_layouts = json.load(f)
                layouts.update(user_layouts)
        except Exception as e:
            print(f"⚠️ Error loading layouts_user.json: {e}")
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
        m_mode = mapping.get('mode', 'Common-KB')

        parsed_sequence = []
        for key_str in m_keys_str:
            if key_str.startswith("{WAIT:") and key_str.endswith("}"):
                parsed_sequence.append(key_str)
            elif "{REL:" in key_str and "}" in key_str:
                parsed_sequence.append(key_str)
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
        rel_names = ['Key.mouse_x', 'Key.mouse_y', 'Key.mouse_wh']

        for name, key_val in constants.KEY_MAPPINGS.items():
            try:
                if isinstance(key_val, tuple):
                    all_keys.add((int(key_val[0]), int(key_val[1])))
                    continue
                code = int(key_val)
                if name in rel_names:
                    all_keys.add((uinput.EV_REL, code))
                else:
                    all_keys.add(code)
            except Exception as e:
                continue

        for char in 'abcdefghijklmnopqrstuvwxyz0123456789':
            attr_name = f'KEY_{char.upper()}'
            if hasattr(uinput, attr_name):
                key_code = getattr(uinput, attr_name)
                if isinstance(key_code, tuple):
                    all_keys.add((int(key_code[0]), int(key_code[1])))
                else:
                    all_keys.add(int(key_code))

        try:
            mouse_btns = [uinput.BTN_LEFT, uinput.BTN_RIGHT, uinput.BTN_MIDDLE]
            for btn in mouse_btns:
                if isinstance(btn, tuple):
                    all_keys.add((int(btn[0]), int(btn[1])))
                else:
                    all_keys.add(int(btn))
        except AttributeError:
            pass

        final_key_list = list(all_keys)
        if not final_key_list:
            self.init_error = "Key list is empty."
            return

        try:
            self.device = uinput.Device(final_key_list)
            print(f"✅ uinput device created. Capabilities: {len(final_key_list)}")
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
        if not self.device or not keys: return
        try:
            for key in keys:
                if isinstance(key, tuple): self.device.emit(key, 1)
                elif isinstance(key, int): self.device.emit((uinput.EV_KEY, key), 1)
        except Exception as e: print("[UINPUT] ERROR key_down:", e)

    def key_up(self, keys):
        if not self.device or not keys: return
        try:
            for key in keys:
                if isinstance(key, tuple): self.device.emit(key, 0)
                elif isinstance(key, int): self.device.emit((uinput.EV_KEY, key), 0)
        except Exception as e: print("[UINPUT] ERROR key_up:", e)

    def emit_rel(self, code, value):
        if not self.device: return
        try:
            final_code = code
            if isinstance(code, tuple) and len(code) == 2: final_code = code[1]
            axis_code = int(final_code)
            val = int(value)
            self.device.emit((uinput.EV_REL, axis_code), val)
        except Exception as e: print(f"[UINPUT] ERROR emit_rel: {e}")

    def send_keystroke(self, keys):
        if not self.device: return
        simple_keys = []
        for k in keys:
            if isinstance(k, int) or (isinstance(k, tuple) and len(k) == 2 and k[0] == uinput.EV_KEY):
                simple_keys.append(k)
            elif isinstance(k, tuple) and len(k) == 2:
                self.emit_rel(k[0], k[1])
        if simple_keys:
            self.key_down(simple_keys)
            time.sleep(0.015)
            self.key_up(simple_keys)

INPUT_MANAGER = InputManager()

class MacroExecutor:
    def __init__(self, input_manager):
        self.im = input_manager
        self.active_loops = {}
        self.active_toggles = {}
        self.app = None

    def execute(self, mapping_id, mapping_data, is_note_on):
        mode = mapping_data.get('mode', 'One-Shot')
        keys = mapping_data.get('keys', [])
        if not keys: return

        def _resolve_key_list(raw_keys):
            resolved = []
            for item in raw_keys:
                if isinstance(item, str) and item.startswith("{WAIT:"):
                    resolved.append(item)
                    continue
                if "{REL:" in item:
                    rel_match = re.search(r"\{REL:(-?\d+)\}", item)
                    if rel_match:
                        try:
                            val = int(rel_match.group(1))
                            key_part = item.split("{REL:")[0].strip()
                            if key_part in constants.KEY_MAPPINGS:
                                code = constants.KEY_MAPPINGS[key_part]
                                resolved.append((code, val))
                                continue
                        except ValueError: pass
                if item in constants.KEY_MAPPINGS:
                    if item in ['Key.mouse_x', 'Key.mouse_y', 'Key.mouse_wh']: continue
                    resolved.append(constants.KEY_MAPPINGS[item])
                    continue
                if isinstance(item, str) and item in constants.KEY_MAPPINGS:
                    resolved.append(constants.KEY_MAPPINGS[item])
                    continue
                if isinstance(item, tuple) and len(item) == 2:
                    code = item[1]
                    if isinstance(code, int): resolved.append(code); continue
                if isinstance(item, int): resolved.append(item); continue
                if isinstance(item, str) and item.isdigit(): resolved.append(int(item)); continue
                if isinstance(item, str) and item.startswith("KEY_"):
                    if hasattr(uinput, item): resolved.append(getattr(uinput, item)); continue
                if isinstance(item, str) and len(item) == 1:
                    keyname = f"KEY_{item.upper()}"
                    if hasattr(uinput, keyname): resolved.append(getattr(uinput, keyname)); continue
                if isinstance(item, str):
                    keyname = f"KEY_{item.upper()}"
                    if hasattr(uinput, keyname): resolved.append(getattr(uinput, keyname)); continue
            return resolved

        resolved_keys = _resolve_key_list(keys)
        if not resolved_keys: return

        if mode == "Common-KB":
            real_keys = [k for k in resolved_keys if isinstance(k, int)]
            if is_note_on:
                self.im.key_down(real_keys)
                for k in resolved_keys:
                    if isinstance(k, tuple): self.im.emit_rel(k[0], k[1])
                color = mapping_data.get("color", 15)
                if self.app:
                    self.app.start_feedback(mapping_id, color_on="#009900")
                    self.app.start_hw_feedback(mapping_id, color)
            else:
                self.im.key_up(real_keys)
                if self.app:
                    self.app.stop_feedback(mapping_id)
                    self.app.stop_hw_feedback(mapping_id)
            return

        if mode == 'One-Shot':
            if is_note_on:
                threading.Thread(target=self._run_sequence, args=(resolved_keys,)).start()
                if self.app:
                    self.app.start_feedback(mapping_id, color_on="#FF0000", color_off="#303030")
                    self.app.start_hw_feedback(mapping_id, mapping_data.get("color", 15))
            else:
                if self.app:
                    self.app.stop_feedback(mapping_id)
                    self.app.stop_hw_feedback(mapping_id)

        elif mode == 'Loop':
            if is_note_on:
                if mapping_id in self.active_loops:
                    self.active_loops[mapping_id].set()
                    del self.active_loops[mapping_id]
                    if self.app:
                        self.app.stop_feedback(mapping_id)
                        self.app.stop_hw_feedback(mapping_id)
                    return
                stop_event = threading.Event()
                self.active_loops[mapping_id] = stop_event
                t = threading.Thread(target=self._run_loop, args=(resolved_keys, stop_event))
                t.start()
                if self.app:
                    self.app.start_feedback(mapping_id)
                    self.app.start_hw_feedback(mapping_id, mapping_data.get("color", 15))

        elif mode == 'Toggle (Hold)':
            if is_note_on:
                held = self.active_toggles.get(mapping_id, False)
                real_keys = [k for k in resolved_keys if isinstance(k, int)]
                if not held:
                    self.im.key_down(real_keys)
                    for item in resolved_keys:
                        if isinstance(item, tuple): self.im.emit_rel(item[0], item[1])
                    self.active_toggles[mapping_id] = True
                    if self.app:
                        self.app.start_feedback(mapping_id)
                        self.app.start_hw_feedback(mapping_id, mapping_data.get("color", 15))
                else:
                    self.im.key_up(real_keys)
                    self.active_toggles[mapping_id] = False
                    if self.app:
                        self.app.stop_feedback(mapping_id)
                        self.app.stop_hw_feedback(mapping_id)

    def _run_sequence(self, keys):
        current_chord = []
        for item in keys:
            if isinstance(item, str) and item.startswith("{WAIT:"):
                if current_chord:
                    self.im.send_keystroke(current_chord)
                    current_chord = []
                try:
                    val = float(re.search(r"[\d\.]+", item).group())
                    time.sleep(val)
                except Exception: pass
            elif isinstance(item, tuple) and len(item) == 2:
                if current_chord:
                    self.im.send_keystroke(current_chord)
                    current_chord = []
                self.im.emit_rel(item[0], item[1])
            elif isinstance(item, int):
                current_chord.append(item)
            elif isinstance(item, str) and item.isdigit():
                try: current_chord.append(int(item))
                except: pass
        if current_chord:
            self.im.send_keystroke(current_chord)

    def _run_loop(self, keys, stop_event):
        while not stop_event.is_set():
            self._run_sequence(keys)
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
                    processed_any = False
                    for msg in port.iter_pending():
                        processed_any = True
                        if msg.type == 'note_on' or msg.type == 'note_off':
                            raw_id = msg.note
                            id_str = str(raw_id)
                            keys_data = self.app.key_map.get(id_str)
                            if keys_data is None: keys_data = self.app.key_map.get(raw_id)
                            if keys_data:
                                is_on = (msg.type == 'note_on' and getattr(msg, 'velocity', 0) > 0)
                                MACRO_EXECUTOR.execute(id_str if id_str in self.app.key_map else raw_id, keys_data, is_on)
                        elif msg.type == 'control_change':
                            raw_id = msg.control
                            id_str = str(raw_id)
                            keys_data = self.app.cc_map.get(id_str)
                            if keys_data is None: keys_data = self.app.cc_map.get(raw_id)
                            if keys_data:
                                is_on = (getattr(msg, 'value', 0) > 0)
                                MACRO_EXECUTOR.execute(id_str if id_str in self.app.cc_map else raw_id, keys_data, is_on)

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


# --- 5. GUI COMPONENTS (PyQt6) ---

class VirtualPadVisualizer(QWidget):
    def __init__(self, parent=None, layout_config={}, button_callback=None, btn_size=40):
        super().__init__(parent)
        self.layout_config = layout_config
        self.button_callback = button_callback
        self.btn_size = btn_size
        self.buttons = {}

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.grid_frame = QFrame()
        self.grid = QGridLayout(self.grid_frame)
        self.grid.setSpacing(2)
        self.main_layout.addWidget(self.grid_frame)

        self.render()

    def render(self):
        # Clear existing
        for i in reversed(range(self.grid.count())):
            self.grid.itemAt(i).widget().setParent(None)
        self.buttons = {}

        layout_type = self.layout_config.get("type", "Mini")

        def add_btn(row, col, label, m_type, m_id, is_side=False):
            btn = QPushButton(label)
            btn.setFixedSize(self.btn_size, self.btn_size)
            btn.setProperty("is_side", is_side)

            # Default style
            bg_color = "#393939" if not is_side else "#1e1e1e"
            btn.setStyleSheet(f"background-color: {bg_color}; border-radius: 4px; color: white;")

            if self.button_callback:
                btn.clicked.connect(lambda _, t=m_type, i=m_id: self.button_callback(i, t))
            else:
                btn.setEnabled(False)

            self.grid.addWidget(btn, row, col)
            self.buttons[(m_type, m_id)] = btn

        if layout_type == "Mini":
            cc_start = self.layout_config.get("cc_row_start", 104)
            cc_end = self.layout_config.get("cc_row_end", 111)
            side_notes = self.layout_config.get("side_notes", [])

            for idx, cc_id in enumerate(range(cc_start, cc_end + 1)):
                add_btn(0, idx, f"{cc_id}", 'cc', cc_id)

            for r in range(8):
                for c in range(8):
                    note_id = r * 16 + c
                    add_btn(r+1, c, "", 'note', note_id)
                if r < len(side_notes):
                    s_id = side_notes[r]
                    add_btn(r+1, 8, f"{s_id}", 'note', s_id, is_side=True)

        elif layout_type == "Pro":
             top = self.layout_config.get("top_notes", [])
             left = self.layout_config.get("left_notes", [])
             right = self.layout_config.get("right_notes", [])
             bottom = self.layout_config.get("bottom_notes", [])
             grid_start = self.layout_config.get("grid_start_note", 11)

             for c, n_id in enumerate(top):
                 add_btn(0, c+1, f"{n_id}", 'note', n_id)

             for r in range(8):
                 if r < len(left):
                     add_btn(r+1, 0, f"{left[r]}", 'note', left[r], is_side=True)
                 for c in range(8):
                     note_id = grid_start + (7-r) * 10 + c
                     add_btn(r+1, c+1, "", 'note', note_id)
                 if r < len(right):
                     add_btn(r+1, 9, f"{right[r]}", 'note', right[r], is_side=True)

             for c, n_id in enumerate(bottom):
                 add_btn(9, c+1, f"{n_id}", 'note', n_id)

        elif layout_type == "Universal":
            notes = self.layout_config.get("notes", [])
            ccs = self.layout_config.get("cc", [])
            row, col = 0, 0
            for i in ccs:
                add_btn(row, col, str(i), 'cc', i, is_side=True)
                col += 1
                if col > 15: col = 0; row += 1
            row += 1
            col = 0
            for i in notes:
                add_btn(row, col, str(i), 'note', i)
                col += 1
                if col > 15: col = 0; row += 1

    def update_states(self, mappings_data, current_selection=None):
        layout_type = self.layout_config.get("type", "Mini")

        # Reset colors
        for (m_type, m_id), btn in self.buttons.items():
            base_color = "#393939"
            if m_type == 'cc' or (layout_type == "Mini" and m_id % 16 == 8): base_color = "#1e1e1e"

            show_text = ""
            if layout_type != "Mini" or m_type == 'cc' or m_id % 16 == 8:
                show_text = str(m_id)

            btn.setText(show_text)
            btn.setStyleSheet(f"background-color: {base_color}; border-radius: 4px; color: white;")

        # Active mappings
        for idx, m in enumerate(mappings_data):
            if m['id'] == 'NEW': continue
            try:
                mid = int(m['id'])
                mtype = m['type']
                if (mtype, mid) in self.buttons:
                    btn = self.buttons[(mtype, mid)]
                    btn.setText(str(idx + 1))
                    color = "#0a78d1" if mtype=='note' else "#c28e0a" # Teal / DarkOrange
                    btn.setStyleSheet(f"background-color: {color}; border-radius: 4px; color: white;")
            except: pass

        if current_selection:
            cs_id = current_selection.get('id')
            cs_type = current_selection.get('type')
            try: cs_id = int(cs_id)
            except: pass
            if (cs_type, cs_id) in self.buttons:
                self.buttons[(cs_type, cs_id)].setStyleSheet("background-color: #f25a0f; border-radius: 4px; color: white;")

    def get_button_by_id(self, mapping_id):
        # Only checks NOTE ID for simplicity in feedback loop for now, similar to original
        # This is a limitation of the feedback loop structure in original code
        for (tp, mid), btn in self.buttons.items():
            if str(mid) == str(mapping_id):
                return btn
        return None

    def set_btn_color(self, btn, color_hex):
        btn.setStyleSheet(f"background-color: {color_hex}; border-radius: 4px; color: white;")

class KeySelectionDialog(QDialog):
    def __init__(self, parent, target_entry):
        super().__init__(parent)
        self.target_entry = target_entry
        self.setWindowTitle(localization.get_string('KEY_SELECT_TITLE'))
        self.resize(350, 600)

        layout = QVBoxLayout(self)

        lbl = QLabel(localization.get_string('KEY_SELECT_LABEL'))
        layout.addWidget(lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        scroll_layout = QVBoxLayout(content_widget)

        sorted_keys = sorted(constants.KEY_MAPPINGS.keys())
        for key_name in sorted_keys:
            display_name = constants.KEY_DISPLAY_MAPPINGS.get(key_name, key_name)
            btn = QPushButton(display_name)
            btn.clicked.connect(lambda _, k=key_name: self.insert_key(k))
            scroll_layout.addWidget(btn)

        scroll_layout.addWidget(QLabel(localization.get_string('KEY_SELECT_SYMBOLS')))

        grid_chars = QGridLayout()
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        r, c = 0, 0
        for char in chars:
            btn = QPushButton(char)
            btn.setFixedSize(30, 30)
            btn.clicked.connect(lambda _, k=char: self.insert_key(k))
            grid_chars.addWidget(btn, r, c)
            c += 1
            if c > 5: c = 0; r += 1

        scroll_layout.addLayout(grid_chars)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

    def insert_key(self, key_value):
        current_text = self.target_entry.text().strip()
        key_to_insert = key_value
        if current_text and not current_text.endswith("+") and not current_text.endswith(" "):
            new_text = f"{current_text} + {key_to_insert}"
        else:
            new_text = f"{current_text}{key_to_insert}"
        self.target_entry.setText(new_text)
        self.accept()

class EditMappingDialog(QDialog):
    def __init__(self, parent, mapping_data, index, layout_config):
        super().__init__(parent)
        self.mapping_data = mapping_data
        self.index = index
        self.master_app = parent
        self.layout_config = layout_config

        title_id = mapping_data['id'] if mapping_data['id'] != 'NEW' else localization.get_string('EDIT_NEW_TITLE')
        self.setWindowTitle(localization.get_string('EDIT_TITLE', id=title_id))
        self.resize(700, 800)

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)

        # Form Layout
        form_frame = QFrame()
        grid = QGridLayout(form_frame)

        # MIDI ID
        grid.addWidget(QLabel(localization.get_string('EDIT_MIDI_ID')), 0, 0)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["note", "cc"])
        self.type_combo.setCurrentText(self.mapping_data['type'])
        grid.addWidget(self.type_combo, 0, 1)

        self.id_entry = QLineEdit()
        curr_id = str(self.mapping_data['id']) if self.mapping_data['id'] != 'NEW' else ''
        self.id_entry.setText(curr_id)
        self.id_entry.setPlaceholderText("ID (0-127)")
        grid.addWidget(self.id_entry, 0, 2)

        # Keys
        grid.addWidget(QLabel(localization.get_string('EDIT_KEYS')), 1, 0)
        keys_str = " + ".join(self.mapping_data['keys_str'])
        self.keys_entry = QLineEdit(keys_str)
        grid.addWidget(self.keys_entry, 1, 1, 1, 2)

        btn_box = QHBoxLayout()
        btn_delay = QPushButton("⏱️ Delay")
        btn_delay.clicked.connect(self.insert_delay)
        btn_key = QPushButton("⌨️")
        btn_key.clicked.connect(self.open_key_menu)
        btn_box.addWidget(btn_delay)
        btn_box.addWidget(btn_key)
        grid.addLayout(btn_box, 1, 3)

        # Mode
        grid.addWidget(QLabel("Mode:"), 2, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Common-KB", "One-Shot", "Loop", "Toggle (Hold)"])
        self.mode_combo.setCurrentText(self.mapping_data.get('mode', 'One-Shot'))
        grid.addWidget(self.mode_combo, 2, 1, 1, 2)

        # Desc
        grid.addWidget(QLabel(localization.get_string('EDIT_DESC')), 3, 0)
        self.desc_entry = QLineEdit(self.mapping_data['description'])
        grid.addWidget(self.desc_entry, 3, 1, 1, 2)

        # Color
        grid.addWidget(QLabel(localization.get_string('EDIT_COLOR')), 4, 0)
        color_layout = QHBoxLayout()
        self.color_combo = QComboBox()

        initial_color = self.mapping_data.get('color', 0)
        color_names = list(constants.LAUNCHPAD_COLORS.values())
        self.color_combo.addItems(color_names)

        initial_name = next((v for k, v in constants.LAUNCHPAD_COLORS.items() if k == initial_color), localization.get_string('COLOR_CUSTOM'))
        if initial_name not in color_names:
            self.color_combo.addItem(initial_name)
        self.color_combo.setCurrentText(initial_name)
        self.color_combo.currentTextChanged.connect(self._on_preset_color_select)

        self.manual_color_entry = QLineEdit(str(initial_color))
        self.manual_color_entry.setFixedWidth(50)

        color_layout.addWidget(self.color_combo)
        color_layout.addWidget(self.manual_color_entry)
        grid.addLayout(color_layout, 4, 1, 1, 2)

        main_layout.addWidget(form_frame)

        # Virtual Pad
        main_layout.addWidget(QLabel(localization.get_string('EDIT_VIRTUAL_PAD', layout=self.layout_config.get('type'))))

        self.scroll_area = QScrollArea()
        self.visualizer = VirtualPadVisualizer(
            layout_config=self.layout_config,
            button_callback=self.map_midi_pad,
            btn_size=45 if self.layout_config.get('type') != 'Universal' else 25
        )
        self.scroll_area.setWidget(self.visualizer)
        self.scroll_area.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_area)
        self.visualizer.update_states(self.master_app.mappings_data,
                                      current_selection={'type': self.mapping_data['type'], 'id': self.mapping_data['id']})

        # Buttons
        bbox = QHBoxLayout()
        save_btn = QPushButton(localization.get_string('EDIT_SAVE'))
        save_btn.clicked.connect(self.save_and_close)
        cancel_btn = QPushButton(localization.get_string('EDIT_CANCEL'))
        cancel_btn.clicked.connect(self.reject)

        bbox.addWidget(save_btn)
        bbox.addWidget(cancel_btn)
        main_layout.addLayout(bbox)

    def insert_delay(self):
        text = self.keys_entry.text().strip()
        tag = "{WAIT:0.1}"
        new_text = f"{text} + {tag}" if (text and not text.endswith("+")) else f"{text}{tag}"
        self.keys_entry.setText(new_text)

    def open_key_menu(self):
        KeySelectionDialog(self, self.keys_entry).exec()

    def _on_preset_color_select(self, choice):
        for k, v in constants.LAUNCHPAD_COLORS.items():
            if v == choice:
                self.manual_color_entry.setText(str(k))
                return

    def map_midi_pad(self, midi_id, midi_type):
        self.type_combo.setCurrentText(midi_type)
        self.id_entry.setText(str(midi_id))
        self.visualizer.update_states(self.master_app.mappings_data,
                                      current_selection={'type': midi_type, 'id': midi_id})

    def save_and_close(self):
        try: new_id_val = int(self.id_entry.text().strip())
        except ValueError:
            QMessageBox.critical(self, "Error", localization.get_string('STATUS_ID_ERROR'))
            return

        new_type = self.type_combo.currentText()
        new_desc = self.desc_entry.text().strip()
        new_mode = self.mode_combo.currentText()
        new_keys_raw = self.keys_entry.text().strip()
        new_keys_list = [k.strip() for k in new_keys_raw.replace(' ', '').split('+') if k.strip()]

        try:
            new_color = int(self.manual_color_entry.text().strip())
            if not 0 <= new_color <= 127: raise ValueError
        except ValueError:
            QMessageBox.critical(self, "Error", localization.get_string('STATUS_COLOR_ERROR'))
            return

        current_id_str = str(self.mapping_data['id'])
        if current_id_str != str(new_id_val) or current_id_str == 'NEW':
            if self.master_app.is_duplicate_mapping(new_type, new_id_val, self.index):
                QMessageBox.critical(self, "Error", localization.get_string('STATUS_MAPPING_USED', type=new_type.upper(), id=new_id_val))
                return

        self.master_app.mappings_data[self.index].update({
            'id': new_id_val, 'type': new_type, 'keys_str': new_keys_list,
            'description': new_desc, 'color': new_color, 'mode': new_mode
        })
        self.master_app.update_mappings()
        self.accept()

class App(QMainWindow):
    # --- SIGNALS FOR THREAD COMMUNICATION ---
    sig_status_update = pyqtSignal(str, bool)
    sig_start_feedback = pyqtSignal(object, str, str) # id, color_on, color_off
    sig_stop_feedback = pyqtSignal(object)
    sig_hw_feedback = pyqtSignal(object, int)
    sig_stop_hw_feedback = pyqtSignal(object)

    def __init__(self, port_name, output_port_name):
        super().__init__()

        # Logic Init
        self.settings = SettingsManager.load()
        localization.set_language(self.settings.get("language", "EN"))
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

        # Connect Logic
        MACRO_EXECUTOR.app = self

        # Feedback state
        self.active_feedback = {}
        self.feedback_running = False
        self.hw_feedback = {}
        self.hw_feedback_running = False

        # GUI Init
        self.setWindowTitle(localization.get_string('APP_TITLE'))
        self.resize(1190, 600)
        self.setup_ui()
        self.connect_signals()

        if INPUT_MANAGER.init_error:
            self.update_status_label(localization.get_string('STATUS_ERROR', error=INPUT_MANAGER.init_error), is_error=True)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header
        header = QHBoxLayout()
        title = QLabel(localization.get_string('MIDI_MAPPER'))
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header.addWidget(title)

        header.addStretch()

        header.addWidget(QLabel(localization.get_string('PROFILE_LABEL')))
        self.profile_combo = QComboBox()
        self.refresh_profile_list()
        self.profile_combo.currentTextChanged.connect(self.change_profile)
        header.addWidget(self.profile_combo)

        header.addWidget(QLabel(localization.get_string('LAYOUT_LABEL')))
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(list(self.layouts.keys()))
        self.layout_combo.setCurrentText(self.current_layout_name)
        self.layout_combo.currentTextChanged.connect(self.change_layout)
        header.addWidget(self.layout_combo)

        main_layout.addLayout(header)

        # Content
        content = QHBoxLayout()

        # Left: Visualizer
        left_panel = QFrame()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Active Mapping View"))

        self.vis_scroll = QScrollArea()
        layout_cfg = self.layouts.get(self.current_layout_name, {})
        self.main_visualizer = VirtualPadVisualizer(
            layout_config=layout_cfg,
            btn_size=35 if layout_cfg.get('type') != 'Universal' else 20
        )
        self.vis_scroll.setWidget(self.main_visualizer)
        self.vis_scroll.setWidgetResizable(True)
        left_layout.addWidget(self.vis_scroll)

        content.addWidget(left_panel, 1) # Stretch factor 1

        # Right: Table & Controls
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)

        self.status_label = QLabel(localization.get_string('STATUS_READY'))
        self.status_label.setStyleSheet("color: gray;")
        right_layout.addWidget(self.status_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["#", "MIDI", "Keys", "Mode", "Desc", "Edit", "Del"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.table)

        add_btn = QPushButton(localization.get_string('ADD_MAPPING_BTN'))
        add_btn.clicked.connect(self.add_new_mapping)
        right_layout.addWidget(add_btn)

        # Footer Controls
        footer = QHBoxLayout()
        self.start_btn = QPushButton(localization.get_string('START_BTN'))
        self.start_btn.clicked.connect(self.toggle_listener)
        self.start_btn.setFixedHeight(40)
        footer.addWidget(self.start_btn)

        self.legacy_check = QCheckBox(localization.get_string('LEGACY_COLORS_LABEL'))
        self.legacy_check.setChecked(self.settings.get("legacy_colors", False))
        self.legacy_check.toggled.connect(self.refresh_lights)
        footer.addWidget(self.legacy_check)

        lang_combo = QComboBox()
        lang_combo.addItems(localization.get_available_languages())
        lang_combo.setCurrentText(localization.CURRENT_LANG)
        lang_combo.currentTextChanged.connect(self.change_language)
        footer.addWidget(lang_combo)

        right_layout.addLayout(footer)
        content.addWidget(right_panel, 2) # Stretch factor 2

        main_layout.addLayout(content)

        self.refresh_table()
        self.main_visualizer.update_states(self.mappings_data)

    def connect_signals(self):
        self.sig_status_update.connect(self._slot_status_update)
        self.sig_start_feedback.connect(self._slot_start_feedback)
        self.sig_stop_feedback.connect(self._slot_stop_feedback)
        self.sig_hw_feedback.connect(self.start_hw_feedback_impl) # Direct call to logic implementation is safe if logic is just setting variable? NO.
        # HW feedback logic involves timers. It should be safe to run timers in main thread.
        # Actually start_hw_feedback logic uses .after in Tkinter. In Qt we use QTimer.

        # Since HW Feedback logic was designed for Tkinter's single thread loop, we can just adapt the methods.
        # But wait, start_hw_feedback is called from Thread. So we MUST use signal to trigger it on MainThread.
        pass # Connections are made, logic below.

    # --- WRAPPERS FOR THREAD SAFE CALLS ---
    def update_status_label(self, text, is_error=False):
        self.sig_status_update.emit(text, is_error)

    def start_feedback(self, mapping_id, color_on="#ff00dd", color_off="#303030"):
        self.sig_start_feedback.emit(mapping_id, color_on, color_off)

    def stop_feedback(self, mapping_id):
        self.sig_stop_feedback.emit(mapping_id)

    def start_hw_feedback(self, mapping_id, color):
        self.sig_hw_feedback.emit(mapping_id, color)

    def stop_hw_feedback(self, mapping_id):
        self.sig_stop_hw_feedback.emit(mapping_id)

    # --- SLOTS (Executed on Main Thread) ---
    @pyqtSlot(str, bool)
    def _slot_status_update(self, text, is_error):
        color = "red" if is_error else "gray"
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    @pyqtSlot(object, str, str)
    def _slot_start_feedback(self, mapping_id, color_on, color_off):
        self.active_feedback[mapping_id] = {
            "state": True, "color_on": color_on, "color_off": color_off
        }
        if not self.feedback_running:
            self.feedback_running = True
            QTimer.singleShot(500, self._feedback_tick)

    @pyqtSlot(object)
    def _slot_stop_feedback(self, mapping_id):
        if mapping_id in self.active_feedback:
            del self.active_feedback[mapping_id]
        if not self.active_feedback:
            self.feedback_running = False
            self.main_visualizer.update_states(self.mappings_data)

    def _feedback_tick(self):
        if not self.feedback_running: return

        to_delete = []
        for mapping_id, data in self.active_feedback.items():
            data["state"] = not data["state"]
            color = data["color_on"] if data["state"] else data["color_off"]
            btn = self.main_visualizer.get_button_by_id(mapping_id)
            if btn: self.main_visualizer.set_btn_color(btn, color)
            else: to_delete.append(mapping_id)

        for d in to_delete: del self.active_feedback[d]

        if self.active_feedback:
            QTimer.singleShot(500, self._feedback_tick)

    @pyqtSlot(object, int)
    def start_hw_feedback_impl(self, mapping_id, color):
        try:
            restore_color = 0
            for m in self.mappings_data:
                if str(m['id']) == str(mapping_id):
                    restore_color = int(self.get_safe_color(m.get('color', 0)))
                    break
        except: restore_color = 0

        self.hw_feedback[mapping_id] = {
            "state": True, "color": int(color), "orig_color": int(restore_color)
        }
        if not self.hw_feedback_running:
            self.hw_feedback_running = True
            self._hw_feedback_tick()

    def _hw_feedback_tick(self):
        if not self.hw_feedback_running: return
        if not self.hw_feedback:
            self.hw_feedback_running = False
            return

        for mapping_id, data in list(self.hw_feedback.items()):
            data["state"] = not data["state"]
            velocity = data["color"] if data["state"] else 0
            try:
                if self.midi_output:
                    self.midi_output.send(Message('note_on', note=int(mapping_id), velocity=int(velocity)))
            except Exception as e: print(e)

        if self.hw_feedback_running and self.hw_feedback:
            QTimer.singleShot(500, self._hw_feedback_tick)
        else:
            self.hw_feedback_running = False

    def stop_hw_feedback_impl(self, mapping_id):
        # Implementation moved from original stop_hw_feedback
        try:
            orig = None
            if mapping_id in self.hw_feedback:
                orig = self.hw_feedback[mapping_id].get("orig_color")
                del self.hw_feedback[mapping_id]

            if not self.hw_feedback: self.hw_feedback_running = False

            restore_color = 0
            if orig is not None: restore_color = int(orig)
            else:
                for m in self.mappings_data:
                    if str(m["id"]) == str(mapping_id):
                        restore_color = int(self.get_safe_color(m.get("color", 0)))
                        break

            if self.midi_output:
                self.midi_output.send(Message("note_on", note=int(mapping_id), velocity=int(restore_color)))
        except Exception as e: print(e)

    # --- LOGIC ACTIONS ---

    def refresh_profile_list(self):
        self.profiles_list = get_available_profiles()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(self.profiles_list)
        self.profile_combo.addItem("---")
        self.profile_combo.addItem(localization.get_string('PROFILE_NEW'))
        self.profile_combo.setCurrentText(self.current_profile_name)
        self.profile_combo.blockSignals(False)

    def change_profile(self, choice):
        if choice == localization.get_string('PROFILE_NEW'):
            text, ok = QInputDialog.getText(self, localization.get_string('PROFILE_NEW'), localization.get_string('PROFILE_NEW_PROMPT'))
            if ok and text:
                filename = f"{text.strip().replace(' ', '_').replace('.json', '')}.json"
                if filename in self.profiles_list:
                    self.update_status_label(localization.get_string('STATUS_PROFILE_EXISTS'), is_error=True)
                    self.profile_combo.setCurrentText(self.current_profile_name)
                    return
                new_path = os.path.join(PROFILES_DIR, filename)
                with open(new_path, 'w', encoding='utf-8') as f:
                    json.dump({"mappings": []}, f, indent=4)
                self.current_profile_name = filename
                self.refresh_profile_list()
                self.load_profile(filename, is_new=True)
            else:
                self.profile_combo.setCurrentText(self.current_profile_name)
        elif choice != "---":
            self.load_profile(choice)

    def load_profile(self, filename, is_new=False):
        self.current_profile_name = filename
        self.save_app_settings()
        self.key_map, self.cc_map, self.mappings_data = load_profile_data(self.current_profile_name)
        self.refresh_table()
        self.main_visualizer.update_states(self.mappings_data)
        self.update_status_label(f"Profile loaded: {filename}")
        if self.listener_thread and self.listener_thread.is_alive():
            self.refresh_lights()

    def change_layout(self, choice):
        self.current_layout_name = choice
        self.save_app_settings()
        # Recreate visualizer logic
        self.vis_scroll.takeWidget() # Remove old
        layout_cfg = self.layouts.get(self.current_layout_name, {})
        self.main_visualizer = VirtualPadVisualizer(
            layout_config=layout_cfg,
            btn_size=35 if layout_cfg.get('type') != 'Universal' else 20
        )
        self.vis_scroll.setWidget(self.main_visualizer)
        self.main_visualizer.update_states(self.mappings_data)

    def refresh_table(self):
        self.table.setRowCount(0)
        for i, m in enumerate(self.mappings_data):
            if m['id'] == 'NEW': continue
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(i+1)))
            self.table.setItem(row, 1, QTableWidgetItem(f"{m['type'][0].upper()}:{m['id']}"))

            display_keys = []
            for k in m['keys_str']:
                if "WAIT" in k: display_keys.append("🕒")
                else: display_keys.append(constants.KEY_DISPLAY_MAPPINGS.get(k, k))
            self.table.setItem(row, 2, QTableWidgetItem(" + ".join(display_keys)))

            self.table.setItem(row, 3, QTableWidgetItem(m.get('mode', 'One-Shot')))
            self.table.setItem(row, 4, QTableWidgetItem(m['description']))

            edit_btn = QPushButton("✎")
            edit_btn.clicked.connect(lambda _, x=i: self.open_edit_window(x))
            self.table.setCellWidget(row, 5, edit_btn)

            del_btn = QPushButton("🗑️")
            del_btn.setStyleSheet("color: red;")
            del_btn.clicked.connect(lambda _, x=i: self.delete_mapping(x))
            self.table.setCellWidget(row, 6, del_btn)

    def add_new_mapping(self):
        self.mappings_data.append({
            'type': 'note', 'id': 'NEW', 'keys_str': [],
            'description': localization.get_string('MAPPING_NEW_DESC'), 'color': 3, 'mode': 'Common-KB'
        })
        self.open_edit_window(len(self.mappings_data) - 1)

    def open_edit_window(self, index):
        current_layout = self.layouts.get(self.current_layout_name, {})
        dlg = EditMappingDialog(self, self.mappings_data[index], index, current_layout)
        dlg.exec()

    def delete_mapping(self, index):
        del self.mappings_data[index]
        self.update_mappings()

    def update_mappings(self):
        self.mappings_data = [m for m in self.mappings_data if m['id'] != 'NEW']
        save_profile_data(self.mappings_data, self.current_profile_name)
        self.refresh_table()
        self.main_visualizer.update_states(self.mappings_data)

        self.key_map = {}
        self.cc_map = {}
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
            self.start_btn.setText(localization.get_string('STOP_BTN'))
            self.start_btn.setStyleSheet("background-color: #0b65db; color: white;") # Blue
        else:
            self.listener_thread.stop()
            self.clear_launchpad()
            self.stop_all_feedbacks()
            self.start_btn.setText(localization.get_string('START_BTN'))
            self.start_btn.setStyleSheet("") # Reset style

    def stop_all_feedbacks(self):
        self.active_feedback.clear()
        self.feedback_running = False
        self.main_visualizer.update_states(self.mappings_data)

        for mid in list(self.hw_feedback.keys()):
            self.stop_hw_feedback_impl(mid)
        self.hw_feedback.clear()
        self.hw_feedback_running = False

    def clear_launchpad(self):
        if self.midi_output:
            try:
                for m in self.mappings_data:
                    try:
                        mid_id = int(m['id'])
                        if m['type'] == 'note': self.midi_output.send(Message('note_on', note=mid_id, velocity=0))
                        elif m['type'] == 'cc': self.midi_output.send(Message('control_change', control=mid_id, value=0))
                    except: pass
            except Exception as e: print(f"Clear Error: {e}")

    def refresh_lights(self):
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.send_initial_lighting()
        self.save_app_settings()

    def change_language(self, lang):
        if localization.set_language(lang):
            self.save_app_settings()
            # In PyQt fully reloading texts requires re-setting text on all widgets.
            # For simplicity, we restart UI creation or user restarts app.
            # Here just saving settings.
            QMessageBox.information(self, "Language", "Language changed. Please restart app to apply all texts.")

    def get_safe_color(self, color_value):
        if self.legacy_check.isChecked():
            return COLOR_TRANSLATION_TABLE.get(color_value, color_value)
        return color_value

    def save_app_settings(self):
        self.settings.update({
            "legacy_colors": self.legacy_check.isChecked(),
            "last_profile": self.current_profile_name,
            "last_layout": self.current_layout_name,
            "language": localization.CURRENT_LANG
        })
        SettingsManager.save(self.settings)

    def open_midi_output(self):
        try: return open_output(self.output_port_name) if self.output_port_name else None
        except: return None

    def closeEvent(self, event):
        self.save_app_settings()
        self.clear_launchpad()
        if self.listener_thread: self.listener_thread.stop()
        if self.midi_output: self.midi_output.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Auto-detect ports
    ins = get_input_names()
    outs = get_output_names()
    in_port = next((n for n in ins if "launchpad" in n.lower()), None)
    out_port = next((n for n in outs if "launchpad" in n.lower()), None)
    if not in_port and ins: in_port = ins[0]
    if not out_port and outs: out_port = outs[0]

    window = App(in_port, out_port)
    window.show()

    # Connect signals for HW feedback implementation (Wiring the internal signal to slot)
    window.sig_stop_hw_feedback.connect(window.stop_hw_feedback_impl)

    sys.exit(app.exec())
