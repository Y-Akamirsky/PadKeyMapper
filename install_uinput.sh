#!/bin/bash

# Проверка на запуск от root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Пожалуйста, запустите скрипт с правами root (sudo)."
  exit 1
fi

echo "⚙️  Настройка прав для PadKey Mapper..."

# 1. Создаем группу uinput, если её нет
groupadd -f uinput

# 2. Определяем реального пользователя (того, кто вызвал sudo)
REAL_USER=${SUDO_USER:-$USER}

# 3. Добавляем пользователя в группу
if [ -n "$REAL_USER" ]; then
    usermod -aG uinput "$REAL_USER"
    echo "✅ Пользователь $REAL_USER добавлен в группу 'uinput'."
else
    echo "⚠️  Не удалось определить пользователя. Выполните вручную: sudo usermod -aG uinput \$USER"
fi

# 4. Создаем правило udev
RULE_FILE="/etc/udev/rules.d/99-padkey-mapper.rules"
echo 'KERNEL=="uinput", SUBSYSTEM=="misc", OPTIONS+="static_node=uinput", TAG+="uaccess", MODE="0660", GROUP="uinput"' > "$RULE_FILE"
echo "✅ Правило udev создано: $RULE_FILE"

# 5. Загружаем модуль ядра uinput (чтобы не требовалась перезагрузка ПК)
if ! lsmod | grep -q uinput; then
    modprobe uinput
    echo "✅ Модуль uinput загружен."
else
    echo "ℹ️  Модуль uinput уже активен."
fi

# 6. Перезагружаем правила udev
udevadm control --reload-rules
udevadm trigger

echo "--------------------------------------------------------"
echo "🎉 Готово! Права настроены."
echo "❗️ Для вступления изменений в силу может потребоваться"
echo "   выход из системы (Log Out) и повторный вход."
echo "--------------------------------------------------------"
