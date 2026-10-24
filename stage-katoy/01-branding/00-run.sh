#!/bin/bash -e
install -d "${ROOTFS_DIR}/usr/share/backgrounds/katoyos" \
           "${ROOTFS_DIR}/usr/share/plymouth/themes/katoyos" \
           "${ROOTFS_DIR}/usr/share/icons/hicolor/scalable/apps" \
           "${ROOTFS_DIR}/usr/share/pixmaps"
install -m 644 files/wallpaper.png     "${ROOTFS_DIR}/usr/share/backgrounds/katoyos/default.png"
install -d "${ROOTFS_DIR}/usr/share/icons/hicolor/256x256/apps" "${ROOTFS_DIR}/usr/share/icons/hicolor/64x64/apps"
install -m 644 files/katoyos-256.png   "${ROOTFS_DIR}/usr/share/icons/hicolor/256x256/apps/katoyos.png"
install -m 644 files/katoyos-64.png    "${ROOTFS_DIR}/usr/share/icons/hicolor/64x64/apps/katoyos.png"
install -m 644 files/katoyos-256.png   "${ROOTFS_DIR}/usr/share/pixmaps/katoyos.png"
install -m 644 files/plymouth-splash.png "${ROOTFS_DIR}/usr/share/plymouth/themes/katoyos/splash.png"
install -m 644 files/plymouth/katoyos.plymouth "${ROOTFS_DIR}/usr/share/plymouth/themes/katoyos/"
install -m 644 files/plymouth/katoyos.script   "${ROOTFS_DIR}/usr/share/plymouth/themes/katoyos/"

# Identity (ID/ID_LIKE stay "debian" so tooling keeps working)
sed -i 's/^NAME=.*/NAME="KatoyOS"/; s/^PRETTY_NAME=.*/PRETTY_NAME="KatoyOS 1.0 (Debian 13 base)"/' "${ROOTFS_DIR}/etc/os-release"
grep -q '^ID_LIKE=' "${ROOTFS_DIR}/etc/os-release" || echo 'ID_LIKE=debian' >> "${ROOTFS_DIR}/etc/os-release"
echo "KatoyOS 1.0" > "${ROOTFS_DIR}/etc/katoyos-release"
printf 'KatoyOS 1.0 \\n \\l\n\n' > "${ROOTFS_DIR}/etc/issue"
printf '\nWelcome to KatoyOS\n\n' > "${ROOTFS_DIR}/etc/motd"

# Boot splash theme (initramfs is rebuilt at the end of the pi-gen export step)
on_chroot << 'CHEOF'
plymouth-set-default-theme katoyos || echo "WARNING: could not set plymouth theme"
CHEOF
