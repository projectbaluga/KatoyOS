#!/bin/bash -e
R="${ROOTFS_DIR}"

# config.txt ends with [cm4]/[pi5] sections, so open [all] before adding our lines.
# (vc4-kms-v3d is already enabled by pi-gen.)
CFG="$R/boot/firmware/config.txt"
[ -f "$CFG" ] || CFG="$R/boot/config.txt"
# Pi 3B + Xorg (modesetting) + software rendering shows a blank screen after the splash with full KMS
# (vc4-kms-v3d). Fake KMS (vc4-fkms-v3d) keeps the firmware in charge of the display and works.
# Verified on a real Pi 3: switching this one line made the player UI appear.
if [ "${KATOY_FKMS:-1}" = "1" ]; then
	sed -i -E 's/^dtoverlay=vc4-kms-v3d/dtoverlay=vc4-fkms-v3d/' "$CFG"
fi

cat >> "$CFG" <<CF

[all]
# --- KatoyOS ---
disable_splash=1
disable_overscan=1
CF

# Quiet boot with the Plymouth splash
CMD="$R/boot/firmware/cmdline.txt"
[ -f "$CMD" ] || CMD="$R/boot/cmdline.txt"
# Strip any stock pi-gen first-boot init_resize.sh kernel argument to prevent p2 rootfs expansion from corrupting p3 KATOYDATA
sed -i -E 's/init=\/usr\/(lib|libexec)\/raspi-config\/init_resize\.sh//g' "$CMD"
# Trixie pi-gen uses a bare `resize` kernel arg + rpi-resize.service instead of init_resize.sh.
# Strip it too: growing p2 would collide with the KATOYDATA partition (p3) that follows it.
sed -i -E 's/ resize( |$)/\1/g' "$CMD"
sed -i 's/ *$/ quiet splash plymouth.ignore-serial-consoles loglevel=3 logo.nologo vt.global_cursor_default=0/' "$CMD"

# Disable stock rootfs resize services (resizing p2 rootfs would overlap/corrupt p3 KATOYDATA partition)
on_chroot << 'CHEOF'
for u in resize2fs_once.service raspi-config.service rpi-resize.service; do
	systemctl disable "$u" >/dev/null 2>&1 || true
	systemctl mask "$u" >/dev/null 2>&1 || true
done
CHEOF

# Mount dedicated FAT32 KATOYDATA partition for songs, SoundFonts, and backgrounds
install -d -m 0755 "$R/media/katoy/KATOYDATA"
if [ -f "$R/etc/fstab" ] && ! grep -q "KATOYDATA" "$R/etc/fstab"; then
	echo "LABEL=KATOYDATA /media/katoy/KATOYDATA vfat defaults,noatime,uid=1000,gid=1000,umask=022,nofail 0 0" >> "$R/etc/fstab"
fi

# Services a karaoke appliance never uses (shaves boot time and RAM)
on_chroot << 'CHEOF'
for u in ModemManager.service triggerhappy.service e2scrub_all.timer; do
	systemctl disable "$u" >/dev/null 2>&1 || true
done

# Ensure NetworkManager is the sole network manager; dhcpcd conflicts and marks wlan0 unmanaged
for u in dhcpcd.service dhcpcd5.service; do
	systemctl disable "$u" >/dev/null 2>&1 || true
	systemctl mask "$u" >/dev/null 2>&1 || true
done
systemctl enable NetworkManager.service || true

# Ensure wlan0 is managed by NetworkManager
if [ -f /etc/NetworkManager/NetworkManager.conf ]; then
	if grep -q "\[ifupdown\]" /etc/NetworkManager/NetworkManager.conf; then
		sed -i '/^\[ifupdown\]/,/^\[/ s/managed=false/managed=true/' /etc/NetworkManager/NetworkManager.conf
	fi
	sed -i '/unmanaged-devices=.*wlan0/d' /etc/NetworkManager/NetworkManager.conf
fi
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

# Configure Wi-Fi Regulatory Domain (Country) and Unblock Wi-Fi
# Must run before OverlayFS is enabled so /boot/firmware and wpa_supplicant configs persist
on_chroot << 'CHEOF'
if command -v raspi-config >/dev/null 2>&1; then
	DEBIAN_FRONTEND=noninteractive raspi-config nonint do_wifi_country PH || true
	DEBIAN_FRONTEND=noninteractive raspi-config nonint do_rfkill 0 || true
