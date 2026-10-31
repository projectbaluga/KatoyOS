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
- **Immutable OverlayFS Root & Update Reconciliation:** KatoyOS enables OverlayFS read-only root with RAM overlay (`KATOY_OVERLAYFS=1`) to protect microSD flash cards from corruption during sudden power cuts. Under `overlayroot=tmpfs`, `systemd-remount-fs.service` (which attempts to remount `/` rw/ro based on `/etc/fstab`) and traditional disk-backed swap (`dphys-swapfile.service`) are meaningless and trigger systemd FAILED or dependency warnings on boot; these units are masked during the Pi 3 build stage to ensure clean boot logs. `katoy-update` detects OverlayFS at runtime and provides an interactive maintenance mode toggle (`raspi-config nonint do_overlayfs 1`) allowing users to reboot into writable mode for persistent security updates.
- **Phone Web Remote & QR Code Generator:** `RemoteWebServer` runs an HTTP server on a background thread providing a mobile web app for searching, reserving, and controlling playback over LAN. QR codes are generated using the standard `python3-qrcode` library (`generate_qr_matrix`), with a lightweight pure-Python matrix generator as fallback, and displayed on the idle screen.
- **Real VAD Scoring & Cascading Config:** Implemented real voice-activity/energy coverage scoring (`calculate_real_score`) alongside optional fun random scoring. `load_config()` supports cascading overrides where a USB root `.katoy-karaoke.conf` takes precedence over `/etc/katoyos/karaoke.conf`.
- **Headless Polkit Authorization & Web Wi-Fi Onboarding:** Added `11-katoy-helper.rules` polkit policy granting user `katoy` permission to execute `katoy-helper` without interactive GUI prompts in kiosk mode. Integrated mobile `/wifi` setup endpoint on `RemoteWebServer` to perform read-only SSID scans and receive submitted credentials. Updated `set-wifi-credentials` to bring down active AP hotspot connections prior to connecting as a client. Displayed configured hotspot password dynamically on the idle screen and targeted the idle QR code to `/wifi` in AP mode.
- **NetworkManager AP Hotspot Onboarding & Systemd Boot Measurement:** Added `check_and_trigger_wifi_hotspot()` to check network status via `nmcli` and automatically start a setup AP hotspot (`KatoyOS-Karaoke`) if disconnected. App surfaces real `systemd-analyze` boot time on the library UI status bar.
- **Wi-Fi Onboarding Hardening & Architectural Review Tradeoffs:**
  1. *Connect Result Persistence (`/wifi/status`):* `set-wifi-credentials` records connection outcome to `/tmp/katoy-wifi-status.json`. `RemoteRequestHandler` exposes GET `/wifi/status` allowing clients (who disconnect from AP mid-request) to poll connection status.
  2. *Unauthenticated Setup Page / PIN Scope:* `REMOTE_PIN` intentionally gates song reservation and player control endpoints (`/api/*`), while setup endpoints (`/wifi`, `/setup`) remain accessible without PIN when the unit is disconnected/in AP mode so first-time users scanning the idle screen QR code can configure network credentials without manual PIN setup.
  3. *Non-Destructive Hotspot Teardown & Re-Arming:* `nmcli connection down Hotspot` deactivates the AP interface without deleting the NetworkManager connection profile. On subsequent boots or connection drops, `check_and_trigger_wifi_hotspot()` re-arms the `KatoyOS-Karaoke` AP whenever `nmcli` general state is not connected.
  4. *Polkit Rule Scope (`os.katoy.helper`):* `11-katoy-helper.rules` targets the `os.katoy.helper` action rather than a sub-action ID because Polkit policy rules filter at the binary/action configuration level (`/usr/lib/katoyos/helper`), which enforces parameter sanitization in shell.

## 10. Hardware Verification Matrix & Real-Device Testing Status
- **x86 / Automated Test Verification (Passed in CI/Local):**
  - Unit tests in `tests/test_karaoke.py` and `tests/test_phase2.py` pass 100% on x86, covering filename parsing, lyric extraction, tempo/key transposition, stable song code mapping, tick-to-seconds elapsed time calculation, cascading config overrides, VAD scoring, QR matrix generation, `nmcli` WiFi list parsing, `systemd-analyze` parsing, and `/wifi` / `/setup` web server endpoints.
  - Sub-stage dry-run assertions (`tools/test-stage.sh`) pass 100%, verifying configuration file structures, policy files, and executable modes.
