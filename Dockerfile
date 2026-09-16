FROM debian:trixie
RUN apt-get update && apt-get install -y --no-install-recommends \
    live-build debootstrap ca-certificates xorriso isolinux syslinux-common \
    grub-pc-bin grub-efi-amd64-bin mtools dosfstools squashfs-tools file rsync xz-utils zstd bzip2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY auto /build/auto
COPY config /build/config
COPY scripts /build/scripts
RUN test -s config/includes.chroot/opt/nora/llm/model.gguf
RUN chmod +x auto/config scripts/*.sh config/hooks/live/*.hook.*
CMD ["./scripts/build.sh"]
