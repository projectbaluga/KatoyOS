#!/bin/bash -e
R="${ROOTFS_DIR}"
install -d "$R/usr/bin" "$R/usr/lib/katoyos" "$R/usr/share/applications" "$R/usr/share/polkit-1/actions" "$R/etc/polkit-1/rules.d" "$R/etc/xdg/autostart" "$R/etc/katoyos" "$R/etc/systemd/system"
install -m 755 files/katoy-welcome   "$R/usr/bin/katoy-welcome"
install -m 755 files/katoy-powerwatch "$R/usr/bin/katoy-powerwatch"
install -m 755 files/katoy-update    "$R/usr/bin/katoy-update"
install -m 755 files/katoy-expand-data "$R/usr/bin/katoy-expand-data"
install -m 755 files/katoy-karaoke   "$R/usr/bin/katoy-karaoke"
install -m 755 files/katoy-karaoke-launcher "$R/usr/bin/katoy-karaoke-launcher"
install -m 755 files/katoy-karaoke-session  "$R/usr/bin/katoy-karaoke-session"
install -m 755 files/katoy-helper    "$R/usr/lib/katoyos/helper"
install -m 644 files/os.katoy.helper.policy "$R/usr/share/polkit-1/actions/os.katoy.helper.policy"
install -m 644 files/10-udisks2-katoy.rules  "$R/etc/polkit-1/rules.d/10-udisks2-katoy.rules"
install -m 644 files/11-katoy-helper.rules  "$R/etc/polkit-1/rules.d/11-katoy-helper.rules"
install -m 644 files/katoy-welcome.desktop  "$R/usr/share/applications/katoy-welcome.desktop"
install -m 644 files/katoy-update.desktop   "$R/usr/share/applications/katoy-update.desktop"
install -m 644 files/katoy-karaoke.desktop  "$R/usr/share/applications/katoy-karaoke.desktop"
install -m 644 files/katoy-karaoke.conf     "$R/etc/katoyos/karaoke.conf"
install -m 644 files/katoy-karaoke.service  "$R/etc/systemd/system/katoy-karaoke.service"
install -m 644 files/katoy-expand-data.service "$R/etc/systemd/system/katoy-expand-data.service"
install -m 644 files/katoy-powerwatch.desktop "$R/etc/xdg/autostart/katoy-powerwatch.desktop"

if [ -d files/songs ] && [ "$(ls files/songs 2>/dev/null)" ]; then
	install -d "$R/usr/share/katoy/songs"
	cp -a files/songs/* "$R/usr/share/katoy/songs/"
fi

install -d "$R/etc/X11"
install -m 644 files/Xwrapper.config "$R/etc/X11/Xwrapper.config"

# ── Appliance (kiosk) boot: power on -> Plymouth splash -> karaoke player. No display manager, no desktop. ──
# Done with plain symlinks instead of `systemctl enable` so it also works (and is testable) outside a chroot.
if [ "${KATOY_KIOSK:-1}" = "1" ]; then
	KUSER="${FIRST_USER_NAME:-katoy}"
	sed -i "s/^User=.*/User=${KUSER}/" "$R/etc/systemd/system/katoy-karaoke.service"
	install -d "$R/etc/systemd/system/multi-user.target.wants"
	ln -sf /etc/systemd/system/katoy-expand-data.service "$R/etc/systemd/system/multi-user.target.wants/katoy-expand-data.service"
	ln -sf /etc/systemd/system/katoy-karaoke.service "$R/etc/systemd/system/multi-user.target.wants/katoy-karaoke.service"
	ln -sf /lib/systemd/system/multi-user.target "$R/etc/systemd/system/default.target"
	rm -f "$R/etc/systemd/system/display-manager.service"
	# Keep the user's systemd instance (PipeWire audio) alive independent of the tty1 session.
	install -d "$R/var/lib/systemd/linger"
	: > "$R/var/lib/systemd/linger/${KUSER}"
fi
