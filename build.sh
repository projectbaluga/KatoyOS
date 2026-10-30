#!/bin/bash
# Build KatoyOS. Needs Linux (or WSL2), Docker, git, and ~15 GB free disk.
set -euo pipefail
cd "$(dirname "$0")"
PI_GEN_REF="${PI_GEN_REF:-2026-10-06-raspios-trixie-armhf}"

command -v docker >/dev/null || { echo "Docker is required."; exit 1; }
if [ ! -d pi-gen ]; then
	git clone --depth 1 --branch "$PI_GEN_REF" https://github.com/RPi-Distro/pi-gen.git
fi

rm -rf pi-gen/stage-katoy
cp -r stage-katoy pi-gen/stage-katoy
find pi-gen/stage-katoy -name '*.sh' -exec chmod +x {} +
cp config pi-gen/config

mkdir -p pi-gen/stage2
touch pi-gen/stage2/SKIP_IMAGES      # don't also export a stock "Lite" image

# Patch pi-gen mke2fs inode ratio and ROOT_MARGIN to prevent "Could not allocate inode" and "No space left on device" during export-image
sed -i 's/mke2fs -q -t ext4/mke2fs -q -i 8192 -t ext4/g' pi-gen/export-image/prerun.sh
sed -i 's/200 \* 1024 \* 1024/1024 \* 1024 \* 1024/g' pi-gen/export-image/prerun.sh
sed -i 's/\$ROOT_SIZE \* 0.2/\$ROOT_SIZE \* 0.5/g' pi-gen/export-image/prerun.sh

# Patch pi-gen export-image/prerun.sh to add third FAT32 partition labeled KATOYDATA
if ! grep -q "DATA_SIZE" pi-gen/export-image/prerun.sh; then
	sed -i '/ROOT_MARGIN=/a DATA_SIZE="$((1024 * 1024 * 1024))"' pi-gen/export-image/prerun.sh
	sed -i '/ROOT_PART_SIZE=/a DATA_PART_START=$((ROOT_PART_START + ROOT_PART_SIZE))\nDATA_PART_SIZE=$(((DATA_SIZE + ALIGN - 1) / ALIGN * ALIGN))' pi-gen/export-image/prerun.sh
	sed -i 's/IMG_SIZE=$((BOOT_PART_START + BOOT_PART_SIZE + ROOT_PART_SIZE))/IMG_SIZE=$((BOOT_PART_START + BOOT_PART_SIZE + ROOT_PART_SIZE + DATA_PART_SIZE))/g' pi-gen/export-image/prerun.sh
	sed -i '/mkpart primary ext4/a parted --script "${IMG_FILE}" unit B mkpart primary fat32 "${DATA_PART_START}" "$((DATA_PART_START + DATA_PART_SIZE - 1))"' pi-gen/export-image/prerun.sh
	sed -i '/ROOT_DEV=/a DATA_DEV="${LOOP_DEV}p3"' pi-gen/export-image/prerun.sh
	sed -i '/mkdosfs -n bootfs/a mkdosfs -n KATOYDATA -F 32 -s 1 -v "$DATA_DEV" > /dev/null\nDATA_STAGING="${STAGE_WORK_DIR}/data-staging"\nmkdir -p "${DATA_STAGING}/songs" "${DATA_STAGING}/soundfonts" "${DATA_STAGING}/backgrounds"\ncat > "${DATA_STAGING}/README.txt" << "DATADOC"\nKatoyOS KaraOkePi Data Drive (KATOYDATA)\n\nYou can copy songs (.mid / .kar), soundfonts (.sf2), and background wallpapers\ndirectly onto this partition from Windows, Mac, or Linux.\n\nFoldering suggestions:\n  - /songs/        : Put MIDI / KAR karaoke files here\n  - /soundfonts/   : Custom SoundFont (.sf2) files\n  - /backgrounds/  : Custom background images (.png / .jpg)\nDATADOC\nDATA_MOUNT="${STAGE_WORK_DIR}/data-mount"\nmkdir -p "${DATA_MOUNT}"\nmount -v "$DATA_DEV" "${DATA_MOUNT}" -t vfat\ncp -rp "${DATA_STAGING}/"* "${DATA_MOUNT}/"\numount "${DATA_MOUNT}"\nrm -rf "${DATA_STAGING}" "${DATA_MOUNT}"' pi-gen/export-image/prerun.sh
fi

cd pi-gen
./build-docker.sh
mkdir -p ../out && cp -v deploy/* ../out/
echo "Done. Image is in ./out  - flash it with Raspberry Pi Imager (Use custom)."
