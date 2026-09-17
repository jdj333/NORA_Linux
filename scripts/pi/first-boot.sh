#!/bin/bash
# Runs on the attached console, before LightDM. No shared default password.
set -euo pipefail
user=$(getent passwd 1000 | cut -d: -f1 || true)
if [[ -z "$user" ]]; then
    user=nora
    useradd -m -s /bin/bash "$user"
fi
usermod -aG adm,sudo,audio,video,render,input,plugdev,netdev "$user"
state=$(passwd -S "$user" | awk '{print $2}')
if [[ "$state" != P ]]; then
    chvt 8
    clear
    echo 'Welcome to NORA Linux for Raspberry Pi 5.'
    echo "Create a password for $user to finish setup."
    until passwd "$user"; do echo 'Please try again.'; done
fi
install -d /etc/lightdm/lightdm.conf.d /var/lib/nora
cat > /etc/lightdm/lightdm.conf.d/95-nora-user.conf <<CONFIG
[Seat:*]
user-session=xfce
autologin-user=$user
autologin-user-timeout=0
CONFIG
# Require the chosen password for administrative commands.
for file in /etc/sudoers.d/010_pi-nopasswd /etc/sudoers.d/90-cloud-init-users; do
    if [[ -f "$file" ]]; then
        sed -i '/^[^#].*NOPASSWD/d' "$file"
    fi
done
touch /var/lib/nora/setup-complete
