# 📖 PadKey Mapper User Manual (EN)

## 1. Program Interface
The PKM interface consists of three main parts:

* **Localization and Layout (Top):** Selection of the Launchpad's MIDI ID Layout and language.
* **Mapping List (Middle):** Table of assigned key combinations and the button for adding a macro.
* **START/STOP Button, Old Colors Mode, Theme (Bottom):** Program start and stop, changing the backlight mode, changing the theme (Light/Dark).
* **Editor:** Appears when adding or editing a macro.

## 2. Start and Stop
1.  Select your MIDI ID Layout from the "Layout" dropdown menu.
2.  Add macro(s) (3. Adding a New Macro).
3.  Click the **"▶️ START"** button. The status should change to "✅ Listening...".
    * *Attention: If the status shows an error, make sure you have configured UDEV rules as described in the installation instructions.*
4.  To disconnect PKM, click the **"⏹️ STOP"** button.

## 3. Adding a New Macro / Deleting an Existing Macro
1.  Click the **"➕ Add Macro"** button. (For adding)
2.  Click the trash can icon to the right of an existing macro. (For deleting)
    * *Attention: Deleting will erase the macro from the configuration file!*
3.  After clicking **"➕ Add Macro"**, the macro editor window will appear.
4.  Follow the instructions in "4. Editing a Macro".

## 4. Editing a Macro
The editor allows you to configure which MIDI event triggers which action:

* **MIDI Type/ID:**
    * **MIDI Type:** Select `Note` (for buttons/pads) or `CC` (for the round side buttons/pads).
    * **ID:** Enter the unique MIDI ID number (If you don't know the MIDI ID number of your pad, switch "Show ID" to ON).
    * **Or:** Click the desired pad on the virtual Launchpad below. This will automatically input it into the correct field.
        * *Attention: Make sure you have selected the correct map/layout for your Launchpad model! Otherwise, the assigned macro may not appear, or may be in the wrong place after starting **[START]**
* **Keys (Клавиши):**
    * Click in the input field.
    * Enter the desired key combination. (The recording format will be approximately: `Key.ctrl + Key.shift + S`) (The full list of key notations will be listed below).
    * **Or:** Select the desired keys from the menu via the button to the right of the input field. (When you click the buttons in the menu, they will be correctly recorded in the field, with "+" signs).
* **Description (Описание):** A short name to be displayed in the list.
* **Color (Цвет):** Select the color number from the Launchpad palette.
* **[Save/Сохранить]**: Saves the change to `config.json` at the path `~/.config/PadKeyMapper/config.json` and applies the changes instantly.
* **[Cancel/Отменить]**: Cancels the changes without saving them to `config.json`.

## 5. Key Notations
```markdown
    Key.ctrl        -       CTRL
    Key.alt         -       ALT
    Key.shift       -       SHIFT
    Key.cmd         -       META/CMD
    Key.enter       -       ENTER
    Key.space       -       SPACE
    Key.tab         -       TAB
    Key.esc         -       ESC
    Key.backspace   -       BACKSPACE
    Key.delete      -       DEL
    Key.insert      -       INSERT
    Key.home        -       HOME
    Key.end         -       END
    Key.page_up     -       PAGE UP
    Key.page_down   -       PAGE DOWN
    Key.up          -       ↑
    Key.down        -       ↓
    Key.left        -       ←
    Key.right       -       →
    Key.ctrl_l      -       LEFT CTRL
    Key.ctrl_r      -       RIGHT CTRL
    Key.alt_l       -       LEFT ALT
    Key.alt_r       -       RIGHT ALT
    Key.shift_l     -       LEFT SHIFT
    Key.shift_r     -       RIGHT SHIFT
    Key.cmd_l       -       LEFT META/CMD
    Key.cmd_r       -       RIGHT META/CMD
    Key.caps_lock   -       CAPS LOCK
    Key.num_lock    -       NUM LOCK
    Key.print_screen-       PRT SCR
    Key.num0        -       NUM 0
    Key.num1        -       NUM 1
    Key.num2        -       NUM 2
    Key.num3        -       NUM 3
    Key.num4        -       NUM 4
    Key.num5        -       NUM 5
    Key.num6        -       NUM 6
    Key.num7        -       NUM 7
    Key.num8        -       NUM 8
    Key.num9        -       NUM 9
    Key.num_dot     -       NUM .
    Key.num_plus    -       NUM +
    Key.num_min     -       NUM -
    Key.num_eq      -       NUM =
    Key.num_comm    -       NUM ,
    Key.num_ast     -       NUM *
```
