#!/bin/bash -e
R="${ROOTFS_DIR}"

# config.txt ends with [cm4]/[pi5] sections, so open [all] before adding our lines.
# (vc4-kms-v3d is already enabled by pi-gen.)
CFG="$R/boot/firmware/config.txt"
[ -f "$CFG" ] || CFG="$R/boot/config.txt"
cat >> "$CFG" <<CF

[all]
# --- KatoyOS ---
disable_splash=1
hdmi_force_hotplug=1
hdmi_drive=2
hdmi_group=1
hdmi_mode=16
disable_overscan=1
CF

# Quiet boot with the Plymouth splash
CMD="$R/boot/firmware/cmdline.txt"
[ -f "$CMD" ] || CMD="$R/boot/cmdline.txt"
sed -i 's/ *$/ quiet splash plymouth.ignore-serial-consoles loglevel=3 logo.nologo vt.global_cursor_default=0/' "$CMD"

# Services a karaoke appliance never uses (shaves boot time and RAM)
on_chroot << 'CHEOF'
for u in ModemManager.service triggerhappy.service e2scrub_all.timer; do
	systemctl disable "$u" >/dev/null 2>&1 || true
done
CHEOF

# Keep the journal in RAM to spare the SD card
install -d "$R/etc/systemd/journald.conf.d"
cat > "$R/etc/systemd/journald.conf.d/katoy.conf" <<JD
[Journal]
Storage=volatile
RuntimeMaxUse=32M
JD

# Enable Systemd Hardware Watchdog
install -d "$R/etc/systemd/system.conf.d"
cat > "$R/etc/systemd/system.conf.d/watchdog.conf" <<WD
[Manager]
RuntimeWatchdogSec=15s
WD

# Enable OverlayFS Read-Only Root with RAM Overlay for power-cut resilience
if [ "${KATOY_OVERLAYFS:-1}" = "1" ]; then
on_chroot << 'CHEOF'
if command -v raspi-config >/dev/null 2>&1; then
	raspi-config nonint do_overlayfs 0 || true
fi
CHEOF
fi

# Package Slimming Stage: Purge unneeded base image packages with dry-run protection
if [ "${KATOY_SLIM_IMAGE:-1}" = "1" ]; then
on_chroot << 'CHEOF'
slim_pkgs="build-essential gdb manpages-dev man-db mkvtoolnix v4l-utils rpicam-apps-lite p7zip-full libmtp-runtime lua5.1 luajit"
purge_list=""
for p in $slim_pkgs; do
	dpkg -s "$p" >/dev/null 2>&1 && purge_list="$purge_list $p"
done
if [ -n "$purge_list" ]; then
	# Dry-run guard: verify apt simulation does not remove essential packages outside slim_pkgs
	extra=$(apt-get -s purge $purge_list | awk '/^Remv/{print $2}' | grep -vE '^(build-essential|gdb|manpages-dev|man-db|mkvtoolnix|v4l-utils|rpicam-apps-lite|p7zip-full|libmtp-runtime|lua5\.1|luajit)$' || true)
	if [ -z "$extra" ]; then
		echo "Purging unneeded base packages for appliance slimming: $purge_list"
		apt-get purge -y $purge_list
	else
		echo "Skipping package slimming; apt dry-run would also remove collateral: $extra"
	fi
fi
CHEOF
fi

# Pi 3B boots kernel7.img; non-v7 kernels (v6, v7l, v8, 2712) and matching headers are dead weight here.
# Removal is skipped if apt would also remove anything that is not a kernel package.
if [ "${KATOY_PRUNE_KERNELS:-1}" = "1" ]; then
on_chroot << 'CHEOF'
pkgs=""
for p in linux-image-rpi-v6 linux-image-rpi-v7l linux-image-rpi-v8 linux-image-rpi-2712 linux-headers-rpi-v6 linux-headers-rpi-v7l linux-headers-rpi-v8 linux-headers-rpi-2712; do
	dpkg -s "$p" >/dev/null 2>&1 && pkgs="$pkgs $p"
done
if [ -n "$pkgs" ]; then
	extra=$(apt-get -s purge $pkgs | awk '/^Remv/{print $2}' | grep -Ev '^linux-(image|headers)' || true)
	if [ -z "$extra" ]; then
		apt-get purge -y $pkgs
	else
		echo "Skipping kernel pruning; apt would also remove: $extra"
	fi
fi
CHEOF
fi

on_chroot << 'CHEOF'
apt-get clean
CHEOF
