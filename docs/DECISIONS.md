# KatoyOS Architectural and Design Decisions

This document records architectural, technical, and design choices made during the development of **KatoyOS** for Raspberry Pi 3 Model B.

---

## 1. Single Hardware Target: Raspberry Pi 3 Model B Only
- **Decision:** Target `kernel7.img` (Cortex-A53 32-bit `armhf`) exclusively.
- **Rationale:** Focusing strictly on Pi 3B eliminates unnecessary multi-architecture packages and kernels, reduces image footprint, and keeps memory usage well under the 400 MB idle target on 1 GB RAM hardware.
- **Kernel Pruning:** Unused Pi 1/Zero (`linux-image-rpi-v6`) and 64-bit (`linux-image-rpi-v8`) kernels are pruned during build if `apt-get -s purge` confirms no critical system dependencies are affected.

## 2. Desktop Architecture: LXQt + Openbox on X11
- **Decision:** Use LXQt with Openbox on X11 rather than Wayland/labwc.
- **Rationale:** LXQt + Openbox offers proven stability, lightweight memory usage, low GPU resource demands on Pi 3B's VC4 graphics, and reliable display management with LightDM.

## 3. First-Boot Zero-Config & Welcome Wizard (`katoy-welcome`)
- **Decision:** Boot automatically into LXQt with auto-login as `katoy`. Launch `katoy-welcome` on first desktop session.
- **Rationale:** Eliminates complex headless setup while guiding users to set timezone, Wi-Fi country, keyboard layout, and change default passwords securely via `katoy-helper` and `pkexec`.

## 4. Privilege Isolation (`/usr/lib/katoyos/helper` + Polkit)
- **Decision:** Implement a minimal, strictly validated bash helper script executed via Polkit (`os.katoy.helper.policy`).
- **Rationale:** Prevents running the entire Python/Qt GUI as root. The helper accepts specific parameters (timezone, wifi-country, keyboard, password) with strict regex and string validation, operating only on the calling user (`PKEXEC_UID`).

## 5. System Health Watchdog (`katoy-powerwatch`)
- **Decision:** Poll `/sys/devices/platform/soc/soc:firmware/get_throttled` (fallback `vcgencmd get_throttled`) every 30s.
- **Rationale:** Detects under-voltage (bit 0x1) and soft thermal limiting (bit 0x8) and triggers desktop notifications via `notify-send` on state transitions, protecting hardware without continuous CPU overhead.

## 6. SD Card Wear Reduction
- **Decision:** Configure systemd journald to `Storage=volatile` and `RuntimeMaxUse=32M`. Enable `rpi-swap` (zram swap).
- **Rationale:** Extends microSD card lifespan by keeping system logs in RAM and minimizing swap writes to physical flash memory.

## 7. Branding Asset Generation Pipeline
- **Decision:** Automate asset generation via `tools/make-assets.py` from `assets/katoyos-brand.png`.
- **Rationale:** Guarantees consistent image dimensions, aspect ratios, rounded corner masks, and background colors across Plymouth boot splash, desktop wallpaper, and panel/menu icon assets.

## 8. Root Filesystem Inode Density Tuning
- **Decision:** In `build.sh`, patch pi-gen's `export-image/prerun.sh` to call `mke2fs -q -i 8192 -t ext4` (1 inode per 8 KB instead of default 1 inode per 16 KB).
- **Rationale:** The full KatoyOS desktop userland contains a high count of small files (fonts, icons, themes, Python modules). Without custom inode ratio tuning (`-i 8192`), `mke2fs -d` exhausts inodes during filesystem creation (`__populate_fs: Could not allocate inode`).

