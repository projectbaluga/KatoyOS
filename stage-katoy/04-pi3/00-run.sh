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
sed -i 's/ *$/ quiet splash plymouth.ignore-serial-consoles/' "$CMD"

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

# Pi 3B boots kernel7.img; the Pi 1/Zero (v6) and 64-bit (v8) kernels are dead weight here.
# Removal is skipped if apt would also remove anything that is not a kernel package.
if [ "${KATOY_PRUNE_KERNELS:-1}" = "1" ]; then
on_chroot << 'CHEOF'
pkgs=""
for p in linux-image-rpi-v6 linux-image-rpi-v8 linux-headers-rpi-v6 linux-headers-rpi-v8; do
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
