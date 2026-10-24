# KatoyOS

**Stable. Rapid. Resilient.** A light, modern desktop OS for the **Raspberry Pi 3 Model B**, built on Debian 13 (Raspberry Pi OS "trixie", 32-bit).

- **Desktop:** LXQt + Openbox on X11, dark theme, Papirus icons, Inter font
- **Boot:** KatoyOS oyster-and-pearl splash and wallpaper, auto-login straight to the desktop
- **First boot:** a Welcome wizard sets time zone, Wi-Fi country, keyboard and a new password
- **Pi 3B care:** power-supply and overheating warnings, RAM-only logs, zram swap (from Raspberry Pi's `rpi-swap`), unused Pi 1/Zero and 64-bit kernels removed
- **Apps:** file manager, terminal, Falkon browser, text editor, image viewer, audio mixer, `KatoyOS Update`

## Build
Needs Linux or WSL2, Docker, git and about 15 GB free.

    ./build.sh

The image lands in `out/` (`.img.xz`). Flash it with Raspberry Pi Imager -> "Use custom".
A GitHub Actions workflow is included (`.github/workflows/build.yml`); run it manually or push a `v*` tag.

Default login: user `katoy`, password `changeme`. The Welcome app prompts to change it.

## Layout
    config                  pi-gen settings (name, user, locale, stages)
    build.sh                clones pi-gen at a pinned tag, injects stage-katoy, builds
    stage-katoy/
      00-packages/          package list (+ optional extras installed best-effort)
      01-branding/          wallpaper, logo, os-release, Plymouth theme
      02-desktop/           LXQt, panel, LightDM, fonts, dark GTK defaults
      03-tools/             katoy-welcome, katoy-helper (polkit), powerwatch, update
      04-pi3/               config.txt, cmdline, journald, kernel pruning

## Customize
- Change the look: edit files in `02-desktop/files/` (panel layout is `panel.conf`).
- Add apps: add package names to `00-packages/00-packages-nr`.
- Replace art: swap `01-branding/files/wallpaper.png` and the logos.
- Keep all kernels: set `KATOY_PRUNE_KERNELS=0` in `config`.

## Status
The scripts were syntax-checked, dry-run against a fake root filesystem, and the Welcome app was launched
headlessly. A full image build and boot on real hardware has **not** been done yet. Expect a round or two
of fixes on the first build (most likely a package name or the Plymouth splash). Check `pi-gen/work/*/build.log`.
