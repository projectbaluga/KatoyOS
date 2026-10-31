#!/bin/bash
# Dry-run harness for stage-katoy sub-stages
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

echo "=== Setting up fake rootfs in $WORK_DIR ==="
mkdir -p "$WORK_DIR/etc" "$WORK_DIR/boot/firmware"
touch "$WORK_DIR/etc/fstab"

cat > "$WORK_DIR/etc/os-release" <<'EOF'
PRETTY_NAME="Debian GNU/Linux trixie/sid"
NAME="Debian GNU/Linux"
VERSION_CODENAME=trixie
ID=debian
HOME_URL="https://www.debian.org/"
SUPPORT_URL="https://www.debian.org/support"
BUG_REPORT_URL="https://bugs.debian.org/"
EOF

cat > "$WORK_DIR/boot/firmware/config.txt" <<'EOF'
# Enable audio (loads snd_bcm2835)
dtparam=audio=on

# Automatically load initramfs files, if found
auto_initramfs=1

# Enable DRM VC4 V3D driver
dtoverlay=vc4-kms-v3d
max_framebuffers=2

# Don't have the firmware create an initial video= setting in cmdline.txt.
disable_fw_kms_setup=1

[cm4]
otg_mode=1

[cm5]
dtoverlay=dwc2,dr_mode=host

[pi5]
CONSOLE_UART=1

[all]
EOF

cat > "$WORK_DIR/boot/firmware/cmdline.txt" <<'EOF'
console=serial0,115200 console=tty1 root=ROOTDEV rootfstype=ext4 fsck.repair=yes rootwait
EOF

# Define stub on_chroot function and export required variables
on_chroot() {
    echo "[STUB on_chroot]"
    cat
}
export -f on_chroot

export ROOTFS_DIR="$WORK_DIR"
export FIRST_USER_NAME="katoy"
export KATOY_PRUNE_KERNELS=1
export KATOY_KIOSK=1

echo "=== Running sub-stages ==="
for stage in 01-branding 02-desktop 03-tools 04-pi3; do
    echo "Running $stage/00-run.sh..."
    (
        cd "$REPO_ROOT/stage-katoy/$stage"
        ./00-run.sh
    )
done

echo "=== Running Assertions ==="

# 1. Assert config.txt ends with [all] block and has single vc4-kms-v3d
CFG="$WORK_DIR/boot/firmware/config.txt"
VC4_COUNT=$(grep -c "dtoverlay=vc4-kms-v3d" "$CFG" || true)
if [ "$VC4_COUNT" -ne 1 ]; then
    echo "FAIL: Expected exactly 1 instance of vc4-kms-v3d in config.txt, found $VC4_COUNT"
    exit 1
fi

if ! sed -n '/^\[all\]/,$p' "$CFG" | grep -q "disable_splash=1"; then
    echo "FAIL: config.txt [all] block does not contain disable_splash=1"
    exit 1
fi

# 2. Assert cmdline.txt is still one line and keeps ROOTDEV
CMD="$WORK_DIR/boot/firmware/cmdline.txt"
LINE_COUNT=$(wc -l < "$CMD")
if [ "$LINE_COUNT" -ne 1 ]; then
    echo "FAIL: cmdline.txt must be exactly 1 line, found $LINE_COUNT"
    exit 1
fi

if ! grep -q "root=ROOTDEV" "$CMD"; then
    echo "FAIL: cmdline.txt lost ROOTDEV placeholder"
    exit 1
fi

if ! grep -q "quiet splash plymouth.ignore-serial-consoles" "$CMD"; then
    echo "FAIL: cmdline.txt missing quiet splash tokens"
    exit 1
fi

# 3. Assert os-release has ID=debian and KatoyOS branding
OS_REL="$WORK_DIR/etc/os-release"
if ! grep -q "^ID=debian" "$OS_REL"; then
    echo "FAIL: os-release missing ID=debian"
    exit 1
fi

if ! grep -q 'NAME="KatoyOS"' "$OS_REL"; then
    echo "FAIL: os-release missing NAME=\"KatoyOS\""
    exit 1
fi

# 4. Assert the karaoke appliance really starts at boot
SVC="$WORK_DIR/etc/systemd/system/katoy-karaoke.service"
[ -f "$SVC" ] || { echo "FAIL: katoy-karaoke.service not installed"; exit 1; }
[ -L "$WORK_DIR/etc/systemd/system/multi-user.target.wants/katoy-karaoke.service" ] || { echo "FAIL: katoy-karaoke.service is not enabled (no wants symlink)"; exit 1; }
[ "$(readlink "$WORK_DIR/etc/systemd/system/default.target")" = "/lib/systemd/system/multi-user.target" ] || { echo "FAIL: default.target is not multi-user.target"; exit 1; }
grep -q "^User=katoy" "$SVC" || { echo "FAIL: service User= not set to the first user"; exit 1; }
grep -q "^PAMName=login" "$SVC" || { echo "FAIL: service has no PAM session (no audio runtime dir)"; exit 1; }
if grep -E "^After=.*graphical\.target" "$SVC"; then
    echo "FAIL: service ordered After=graphical.target while WantedBy=multi-user.target (ordering cycle)"; exit 1
