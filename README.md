# PadKey Mapper | PKM

![Version](https://img.shields.io/badge/version-Pre--Alpha_0.0.1.1b-blue) ![Platform](https://img.shields.io/badge/platform-Linux-green) ![License](https://img.shields.io/badge/license-GPL3-orange)

**PadKey Mapper** turns your MIDI device like Novation Launchpad into a powerful, customizable macro keyboard for Linux.

![Logo](icons/PKMICON.png)

Map any button on your MIDI device to keyboard shortcuts (Ctrl+C, Ctrl+V, etc), function keys (F1-F12), mouse actions, or macro-script using a modern, easy-to-use GUI.

![Main window Screenshot](docs/screenshots/main_edit_window_0011.png)
![Add key window Screenshot](docs/screenshots/add_key_window_0011.png)

## ✨ Features
- **Graphic Interface:** No config files editing needed—assign keys visually.
- **Visual Feedback:** Assigned pads light up.
- **Multiple Layouts:** Special support for Launchpad (Mini, MK2, X, and Pro models). For any other MIDI device use "Universal" layout.
- **Native Arch Linux package:** You can just install it with pacman -U! Or build from sources using PKGBUILD.
- **AppImage:** Runs on almost any Linux distribution.
- **Low Latency:** Uses native Linux `uinput` kernel module.
- !NEW! **Mouse Actions support:** Added mouse axises! X for horizontal, Y for vertical axises! And of course mouse wheel.

## 🚀 Quick Start

1. **Download** the latest PadKeyMapper `.AppImage` from Releases.
2. **Setup Permissions** (Required for uinput):
    ```bash
    curl -sL https://raw.githubusercontent.com/Y-Akamirsky/PadKeyMapper/refs/heads/main/install_uinput.sh | bash
    ```
    **Note:** Applying changes may require reboot/logout
3. If doesn't work **Run:**
    ```bash
    cd ~/directory/of/your/PadKeyMapper-{version}-x86-64.AppImage # Change to your actual directory and version!!!
    chmod +x PadKeyMapper-{version}-x86-64.AppImage # Change {version} to actual package version!!!
    cd
    sudo modprobe uinput
    ```

## 📚 Documentation
- 🇬🇧 **English:**
  - [Installation Guide](docs/INSTALL_EN.md)
  - [User Manual](docs/USAGE_EN.md)
  - [Changelog & Known Issues](docs/INFO_EN.md)

- 🇷🇺 **Русский:**
  - [Инструкция по установке](docs/INSTALL_RU.md)
  - [Руководство пользователя](docs/USAGE_RU.md)
  - [История изменений и ошибки](docs/INFO_RU.md)

## 🤝 Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## ➡️ Versioning

  M.m.P.p (v0.0.1.1)
  
  Major       - "M"
  Minor       - "m"
  Patch       - "P"
  minor-patch - "p"

## 🪜 Stage

  - [ ] Pre-Alpha   -   0.0.1.p       <--- Now here
  - [ ] Alpha       -   0.0.2.p
  - [ ] Beta        -   0.1.P.p
  - [ ] Release     -   M.m.P.p
  

## 🛠 Built With

    - Python 3

    - CustomTkinter

    - python-uinput

    - Mido / RtMidi
