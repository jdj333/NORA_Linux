#!/bin/bash
# Executed inside the ARM64 image, never on the host.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
[[ $(dpkg --print-architecture) == arm64 ]]
printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d
chmod 755 /usr/sbin/policy-rc.d
apt-get update
apt-get -o Dpkg::Options::=--force-confold install -y --no-install-recommends \
    xfce4 xfce4-terminal lightdm lightdm-gtk-greeter xserver-xorg \
    network-manager-gnome firefox-esr sudo locales dbus-x11 \
    adwaita-icon-theme gnome-themes-extra greybird-gtk-theme fonts-dejavu \
    curl ca-certificates python3 python3-pip python3-gi python3-cairo python3-gi-cairo \
    gir1.2-gtk-3.0 gir1.2-gstreamer-1.0 gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good gstreamer1.0-libav libportaudio2 libasound2-plugins \
    espeak-ng libgomp1 procps iproute2 pipewire-audio pavucontrol
python3 -m pip install --no-cache-dir --only-binary=:all: --require-hashes \
    --target /opt/nora/voice/python -r /opt/nora/voice/voice-requirements.txt
bash /tmp/nora-branding.sh
bash /tmp/nora-chat.sh
chmod 755 /usr/local/sbin/nora-first-boot
systemctl disable userconfig.service
systemctl enable nora-first-boot.service lightdm.service
systemctl set-default graphical.target
# Do not start a blank desktop if account setup fails.
mkdir -p /etc/systemd/system/lightdm.service.d
printf '[Unit]\nRequires=nora-first-boot.service\nAfter=nora-first-boot.service\n' \
    > /etc/systemd/system/lightdm.service.d/nora-setup.conf
printf 'nora\n' > /etc/hostname
sed -i 's/raspberrypi/nora/g' /etc/hosts
# Keep cloud-init support for Imager networking, but preserve NORA hostname.
cat > /etc/cloud/cloud.cfg.d/99-nora.cfg <<'CONFIG'
preserve_hostname: true
system_info:
  default_user:
    name: nora
    gecos: NORA User
CONFIG
# Python/native speech wheels need the supported 4K-page Pi kernel.
printf '\n[all]\n# NORA: 4K pages for native speech runtime compatibility\nkernel=kernel8.img\n' >> /boot/firmware/config.txt
# Use the four Pi cores conservatively; leave capacity for desktop and speech.
sed -i 's/--threads 2/--threads 3/; s/--threads-batch 2/--threads-batch 3/' /usr/local/bin/nora-llm
apt-get clean
rm -rf /var/lib/apt/lists/*
rm -f /usr/sbin/policy-rc.d /tmp/nora-branding.sh /tmp/nora-chat.sh
# These are generated uniquely on first boot, not shared across flashed cards.
rm -f /etc/ssh/ssh_host_*
truncate -s 0 /etc/machine-id
rm -f /var/lib/dbus/machine-id
ln -s /etc/machine-id /var/lib/dbus/machine-id
