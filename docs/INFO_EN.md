# 🇬🇧 Project Information (EN)

## ⚠️ ATTENTION:
    Currently, there is full support only for devices of the Novation Launchpad family. For other devices, a "Universal" layout is available. And if you encounter difficulties with another device or wish to adapt the editor interface for it, please submit an "Issue" or a "Pull Request" (if you are a developer willing to contribute to the project)

## ✅ Planned Features (TODO)
- [x] Support for macros (key sequences with delays).
- [x] Saving/Loading profiles to different files.
- [x] "Toggle" mode (press once to turn on, press again to turn off).
- [ ] Add convenient color selection for different models (Legacy mode/RGB mode).
- [x] Add a virtual Launchpad to the main window (left or right of all elements) and display added macros on it using colors.
- [x] Add support for mouse actions.
- [ ] Create a more user-friendly syntax for writing complex macros.
- [ ] Add a convenient editor for complex macros (separate from the main field) for those who prefer less keyboard interaction :).
- [ ] Make it possible to export and import individual macros without binding them to the config for easy exchange between potential users.
- [ ] Add a subloop function to simplify repetitive actions that need to play for a certain amount of time, then stop and pass the action to the next action.
- [ ] Add a function for "Light show" (Not urgent at all, purely Fun mode).
- [ ] Add the ability to configure timeout for Loop and Toggle modes.
- [ ] **(BEFORE v1.0 RELEASE)** Port the interface to PyQT.

## 🚧 Known Issues
1. **Reassigning:** When reassigning an existing mapping without stopping the program, the physical device continues to light up the button/pad at the previous location. This can be fixed by returning the assignment to the previous location and reassigning it in a stopped state, or by reconnecting the device.
2. **X11:** Not tested on X11 session. Please open an issue if it works incorrectly or not at all. And please attach logs.
3. **AppImage "fuse" error:** If AppImage does not start on new systems (Ubuntu 24.04), install `libfuse2`.
4. **Cumbersome Script Syntax:** For complex and long macros, the resulting text string is long, making such macros easier to edit in the config file than in the GUI editor. This is also affected by the fact that the macro input line does not scale and does not have scrolling.

### Fixed:
1. **Color Input Field:** Limited selection for older and especially newer Launchpad models. (I have an old Launchpad mini, colors and assignments for newer models might be broken)

## 📜 Changelog

### v0.0.1.0 (Pre-Alpha)
- Initial version.
- Support for Note and CC messages.
- Visual mapping editor.
- Localization support (EN/RU).
- Basic Launchpad illumination.
- Theme switcher (Light/Dark)
- Show ID switcher in the mapping editor.

### v0.0.1.1b (Pre-Alpha)
- Support for mouse actions (buttons, movement axes, and scroll wheel axis).
- Various macro modes (CommonKB, One-shot, Loop, Toggle).
- Display of assigned pads in the main and editor windows.
- Feedback for active Loop/Toggle/One-Shot assignments via illumination blinking.
- Ability to enter a custom illumination value in the new input field.
- Significant refactoring of the logic in main.py
- Fixed minor bugs.
- Few visual improvements.
