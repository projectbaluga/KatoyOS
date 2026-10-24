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

cd pi-gen
./build-docker.sh
mkdir -p ../out && cp -v deploy/* ../out/
echo "Done. Image is in ./out  - flash it with Raspberry Pi Imager (Use custom)."
