# 🛠 PadKey Mapper Installation (EN)

## ⚠️ ATTENTION:
    * The program requires the `uinput` kernel module to be loaded to work!
        - To do this, you need to execute the following command in the terminal:
            ```bash
            sudo modprobe uinput
            ```
        - The program usually informs you if it cannot find the module. But if it doesn't, please try running this command first before submitting an Issue.

## Universal AppImage

For the program to work, it requires access to the kernel subsystem `uinput` (for keyboard emulation) and access to USB MIDI devices.

1. Download the latest `.AppImage` file from the [Releases](https://github.com/Y-Akamirsky/PadKeyMapper/releases) section.

    * *By default, Linux prohibits applications from creating virtual keyboards. We need to create a `udev` rule.*

2. Open the terminal and run the script to configure the udev rule from the remote repository:
    ```bash
    curl -sL https://raw.githubusercontent.com/Y-Akamirsky/PadKeyMapper/refs/heads/main/install_uinput.sh | bash
    ```
3. Reboot or log out and log back in to your session (session restart).
    * (If it does not start after setup and logging out/rebooting) Use the following commands to fix the permissions for the executable file:
    ```bash
    # Change the path to your actual package location!!!
    cd /directory/of/your/appimage/
    # Replace {version} with the actual package version!!!
    chmod +x PadKeyMapper-{version}-x86-64.AppImage
    cd
    ```
    * **ATTENTION:** Change the path in the commands to your actual package location and {version} to the actual package version!!!

## Native package for Arch Linux (.pkg.tar.zst)

There are two ways: Install a ready-made package from [releases](https://github.com/Y-Akamirsky/PadKeyMapper/releases) or build it from source.

* **Installation from** [releases](https://github.com/Y-Akamirsky/PadKeyMapper/releases)
    
    1. Download the latest release in `.pkg.tar.zst` format.
    2. Install the package using:
    ```bash
    # Replace the path with your actual path!!!
    sudo pacman -U /path/to/package/PackageName.pkg.tar.zst
    ```
    3. **IMPORTANT:** Add the user to the `uinput` group.
    ```bash
    sudo usermod -aG uinput $USER
    ```
    4. Reboot or log out and log back in to your session (session restart) for the udev changes to take effect.
    
* **Building from source** (for advanced users)
    
    1. Clone the repository.
    ```bash
    git clone https://github.com/Y-Akamirsky/PadKeyMapper
    ```
    2. Navigate to the `build_arch/` build directory.
    ```bash
    cd ~/PadKeyMapper/build_arch
    ```
    3. Start the build.
    ```bash
    makepkg -fsi
    # Flags:
    # (-f) Rebuilds the package even if it already exists.
    # (-s) Installs necessary dependencies.
    # (-i) Installs the package after building via sudo pacman -U.
    ```
    4. **IMPORTANT:** Add the user to the `uinput` group.
    ```bash
    sudo usermod -aG uinput $USER
    ```
    5. Reboot or log out and log back in to your session (session restart) for the udev changes to take effect.

## DONE!

Enjoy using it!
