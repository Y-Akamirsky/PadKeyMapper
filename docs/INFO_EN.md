# ℹ️ Project Information (EN)

## Planned Features (TODO)
- [ ] Full macro support (sequence of keys with delays).
- [ ] Save/Load profiles to different files.
- [ ] "Toggle" mode (pressed - enabled, pressed - disabled).
- [ ] Add convenient color selection for different models (Legacy mode/RGB mode).
- [ ] Add the virtual Launchpad to the main window (left or right of all elements) and display added macros with colors on it.
- [ ] Add support for mouse actions.

## Known Issues
1. **Color specification field:** Limited selection for old and especially new Launchpad models. (I have an old Launchpad mini; colors and assignments for newer models may be broken).
2. **X11:** Not tested on X11 sessions. Please submit an issue if it works incorrectly or not at all. And please — attach logs.
3. **AppImage "fuse" error:** If AppImage does not start on new systems (Ubuntu 24.04), install `libfuse2`.

## Changelog

### v0.0.1 (Pre-Alpha)
- Initial version.
- Support for Note and CC messages.
- Visual mapping editor.
- Localization support (EN/RU).
- Basic Launchpad backlighting.
- Theme switch (Light/Dark).
- Show ID switch in the mapping editor.
