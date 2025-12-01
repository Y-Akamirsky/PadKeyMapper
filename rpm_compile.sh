#!/bin/bash

# RPM FPM COMPILE

fpm -s dir -t rpm \
    --name padkey-mapper \
    --version 0.1.0 \
    --iteration 1 \
    --description "PadKey Mapper (PKM) - Launchpad to Keyboard Macro Utility" \
    --maintainer "Yaroslav Akamirsky <akamirsky.yaros@gmail.com>" \
    --url "https://github.com/Y-Akamirsky/Pad-Key-Mapper" \
    --after-install post-install.sh \
    --prefix /usr \
    dist/pkm-mapper=/usr/bin/pkm-mapper \
    99-pkm-uinput.rules=/etc/udev/rules.d/99-pkm-uinput.rules \
    config.json=/usr/share/pkm/config.json \
    config.json=/usr/share/pkm/config.json \
    layouts.json=/usr/share/pkm/layouts.json \
    localization.py=/usr/share/pkm/localization.py \
    constants.py=/usr/share/pkm/constants.py
