FROM debian:trixie
RUN apt-get update && apt-get install -y --no-install-recommends \
    live-build debootstrap ca-certificates xorriso isolinux syslinux-common \
    grub-pc-bin grub-efi-amd64-bin mtools dosfstools squashfs-tools file rsync xz-utils zstd bzip2 \
    python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY auto /build/auto
COPY config /build/config
COPY scripts /build/scripts
COPY music /build/music
RUN test -s config/includes.chroot/opt/nora/llm/model.gguf
RUN python3 scripts/prepare-voice.py --verify-only
RUN python3 -m pip install --no-cache-dir --only-binary=:all: --require-hashes \
    --target /build/config/includes.chroot/opt/nora/voice/python \
    -r scripts/voice-requirements.txt
RUN cp scripts/voice-requirements.txt config/includes.chroot/opt/nora/voice/
RUN chmod +x auto/config scripts/*.sh config/hooks/live/*.hook.*
CMD ["./scripts/build.sh"]
