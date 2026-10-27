#!/bin/bash -e
R="${ROOTFS_DIR}"
install -d "$R/etc/xdg/lxqt" "$R/etc/xdg/pcmanfm-qt/lxqt" "$R/etc/lightdm/lightdm.conf.d" "$R/etc/gtk-3.0" "$R/etc/fonts/conf.d" "$R/etc/X11"
install -m 644 files/lxqt.conf              "$R/etc/xdg/lxqt/lxqt.conf"
install -m 644 files/session.conf           "$R/etc/xdg/lxqt/session.conf"
install -m 644 files/panel.conf             "$R/etc/xdg/lxqt/panel.conf"
install -m 644 files/pcmanfm-settings.conf  "$R/etc/xdg/pcmanfm-qt/lxqt/settings.conf"
install -m 644 files/50-katoy.conf          "$R/etc/lightdm/lightdm.conf.d/50-katoy.conf"
install -m 644 files/greeter.conf           "$R/etc/lightdm/lightdm-gtk-greeter.conf"
install -m 644 files/gtk-settings.ini       "$R/etc/gtk-3.0/settings.ini"
install -m 644 files/60-katoy-fonts.conf    "$R/etc/fonts/conf.d/60-katoy-fonts.conf"

# Boot straight into the desktop, logged in as the first user
cat >> "$R/etc/lightdm/lightdm.conf.d/50-katoy.conf" <<LDM
autologin-user=${FIRST_USER_NAME}
autologin-user-timeout=0
LDM

echo /usr/sbin/lightdm > "$R/etc/X11/default-display-manager"
on_chroot << 'CHEOF'
systemctl set-default graphical.target
systemctl enable lightdm
systemctl enable NetworkManager
CHEOF
