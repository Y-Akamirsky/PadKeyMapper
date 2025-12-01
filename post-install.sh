#!/bin/bash
# Скрипт, выполняемый после установки пакета padkey-mapper

# 1. Создание группы 'uinput', если она не существует
if ! getent group uinput > /dev/null; then
    groupadd uinput
    echo "Создана новая группа 'uinput'."
fi

# 2. Добавление текущего пользователя в группу 'uinput'
# $SUDO_USER - это пользователь, запустивший команду установки (например, dpkg -i или pacman)
if id -u $SUDO_USER > /dev/null 2>&1; then
    usermod -aG uinput $SUDO_USER
    echo "Пользователь $SUDO_USER добавлен в группу 'uinput'."
    echo "Для активации изменений пользователю необходимо перелогиниться."
fi

# 3. Применение правил udev
udevadm control --reload-rules
udevadm trigger
exit 0
