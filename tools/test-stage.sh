#!/bin/bash
# Dry-run harness for stage-katoy sub-stages
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

echo "=== Setting up fake rootfs in $WORK_DIR ==="
mkdir -p "$WORK_DIR/etc" "$WORK_DIR/boot/firmware"

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

TAIL_LINE=$(tail -n 3 "$CFG" | grep "disable_splash=1" || true)
if [ -z "$TAIL_LINE" ]; then
    echo "FAIL: config.txt does not end with disable_splash=1 in [all] block"
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

# 4. Assert lightdm autologin file is correct
LDM_CONF="$WORK_DIR/etc/lightdm/lightdm.conf.d/50-katoy.conf"
if ! grep -q "autologin-user=katoy" "$LDM_CONF"; then
    echo "FAIL: LightDM autologin user katoy not set correctly"
    exit 1
fi

# 5. Assert installed tools and files exist with correct modes
[ -x "$WORK_DIR/usr/bin/katoy-welcome" ] || { echo "FAIL: katoy-welcome missing or not executable"; exit 1; }
[ -x "$WORK_DIR/usr/bin/katoy-karaoke" ] || { echo "FAIL: katoy-karaoke missing or not executable"; exit 1; }
[ -x "$WORK_DIR/usr/lib/katoyos/helper" ] || { echo "FAIL: katoy-helper missing or not executable"; exit 1; }
[ -f "$WORK_DIR/etc/katoyos/karaoke.conf" ] || { echo "FAIL: karaoke.conf missing"; exit 1; }
[ -f "$WORK_DIR/usr/share/applications/katoy-karaoke.desktop" ] || { echo "FAIL: katoy-karaoke.desktop missing"; exit 1; }
[ -f "$WORK_DIR/etc/xdg/autostart/katoy-karaoke.desktop" ] || { echo "FAIL: katoy-karaoke-autostart.desktop missing"; exit 1; }
[ -f "$WORK_DIR/usr/share/backgrounds/katoyos/default.png" ] || { echo "FAIL: wallpaper missing"; exit 1; }

echo "=== All test harness assertions PASSED successfully! ==="
