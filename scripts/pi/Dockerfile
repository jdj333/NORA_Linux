FROM debian:trixie
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl xz-utils util-linux fdisk parted e2fsprogs dosfstools \
    rsync python3 python3-pip file git cmake ninja-build g++ pkg-config \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /work
