#!/bin/bash -e
# Nice-to-have packages: a missing one must not break the whole build.
on_chroot << 'CHEOF'
export DEBIAN_FRONTEND=noninteractive
for p in fonts-inter papirus-icon-theme falkon featherpad lximage-qt fluidsynth python3-mido; do
	apt-get install -y --no-install-recommends "$p" || echo "WARNING: optional package $p was not installed"
done
CHEOF
