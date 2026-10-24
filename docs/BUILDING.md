# Building KatoyOS

This document provides prerequisites, environment setup instructions, and troubleshooting tips for building **KatoyOS**.

---

## 1. Prerequisites

To build KatoyOS, your host system must have:
- **Operating System:** Linux (Debian, Ubuntu, Fedora, Arch, etc.) or **WSL2** (Windows Subsystem for Linux).
- **Disk Space:** At least **15 GB** free disk space.
- **Tools:** `git`, `docker`, `bash`, `python3`, `python3-pil` (Pillow).
- **Permissions:** Ability to run `docker` (user added to `docker` group or `sudo` access).

> **WSL2 Note:** If building under WSL2, **keep the repository inside the Linux root filesystem** (e.g. `/home/user/katoyos`), NOT under `/mnt/c/...`. File permissions and overlay mounts required by pi-gen Docker container will fail on NTFS mounts.

---

## 2. Building KatoyOS

1. **Clone the repository:**
   ```bash
   git clone https://github.com/katoyos/katoyos.git
   cd katoyos
   ```

2. **Run the asset generator (optional, assets pre-generated):**
   ```bash
   python3 tools/make-assets.py
   ```

3. **Execute the build script:**
   ```bash
   ./build.sh
   ```

4. **Locate the built image:**
   When complete, the flashable compressed image will be written to `./out/`:
   ```
   out/KatoyOS-*.img.xz
   ```

---

## 3. Flashing & First Boot

1. **Flash to microSD card:**
   Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/):
   - Click **Operating System** -> **Use custom** -> select `out/KatoyOS-*.img.xz`.
   - Select your microSD card and click **Write**.

2. **Boot Raspberry Pi 3 Model B:**
   - Insert microSD card into Pi 3B.
   - Connect HDMI, keyboard, mouse, and power supply (5V / 2.5A recommended).
   - KatoyOS will boot into Plymouth boot splash, then auto-login to LXQt desktop as user `katoy`.
   - The **KatoyOS Welcome** wizard will launch automatically.

---

## 4. Testing & Verification Tools

- **Run sub-stage dry-run harness:**
  ```bash
  ./tools/test-stage.sh
  ```
- **Syntax check shell scripts & Python tools:**
  ```bash
  bash -n stage-katoy/*/*.sh build.sh tools/*.sh
  python3 -m py_compile stage-katoy/03-tools/files/katoy-welcome tools/make-assets.py
  ```

---

## 5. Troubleshooting

- **Docker Permission Denied:**
  Ensure your user is in the `docker` group: `sudo usermod -aG docker $USER` and log back in.
- **Docker in Docker / cgroups errors:**
  Verify Docker daemon is running properly (`docker info`). On WSL2, ensure systemd is enabled in `/etc/wsl.conf`.
- **Package Download Failures:**
  Check `pi-gen/work/*/build.log` to identify failed network requests or outdated package repository mirrors.
