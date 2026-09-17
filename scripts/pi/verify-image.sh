#!/bin/bash
# Run in the privileged Pi builder with the checkout mounted at /work.
set -euo pipefail
cd /work
image=${1:-/work/.build/pi/nora-pi.img}
[[ -f "$image" ]] || { echo 'A regular disk image file is required'; exit 1; }
loop=$(losetup --read-only --find --show --partscan "$image")
trap 'umount -R /mnt/check; losetup -d "$loop"' EXIT
for part in 1 2; do
 node="${loop}p$part"; numbers=$(cat /sys/class/block/$(basename "$node")/dev)
 [[ -b "$node" ]] || mknod "$node" b "${numbers%:*}" "${numbers#*:}"
done
mkdir -p /mnt/check
mount -o ro,noload "${loop}p2" /mnt/check
mount -o ro "${loop}p1" /mnt/check/boot/firmware
root_uuid=$(blkid -s PARTUUID -o value "${loop}p2")
boot_uuid=$(blkid -s PARTUUID -o value "${loop}p1")
grep -F "root=PARTUUID=$root_uuid " /mnt/check/boot/firmware/cmdline.txt
grep -F "PARTUUID=$root_uuid" /mnt/check/etc/fstab
grep -F "PARTUUID=$boot_uuid" /mnt/check/etc/fstab
cmp scripts/pi/first-boot.sh /mnt/check/usr/local/sbin/nora-first-boot
cmp scripts/pi/nora-first-boot.service /mnt/check/etc/systemd/system/nora-first-boot.service
grep -q 'name: nora' /mnt/check/etc/cloud/cloud.cfg.d/99-nora.cfg
test ! -s /mnt/check/etc/machine-id
test ! -e /mnt/check/var/lib/nora/setup-complete
cat /mnt/check/etc/xdg/autostart/nora-terminal.desktop
echo 'PASS: root/boot PARTUUID references match, first-boot scripts match source, unique machine identity pending'
