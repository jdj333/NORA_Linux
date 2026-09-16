#!/bin/bash
set -euo pipefail
iso=${1:?Usage: verify-iso.sh path/to/nora.iso}
test -s "$iso"
report=$(xorriso -indev "$iso" -report_el_torito plain 2>&1)
printf '%s\n' "$report"
# Require actual BIOS and UEFI El Torito boot records, not just an ISO filename.
grep -Eq 'El Torito boot img.*BIOS' <<< "$report"
grep -Eq 'El Torito boot img.*UEFI' <<< "$report"
files=$(xorriso -indev "$iso" -find /live -type f -exec echo -- 2>/dev/null)
printf '%s\n' "$files"
grep -q '/live/filesystem.squashfs' <<< "$files"
grep -q '/live/vmlinuz' <<< "$files"
grep -q '/live/initrd.img' <<< "$files"
echo 'ISO structure passed. A VM boot and installation test are still required.'
