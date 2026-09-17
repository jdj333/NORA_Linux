#!/bin/bash
# Run only inside scripts/pi/Dockerfile, with --privileged and /work mounted.
set -euo pipefail
cd /work
[[ $(uname -m) == aarch64 && $EUID == 0 ]] || { echo 'Native ARM64 Linux root required'; exit 1; }
mkdir -p .build/pi
exec 9>.build/pi/build.lock
flock -n 9 || { echo 'Another Pi build is running in this checkout'; exit 1; }
python3 scripts/pi/prepare.py
python3 scripts/prepare-voice.py --verify-only
mkdir -p dist/pi
rm -f dist/pi/SHA256SUMS
image=/work/.build/pi/nora-pi.img
mountpoint=/mnt/nora-pi
loop=''
cleanup() {
    if mountpoint -q "$mountpoint"; then umount -R "$mountpoint"; fi
    if [[ -n "$loop" ]]; then losetup -d "$loop"; fi
}
trap cleanup EXIT
xz -dc .build/pi/base.img.xz > "$image"
truncate -s 10G "$image"
parted -s "$image" resizepart 2 100%
loop=$(losetup --find --show --partscan "$image")
# Containers may expose sysfs partition metadata without creating /dev nodes.
for part in 1 2; do
    node="${loop}p$part"
    for attempt in {1..20}; do [[ -f /sys/class/block/$(basename "$node")/dev ]] && break; sleep .1; done
    if [[ ! -b "$node" ]]; then
        numbers=$(cat "/sys/class/block/$(basename "$node")/dev")
        mknod "$node" b "${numbers%:*}" "${numbers#*:}"
    fi
done
e2fsck -pf "${loop}p2" || [[ $? == 1 ]]
resize2fs "${loop}p2"
mkdir -p "$mountpoint"
mount "${loop}p2" "$mountpoint"
mount "${loop}p1" "$mountpoint/boot/firmware"
mount --rbind /dev "$mountpoint/dev"
mount --make-rslave "$mountpoint/dev"
mount -t proc proc "$mountpoint/proc"
mount -t sysfs sysfs "$mountpoint/sys"
cp -L "$mountpoint/etc/resolv.conf" .build/pi/resolv.conf.original
rm "$mountpoint/etc/resolv.conf"
cp /etc/resolv.conf "$mountpoint/etc/resolv.conf"
# Explicitly exclude all generated architecture-specific overlays.
rsync -a --chown=0:0 --exclude=/opt/nora/llm --exclude=/opt/nora/voice \
    --exclude=/etc/live config/includes.chroot/ "$mountpoint/"
mkdir -p "$mountpoint/opt/nora/llm" "$mountpoint/opt/nora/voice"
rsync -a --chown=0:0 --exclude=python config/includes.chroot/opt/nora/voice/ "$mountpoint/opt/nora/voice/"
tar -xzf .build/pi/llama-arm64.tar.gz -C "$mountpoint/opt/nora/llm" --strip-components=1
cp .build/chat/model.gguf "$mountpoint/opt/nora/llm/model.gguf"
cp .build/chat/model-LICENSE "$mountpoint/opt/nora/llm/MODEL-LICENSE"
cp scripts/pi/assets.json "$mountpoint/usr/share/nora/pi-assets.json"
cp .build/pi/llm-provenance.json "$mountpoint/opt/nora/llm/provenance.json"
install -Dm644 music/NoraLinuxStartupSong.mp3 "$mountpoint/usr/share/nora/music/NoraLinuxStartupSong.mp3"
install -Dm755 scripts/pi/first-boot.sh "$mountpoint/usr/local/sbin/nora-first-boot"
cp scripts/pi/nora-first-boot.service "$mountpoint/etc/systemd/system/"
cp config/hooks/live/0900-nora.hook.chroot "$mountpoint/tmp/nora-branding.sh"
cp config/hooks/live/0910-nora-chat.hook.chroot "$mountpoint/tmp/nora-chat.sh"
chroot "$mountpoint" /bin/bash < scripts/pi/customize.sh
cp scripts/pi/verify-runtime.py "$mountpoint/tmp/nora-verify-runtime.py"
cp scripts/verify-voice.py "$mountpoint/tmp/nora-verify-voice.py"
chroot "$mountpoint" /bin/bash < scripts/pi/verify.sh | tee dist/pi/verification.txt
cp "$mountpoint/usr/share/nora/build-packages.txt" dist/pi/build-packages.txt
# Restore a conventional NetworkManager-managed DNS file, not the build host's DNS.
cp .build/pi/resolv.conf.original "$mountpoint/etc/resolv.conf"
sync
umount -R "$mountpoint"
e2fsck -fn "${loop}p2"
fsck.fat -n "${loop}p1"
cleanup
loop=''
echo 'Compressing Raspberry Pi image…'
xz -T2 -3 -c "$image" > dist/pi/nora-linux-13-raspberry-pi5-arm64.img.xz.partial
mv dist/pi/nora-linux-13-raspberry-pi5-arm64.img.xz{.partial,}
cp scripts/pi/assets.json dist/pi/base-assets.json
(cd dist/pi && sha256sum nora-linux-13-raspberry-pi5-arm64.img.xz > SHA256SUMS)
echo 'Pi image complete. Physical Raspberry Pi boot/audio testing still required.'