- **On-Hardware Physical Verification Status (Raspberry Pi 3 Model B):**
  - *Wi-Fi Onboarding:* AP hotspot creation (`KatoyOS-Karaoke`), mobile `/wifi` / `/setup` page serving, credential submission, and single-radio AP teardown prior to `nmcli device wifi connect` logic is implemented and unit-tested; pending physical Wi-Fi radio handoff confirmation on real Broadcom BCM43438 hardware.
  - *USB Automount (`udiskie`):* `udiskie -2 -s -f /media/katoy` configured with `10-udisks2-katoy.rules` and `11-katoy-helper.rules` for non-graphical kiosk hot-plugging of FAT32/exFAT/NTFS volumes; pending physical USB flash drive hot-plug/unplug verification during active playback on hardware.
  - *OverlayFS + `katoy-update`:* Read-only root overlay toggle (`raspi-config nonint do_overlayfs 1`) and updater flow implemented; pending physical power-cut persistence verification across reboot cycles.
  - *Boot Time Measurement:* `systemd-analyze` parsing logic integrated; pending real hardware boot measurement (target ~25s to kiosk display).

## 11. Boot straight into the karaoke player (systemd + xinit, no display manager)
- **Decision:** `katoy-karaoke.service` is enabled at build time via symlinks in `03-tools/00-run.sh` (so it is also verified by `tools/test-stage.sh`), `default.target` is `multi-user.target`, and LightDM/LXQt are not enabled (`KATOY_KIOSK=1`, default).
- **Why it previously did not start:** (1) the unit was installed but never enabled, while the build enabled `lightdm`, which is no longer installed; (2) the unit was `WantedBy=multi-user.target` yet `After=graphical.target`, an ordering cycle systemd breaks by dropping the job; (3) the app crashed during construction (`mic_manager` used before creation). `tests/test_ui_smoke.py` now builds the real window offscreen so (3) cannot regress, and `tools/test-stage.sh` asserts (1) and (2).
- **Session:** `PAMName=login` + `TTYPath=/dev/tty1` gives logind a session (so `/run/user/UID` exists for PipeWire and rootless X gets a VT); `loginctl enable-linger` is baked in so the user's PipeWire survives session restarts. `OnFailure=getty@tty1.service` returns a login prompt if the player crash-loops.
- **Early start, so nothing may assume the network or audio are ready:** the remote HTTP server binds `0.0.0.0` (previously the IP present at start, i.e. `127.0.0.1` at boot); a `NetworkWatcher` thread keeps the idle-screen QR/IP fresh and only raises the setup hotspot after the network has been down for `HOTSPOT_GRACE` seconds; PipeWire setup (`pactl`) is retried for ~60 s; slow probes (`systemd-analyze`) run off the UI thread.

## 12. "Neon Videoke" UI
- **Decision:** a QSS theme plus a few QPainter widgets (`LyricLineWidget`, delegates, `EqualizerWidget`, `ScoreCard`, vector icons) instead of QML/OpenGL/effects.
- **Rationale:** the Pi 3B has no spare GPU/CPU budget during FluidSynth playback. The full-screen backdrop and the outlined lyric text are rendered once into cached pixmaps and only blitted per frame; the karaoke wipe is a clipped blit at 20 fps. No emoji font is shipped, so all icons are drawn as vectors. Sizes scale with screen height (`S()`), so 720p panels work.
- **Phone remote:** same visual language, `/api/state` + pause, and reservations now go by song *code* (the file path always comes from the local index, never from the phone). `SongDatabase` is opened `check_same_thread=False` behind a lock because the remote queries from HTTP worker threads.
- **USB automount in the launcher:** `udiskie --automount --no-tray --no-notify --no-file-manager` (the earlier `-s -f /media/katoy` pulled in a tray and treated `/media/katoy` as the file-manager program). Mounts still land in `/media/katoy/<label>` thanks to `10-udisks2-katoy.rules`.
- **Setup endpoints and PIN:** `/wifi`, `/setup` and `/wifi/status` bypass `REMOTE_PIN` only while the unit is in hotspot mode (`net_ap`), matching section 10, item 2; the setup page polls `/wifi/status` after submitting.
