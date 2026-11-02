#!/bin/bash -e
R="${ROOTFS_DIR}"
install -d "$R/etc/xdg/lxqt" "$R/etc/xdg/pcmanfm-qt/lxqt" "$R/etc/lightdm/lightdm.conf.d" "$R/etc/gtk-3.0" "$R/etc/fonts/conf.d" "$R/etc/X11" \
           "$R/usr/share/icons/default"
install -m 644 files/lxqt.conf              "$R/etc/xdg/lxqt/lxqt.conf"
install -m 644 files/session.conf           "$R/etc/xdg/lxqt/session.conf"
install -m 644 files/panel.conf             "$R/etc/xdg/lxqt/panel.conf"
install -m 644 files/pcmanfm-settings.conf  "$R/etc/xdg/pcmanfm-qt/lxqt/settings.conf"
install -m 644 files/50-katoy.conf          "$R/etc/lightdm/lightdm.conf.d/50-katoy.conf"
install -m 644 files/greeter.conf           "$R/etc/lightdm/lightdm-gtk-greeter.conf"
install -m 644 files/gtk-settings.ini       "$R/etc/gtk-3.0/settings.ini"
install -m 644 files/60-katoy-fonts.conf    "$R/etc/fonts/conf.d/60-katoy-fonts.conf"

# Windows 11 style LXQt theme. Start from the stock "dark" theme so its SVG
# assets (menu arrows, check marks, ...) are reused, then replace the stylesheets.
THEMES="$R/usr/share/lxqt/themes"
rm -rf "$THEMES/katoy-win11"
if [ -d "$THEMES/dark" ]; then
	cp -a "$THEMES/dark" "$THEMES/katoy-win11"
	rm -f "$THEMES/katoy-win11/preview.png"
else
	install -d "$THEMES/katoy-win11"
fi
install -m 644 files/lxqt-theme/*.qss files/lxqt-theme/wallpaper.cfg "$THEMES/katoy-win11/"

# Windows 11 style window decorations for Openbox (flat titlebars, red close button)
OB="$R/usr/share/themes/Katoy-Win11/openbox-3"
install -d "$OB"
install -m 644 files/openbox-theme/themerc files/openbox-theme/*.xbm "$OB/"
RC="$R/etc/xdg/openbox/rc.xml"
if [ -f "$RC" ]; then
	sed -i '/<theme>/,/<\/theme>/{
		s|<name>Clearlooks</name>|<name>Katoy-Win11</name>|
		s|<name>sans</name>|<name>Inter</name>|
		s|<size>8</size>|<size>10</size>|
		s|<weight>bold</weight>|<weight>normal</weight>|
	}' "$RC"
	grep -q '<name>Katoy-Win11</name>' "$RC" || echo "WARNING: could not set the Openbox theme in rc.xml"
fi

# White arrow cursor, close to the Windows one (package dmz-cursor-theme)
printf '[Icon Theme]\nInherits=DMZ-White\n' > "$R/usr/share/icons/default/index.theme"

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