## 9. Fullscreen MIDI/KAR Karaoke Player (`katoy-karaoke`) Architecture
- **Decision:** Implement `katoy-karaoke` as a lightweight standalone PyQt6 application. Keep rootfs minimal by installing only the player binary, config file, `fluidsynth`, and `python3-mido`. All song files (MIDI/`.kar`), SoundFonts (`.sf2`), background images, and the SQLite index reside on the external USB flash drive.
- **Rationale:** Eliminates SD-card write wear, minimizes image size (omitting ~140 MB SoundFont packages from rootfs), and optimizes performance on 1 GB RAM Raspberry Pi 3 Model B hardware.
- **Pinoy Karaoke Experience:** Implements authentic Pinoy videoke features including song reservation queueing (`R`), key transposition (-6 to +6 semi-tones), "NEXT UP" song ticker banners, and end-of-song scoring overlay (random fun score 85-100 with Tagalog praise texts like "MAGALING!" and "HATAW!").
- **SQLite Indexing:** Stores `.katoy-karaoke.db` directly on the USB drive so the index travels with the media. Only updates when file count/mtime changes or on manual rescan (F5), ensuring instant boot search performance across ~40,000 files.
- **Audio Output Driver:** Configured to `pulseaudio` by default in `/etc/katoyos/karaoke.conf`, which connects seamlessly to WirePlumber / PipeWire via the `pipewire-pulse` compatibility layer on KatoyOS.
- **Persistent Synth & Pause/Seek Mechanics:** `katoy-karaoke` uses a `ctypes` wrapper (`PersistentFluidSynth`) around `libfluidsynth.so.3` to keep SoundFonts loaded in RAM between songs. To pause playback without destroying the synth context, `PersistentFluidSynth.pause()` saves the current tick position (`get_current_tick()`), stops the player (`fluid_player_stop`), and silences held notes (`fluid_synth_all_notes_off`). Upon resuming, `fluid_player_play()` is called followed by `fluid_player_seek()` to restore the exact tick offset.
- **Microphone Chain & Audio Routing:** Microphone monitoring is managed via `MicrophoneChainManager` using PulseAudio/PipeWire `module-loopback` via `pactl`. Supports runtime volume adjustment, muting, and sink output selection.
- **Hardware Reverb Limitations on Pi 3B:** Software reverb filters (e.g. LADSPA plugins) incur significant CPU overhead on the Raspberry Pi 3B's Quad Cortex-A53 processor. Microphone monitoring is defaulted to dry low-latency loopback (`MIC_REVERB=0`) to ensure fluid MIDI synthesis and UI responsiveness.
- **Appliance Direct Boot & Package Slimming:** Removed LXQt desktop userland packages (`lxqt-*`, `lightdm`, `pcmanfm-qt`) in favor of direct xinit autostart (`katoy-karaoke.service`) and `udiskie` automount. Base development packages (`build-essential`, `gdb`, `manpages-dev`, `mkvtoolnix`) are purged during build (`KATOY_SLIM_IMAGE=1`), reducing image size while retaining `firmware-brcm80211`, `bluez-firmware`, `raspi-config`, and `cloud-init`.
- **Immutable OverlayFS Root & Update Reconciliation:** KatoyOS enables OverlayFS read-only root with RAM overlay (`KATOY_OVERLAYFS=1`) to protect microSD flash cards from corruption during sudden power cuts. `katoy-update` detects OverlayFS at runtime and provides an interactive maintenance mode toggle (`raspi-config nonint do_overlayfs 1`) allowing users to reboot into writable mode for persistent security updates.
- **Phone Web Remote & QR Code Generator:** `RemoteWebServer` runs an HTTP server on a background thread providing a mobile web app for searching, reserving, and controlling playback over LAN. QR codes are generated using the standard `python3-qrcode` library (`generate_qr_matrix`), with a lightweight pure-Python matrix generator as fallback, and displayed on the idle screen.
- **Real VAD Scoring & Cascading Config:** Implemented real voice-activity/energy coverage scoring (`calculate_real_score`) alongside optional fun random scoring. `load_config()` supports cascading overrides where a USB root `.katoy-karaoke.conf` takes precedence over `/etc/katoyos/karaoke.conf`.
- **NetworkManager AP Hotspot Onboarding & Systemd Boot Measurement:** Added `check_and_trigger_wifi_hotspot()` to check network status via `nmcli` and automatically start a setup AP hotspot (`KatoyOS-Karaoke`) if disconnected, allowing credentials to be applied via `katoy-helper`. App surfaces real `systemd-analyze` boot time on the library UI status bar.
