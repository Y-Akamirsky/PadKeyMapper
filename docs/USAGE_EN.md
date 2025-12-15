# 📖 PadKey Mapper User Guide (EN)

## 1. Program Interface
The PadKey Mapper (PKM) interface consists of three main parts:

* **Localization, Config Selection/Creation, and Layout (Top):** Selecting the MIDI ID Layout of the Launchpad and language, as well as selecting and creating a custom configuration.
* **Mappings List (Middle):** A table of assigned key combinations and a button to add a macro.
* **START/STOP Button, Legacy Color Mode, Theme (Bottom):** Starting and stopping the program, changing the illumination mode, changing the theme (Light/Dark).
* **Editor:** Appears when adding or editing a macro.

## 2. Startup and Shutdown
1.  Select your MIDI ID Layout from the "Layout" dropdown menu.
2.  Add macro(s) (see 3. Adding a New Macro / Deleting an Existing One).
3.  Click the **"▶️ START"** button. The status should change to "✅ Listening...".
    * *Attention: If the status shows an error, ensure you have configured UDEV rules as described in the installation instructions.*
4.  To disable PKM, click the **"⏹️ STOP"** button.

## 3. Adding a New Macro / Deleting an Existing One
1.  Select/create a config (or use the standard one).
2.  Click the **"➕ Add Macro"** button (to add).
3.  Click the trash can icon to the right of an existing macro (to delete).
    * *Attention: Deleting will erase the macro from the configuration file!*
4.  After clicking **"➕ Add Macro"**, the macro editor window will appear.
5.  Follow the instructions in 4. Editing a Macro.

## 4. Editing a Macro
The editor allows you to configure which MIDI event triggers which action:

* **MIDI Type/ID:**
    * **MIDI Type:** Select `Note` (for buttons/pads) or `CC` (for side round buttons/pads).
    * **ID:** Enter the unique MIDI ID number (If you don't know your pad's MIDI ID number, toggle "Show ID" to ON).
    * **Or:** Click on the desired pad on the virtual Launchpad below. This will automatically record it into the required field.
        * *Attention: Make sure you have selected the correct map/layout for your Launchpad model! Otherwise, the assigned macro may not be displayed or may be in the wrong location after starting **[START]***.
* **Mode:**
    * **Select the mode for your assignment:**
        -   **CommonKB** -   Standard keyboard mode, allows working with keys by manually holding them down for more flexible use of modifiers like Ctrl, Alt, etc.
        -   **One-Shot** -   Mode for single playback of a macro/key press.
        -   **Loop** -   Mode for continuous looped playback of a macro/frequent key pressing. It will not be turned off until the button/pad is pressed again.
        -   **Toggle** -   Mode for holding keys pressed until the pad is pressed again.
* **Keys:**
    * Click in the input field.
    * Enter the desired key combination (The recording format will look approximately like this: Key.ctrl + Key.shift + S) (A full list of key notations will be provided below).
    * **Or:** Select the required keys from the menu next to the button to the right of the input field. (When you click the buttons in the menu, they will be correctly recorded into the field, with "+" signs).
* **Mouse Actions:**
    * Select the mouse movement axis from the list (MOUSE_RELX (Horizontal movement) and MOUSE_RELY (Vertical movement)) and click to add it to the editor field.
    * In the field, you will see Key.mouse_x for MOUSE_RELX and Key.mouse_y for MOUSE_RELY.
    * After designating the movement axis, you must specify the movement itself {REL:number}. For example:
        ```
        Key.mouse_x{REL:100} + {WAIT:10.0} + Key.mouse_x{REL:-100}
        ```
        - This script first moves the mouse 100 pixels to the left, waits 10 seconds, and then moves it 100 pixels to the right.
    * The same syntax applies to any REL event, such as the mouse wheel.
* **Description:** A short name for display in the list.
* **Color:** Select the color number from the Launchpad palette.
* **[Save]**: Saves the change to config.json at path ~/.config/PadKeyMapper/config.json and instantly applies the changes.
* **[Cancel]**: Cancels the changes without writing them to config.json.

## 5. Key Notations
    ```markdown

    Keyboard

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
        Key.print_screen-       PRT SCR
        
    Numpad
        
        Key.num_lock    -       NUM LOCK
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
        
    Mouse Buttons and Actions
        
        Buttons
        
        Key.mouse_l     -       MOUSE_L (LEFT MB)
        Key.mouse_r     -       MOUSE_R (RIGHT MB)
        Key.mouse_m     -       MOUSE_M (MIDDLE MB)
        
        Axises (RELATIVE INPUTS)
        
        Key.mouse_x     -       MOUSE_RELX (Horizontal axis)
        Key.mouse_y     -       MOUSE_RELY (Vertical axis)
        Key.mouse_wh    -       MOUSE_WHEEL
    ```