fi
grep -q "^ExecStart=/usr/bin/xinit" "$SVC" || { echo "FAIL: service ExecStart does not use xinit"; exit 1; }
[ -f "$WORK_DIR/var/lib/systemd/linger/katoy" ] || { echo "FAIL: linger not enabled for katoy"; exit 1; }
[ -x "$WORK_DIR/usr/bin/katoy-karaoke-launcher" ] || { echo "FAIL: launcher missing or not executable"; exit 1; }
grep -q "DISPLAY=" "$WORK_DIR/usr/bin/katoy-karaoke-launcher" || { echo "FAIL: launcher does not export DISPLAY"; exit 1; }
grep -q "xset q" "$WORK_DIR/usr/bin/katoy-karaoke-launcher" || { echo "FAIL: launcher missing xset q wait loop"; exit 1; }
[ -f "$WORK_DIR/etc/X11/Xwrapper.config" ] || { echo "FAIL: Xwrapper.config missing"; exit 1; }
grep -q "^needs_root_rights=yes" "$WORK_DIR/etc/X11/Xwrapper.config" || { echo "FAIL: Xwrapper.config needs_root_rights is not yes"; exit 1; }
[ -f "$WORK_DIR/var/lib/openbox/debian-menu.xml" ] || { echo "FAIL: debian-menu.xml missing"; exit 1; }
[ -f "$WORK_DIR/etc/wpa_supplicant/wpa_supplicant.conf" ] || { echo "FAIL: wpa_supplicant.conf missing"; exit 1; }
grep -q "country=PH" "$WORK_DIR/etc/wpa_supplicant/wpa_supplicant.conf" || { echo "FAIL: wpa_supplicant.conf missing country=PH"; exit 1; }
grep -q "^x11-utils" "$REPO_ROOT/stage-katoy/00-packages/00-packages-nr" || { echo "FAIL: x11-utils missing from package list"; exit 1; }
grep -q "^libxcb-cursor0" "$REPO_ROOT/stage-katoy/00-packages/00-packages-nr" || { echo "FAIL: libxcb-cursor0 missing from package list"; exit 1; }
grep -q "^xserver-xorg-legacy" "$REPO_ROOT/stage-katoy/00-packages/00-packages-nr" || { echo "FAIL: xserver-xorg-legacy missing from package list"; exit 1; }
grep -q "^x11-xserver-utils" "$REPO_ROOT/stage-katoy/00-packages/00-packages-nr" || { echo "FAIL: x11-xserver-utils missing from package list"; exit 1; }
grep -q "^KIOSK=1" "$WORK_DIR/etc/katoyos/karaoke.conf" || { echo "FAIL: karaoke.conf KIOSK is not 1"; exit 1; }

# 5. Assert installed tools and files exist with correct modes
[ -d "$WORK_DIR/media/katoy/KATOYDATA" ] || { echo "FAIL: KATOYDATA mountpoint missing"; exit 1; }
grep -q "LABEL=KATOYDATA /media/katoy/KATOYDATA vfat" "$WORK_DIR/etc/fstab" || { echo "FAIL: KATOYDATA fstab entry missing"; exit 1; }
! grep -q "init_resize.sh" "$CMD" || { echo "FAIL: init_resize.sh was not stripped from cmdline.txt"; exit 1; }
[ -x "$WORK_DIR/usr/bin/katoy-expand-data" ] || { echo "FAIL: katoy-expand-data missing or not executable"; exit 1; }
[ -f "$WORK_DIR/etc/systemd/system/katoy-expand-data.service" ] || { echo "FAIL: katoy-expand-data.service missing"; exit 1; }
[ -L "$WORK_DIR/etc/systemd/system/multi-user.target.wants/katoy-expand-data.service" ] || { echo "FAIL: katoy-expand-data.service not enabled"; exit 1; }
grep -q "^parted" "$REPO_ROOT/stage-katoy/00-packages/00-packages-nr" || { echo "FAIL: parted missing from package list"; exit 1; }
grep -q "^fatresize" "$REPO_ROOT/stage-katoy/00-packages/00-packages-nr" || { echo "FAIL: fatresize missing from package list"; exit 1; }
[ -x "$WORK_DIR/usr/bin/katoy-welcome" ] || { echo "FAIL: katoy-welcome missing or not executable"; exit 1; }
[ -x "$WORK_DIR/usr/bin/katoy-karaoke" ] || { echo "FAIL: katoy-karaoke missing or not executable"; exit 1; }
[ -x "$WORK_DIR/usr/lib/katoyos/helper" ] || { echo "FAIL: katoy-helper missing or not executable"; exit 1; }
[ -f "$WORK_DIR/etc/katoyos/karaoke.conf" ] || { echo "FAIL: karaoke.conf missing"; exit 1; }
[ -f "$WORK_DIR/usr/share/applications/katoy-karaoke.desktop" ] || { echo "FAIL: katoy-karaoke.desktop missing"; exit 1; }
[ -f "$WORK_DIR/usr/share/backgrounds/katoyos/default.png" ] || { echo "FAIL: wallpaper missing"; exit 1; }

echo "=== All test harness assertions PASSED successfully! ==="
