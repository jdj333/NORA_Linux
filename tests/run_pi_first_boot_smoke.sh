#!/bin/bash
# Run only in a disposable scripts/pi/Dockerfile container. No real audio/TTY needed.
set -euo pipefail
[[ -f /.dockerenv && $EUID == 0 ]] || { echo 'Disposable root Docker container required'; exit 1; }
! getent passwd 1000 >/dev/null || { echo 'Expected an empty build container'; exit 1; }
for group in adm sudo audio video render input plugdev netdev; do
 getent group "$group" >/dev/null || groupadd "$group"
done
mkdir -p /tmp/test-bin /etc/sudoers.d
printf '#!/bin/sh\nexit 0\n' > /tmp/test-bin/chvt
cp /tmp/test-bin/chvt /tmp/test-bin/clear
chmod +x /tmp/test-bin/*
# Console switching alone is stubbed; user creation, passwd and groups are real.
printf 'nora ALL=(ALL) NOPASSWD:ALL\n' > /etc/sudoers.d/010_pi-nopasswd
printf 'NoraTestFixture123!\nNoraTestFixture123!\n' | PATH="/tmp/test-bin:$PATH" bash /work/scripts/pi/first-boot.sh
[[ $(passwd -S nora | awk '{print $2}') == P ]]
grep -q '^autologin-user=nora$' /etc/lightdm/lightdm.conf.d/95-nora-user.conf
test -f /var/lib/nora/setup-complete
! grep -q NOPASSWD /etc/sudoers.d/010_pi-nopasswd
id -nG nora | grep -q sudo
# A configured account must not prompt or change its password on another call.
before=$(getent shadow nora | cut -d: -f2)
bash /work/scripts/pi/first-boot.sh </dev/null
[[ $(getent shadow nora | cut -d: -f2) == "$before" ]]
echo 'PASS: new-account password setup, sudo groups, autologin, and configured-user reuse'
