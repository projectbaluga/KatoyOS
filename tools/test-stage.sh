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

# Minimal stand-ins for files that earlier pi-gen stages and Debian packages provide
mkdir -p "$WORK_DIR/etc/xdg/openbox" "$WORK_DIR/usr/share/lxqt/themes/dark"
touch "$WORK_DIR/usr/share/lxqt/themes/dark/arrow-right.svg" "$WORK_DIR/usr/share/lxqt/themes/dark/preview.png"
cat > "$WORK_DIR/etc/xdg/openbox/rc.xml" <<'EOF'
<openbox_config>
<theme>
  <name>Clearlooks</name>
  <titleLayout>NLIMC</titleLayout>
  <font place="ActiveWindow">
    <name>sans</name>
    <size>8</size>
    <weight>bold</weight>
  </font>
</theme>
</openbox_config>
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

# 1. Assert config.txt replaces full-KMS with fake-KMS and includes forced HDMI settings
CFG="$WORK_DIR/boot/firmware/config.txt"
KMS_COUNT=$(grep -c "dtoverlay=vc4-kms-v3d" "$CFG" || true)
if [ "$KMS_COUNT" -ne 0 ]; then
    echo "FAIL: Expected 0 instances of vc4-kms-v3d in config.txt, found $KMS_COUNT"
    exit 1
fi

FKMS_COUNT=$(grep -c "dtoverlay=vc4-fkms-v3d" "$CFG" || true)
if [ "$FKMS_COUNT" -ne 1 ]; then
    echo "FAIL: Expected exactly 1 instance of vc4-fkms-v3d in config.txt, found $FKMS_COUNT"
    exit 1
fi

if ! grep -q "disable_splash=1" "$CFG"; then
    echo "FAIL: config.txt missing disable_splash=1"
    exit 1
fi

for hdmi_setting in "hdmi_force_hotplug=1" "hdmi_group=1" "hdmi_mode=16" "hdmi_drive=2"; do
    if ! grep -q "$hdmi_setting" "$CFG"; then
        echo "FAIL: config.txt missing $hdmi_setting"
        exit 1
    fi
done

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
[ -x "$WORK_DIR/usr/lib/katoyos/helper" ] || { echo "FAIL: katoy-helper missing or not executable"; exit 1; }
[ -f "$WORK_DIR/etc/xdg/autostart/katoy-noblank.desktop" ] || { echo "FAIL: katoy-noblank.desktop missing"; exit 1; }
[ -f "$WORK_DIR/usr/share/backgrounds/katoyos/default.png" ] || { echo "FAIL: wallpaper missing"; exit 1; }

# 6. Assert new runtime packages exist in package list
PKGS_FILE="$REPO_ROOT/stage-katoy/00-packages/00-packages-nr"
for pkg in "dbus-x11" "accountsservice" "x11-xserver-utils"; do
    if ! grep -q "^$pkg$" "$PKGS_FILE"; then
        echo "FAIL: Package $pkg missing from $PKGS_FILE"
        exit 1
    fi
done

# 7. Assert the Windows 11 theme pieces are installed and wired up
for f in usr/share/katoyos/win11/katoy-win11.qss \
         usr/share/themes/Katoy-Win11/openbox-3/themerc \
         usr/share/themes/Katoy-Win11/openbox-3/close.xbm \
         usr/share/lxqt/themes/katoy-win11/lxqt-panel.qss \
         usr/share/lxqt/themes/katoy-win11/lxqt-notificationd.qss \
         usr/share/lxqt/themes/katoy-win11/lxqt-runner.qss \
         usr/share/lxqt/themes/katoy-win11/arrow-right.svg; do
    [ -f "$WORK_DIR/$f" ] || { echo "FAIL: $f missing"; exit 1; }
done
[ ! -e "$WORK_DIR/usr/share/lxqt/themes/katoy-win11/preview.png" ] || { echo "FAIL: stale dark-theme preview copied"; exit 1; }

grep -q "^theme=katoy-win11" "$WORK_DIR/etc/xdg/lxqt/lxqt.conf" || { echo "FAIL: lxqt.conf does not select katoy-win11"; exit 1; }
grep -q "^panelSize=48" "$WORK_DIR/etc/xdg/lxqt/panel.conf" || { echo "FAIL: panel.conf is not 48px"; exit 1; }
grep -q "<name>Katoy-Win11</name>" "$WORK_DIR/etc/xdg/openbox/rc.xml" || { echo "FAIL: Openbox theme not selected in rc.xml"; exit 1; }
grep -q "DMZ-White" "$WORK_DIR/usr/share/icons/default/index.theme" || { echo "FAIL: default cursor theme not set"; exit 1; }

# Every plugin listed in panel.conf must have its own section
PANEL="$WORK_DIR/etc/xdg/lxqt/panel.conf"
for plugin in $(sed -n 's/^plugins=//p' "$PANEL" | tr -d ' ' | tr ',' ' '); do
    grep -q "^\\[$plugin\\]" "$PANEL" || { echo "FAIL: panel.conf lists $plugin but has no [$plugin] section"; exit 1; }
done

# Python tools must compile
python3 -m py_compile "$REPO_ROOT/stage-katoy/03-tools/files/katoy-welcome" "$REPO_ROOT/stage-katoy/03-tools/files/katoy-browser" \
    || { echo "FAIL: Python tools do not compile"; exit 1; }

echo "=== All test harness assertions PASSED successfully! ==="