fi
if command -v rfkill >/dev/null 2>&1; then
	rfkill unblock wifi || true
fi
CHEOF

# Fallback: ensure country=PH in wpa_supplicant.conf
install -d "$R/etc/wpa_supplicant"
if [ ! -f "$R/etc/wpa_supplicant/wpa_supplicant.conf" ]; then
	cat > "$R/etc/wpa_supplicant/wpa_supplicant.conf" <<'EOF'
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=PH
EOF
elif ! grep -q "^country=" "$R/etc/wpa_supplicant/wpa_supplicant.conf"; then
	echo "country=PH" >> "$R/etc/wpa_supplicant/wpa_supplicant.conf"
fi

# Enable OverlayFS Read-Only Root with RAM Overlay for power-cut resilience
if [ "${KATOY_OVERLAYFS:-1}" = "1" ]; then
on_chroot << 'CHEOF'
if command -v raspi-config >/dev/null 2>&1; then
	DEBIAN_FRONTEND=noninteractive raspi-config nonint do_overlayfs 0 || true
fi
# Mask services that fail or produce cascade errors on read-only OverlayFS root
systemctl mask systemd-remount-fs.service >/dev/null 2>&1 || true
systemctl mask dphys-swapfile.service >/dev/null 2>&1 || true
CHEOF
fi

# Package Slimming Stage: Purge unneeded base image packages with dry-run protection
if [ "${KATOY_SLIM_IMAGE:-1}" = "1" ]; then
on_chroot << 'CHEOF'
export DEBIAN_FRONTEND=noninteractive
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
export DEBIAN_FRONTEND=noninteractive
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
export DEBIAN_FRONTEND=noninteractive
apt-get purge -y unattended-upgrades || true
# The appliance uses the fixed katoy account; remove Raspberry Pi's first-boot user setup prompt.
apt-get purge -y userconf-pi || true

# Nothing on this appliance may ever show the blue "Package configuration" screen.
# 1) debconf: never use a dialog frontend, never ask below "critical" priority.
echo 'debconf debconf/frontend select Noninteractive' | debconf-set-selections
echo 'debconf debconf/priority select critical' | debconf-set-selections
# 2) mask (not just disable) everything that can start apt/dpkg by itself.
systemctl mask apt-daily.service apt-daily-upgrade.service apt-daily.timer apt-daily-upgrade.timer \
	apt-listchanges.service apt-listchanges.timer packagekit.service packagekit-offline-update.service \
	man-db.timer userconfig.service rpi-user-configure.service userconf-pi.service \
	piwiz.service piwiz.socket rsyslog.service >/dev/null 2>&1 || true
# Persist the noninteractive frontend for login, SSH, and sudo-launched sessions.
touch /etc/environment
grep -qxF 'DEBIAN_FRONTEND=noninteractive' /etc/environment || \
	echo 'DEBIAN_FRONTEND=noninteractive' >> /etc/environment
mkdir -p /etc/apt/apt.conf.d
cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "0";
APT::Periodic::Unattended-Upgrade "0";
EOF
# 3) the image must not ship a half-configured package: that is what makes dpkg ask questions later.
dpkg --configure -a
bad=$(dpkg -l | awk 'NR>5 && $1 !~ /^(ii|rc|un)$/ {print $1, $2}')
if [ -n "$bad" ]; then
	echo "ERROR: packages not fully configured:"; echo "$bad"; exit 1
fi
if dpkg -s userconf-pi >/dev/null 2>&1; then
	echo "ERROR: userconf-pi is still installed; first-boot user setup can prompt."
	exit 1
fi
# Prefer the requested debconf-get-selections check; fall back to debconf's built-in query
# when debconf-utils (which provides debconf-get-selections) is not installed in the image.
if command -v debconf-get-selections >/dev/null 2>&1; then
	frontend=$(debconf-get-selections | awk '$1 == "debconf" && $2 == "debconf/frontend" { print $4; exit }')
else
	frontend=$(printf 'GET debconf/frontend\n' | debconf-communicate debconf | awk '$1 == "0" { $1=""; sub(/^[[:space:]]+/, ""); print; exit }')
fi
if [ "$frontend" != "Noninteractive" ]; then
	echo "ERROR: debconf frontend is not persistently set to Noninteractive (found: $frontend)."
	exit 1
fi
apt-get clean
CHEOF
