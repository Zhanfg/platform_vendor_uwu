#!/bin/sh
# Check signer compatibility before ANY systemless package replacement.
# Run: sh tools/ui-deployment/verify_apk_signatures.sh (no arguments).
# This script only reads APKs; it does not install, sign, mount or patch anything.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
STAGE="$ROOT/staging"
ORIGINAL="$STAGE/original"
BUILT="$STAGE/built"
OUT="$STAGE/signature-check.tsv"
umask 077

for tool in apksigner sha256sum sed tr; do
    command -v "$tool" >/dev/null 2>&1 || { echo "Missing required command: $tool" >&2; exit 2; }
done
[ -d "$ORIGINAL" ] && [ -d "$BUILT" ] || {
    echo "Expected staging/original and staging/built APK directories" >&2; exit 2;
}

digest() {
    # The original and built APK must both pass Android's signature validation.
    apk="$1"
    result=$(apksigner verify --print-certs "$apk") || return 1
    hash=$(printf '%s\n' "$result" |
        sed -n 's/^Signer #1 certificate SHA-256 digest:[[:space:]]*//p' |
        tr -d '[:space:]')
    [ ${#hash} -eq 64 ] || return 1
    printf '%s\n' "$hash"
}

tmp="$OUT.tmp"
printf 'name\tbaseline_cert_sha256\tbaseline_apk_sha256\tbuilt_apk_sha256\n' > "$tmp"
total=0
for name in SystemUI.apk Settings.apk Launcher3QuickStep.apk uwuSettingsExt.apk ThemePicker.apk; do
    old="$ORIGINAL/$name"
    new="$BUILT/$name"
    if [ ! -f "$old" ] && [ ! -f "$new" ]; then continue; fi
    if [ ! -f "$old" ] || [ ! -f "$new" ]; then
        echo "INCOMPLETE pair: $name" >&2
        rm -f "$tmp"
        exit 3
    fi
    orig_digest=$(digest "$old") || { echo "Signature verification failed: original $name" >&2; rm -f "$tmp"; exit 4; }
    new_digest=$(digest "$new") || { echo "Signature verification failed: built $name" >&2; rm -f "$tmp"; exit 4; }
    if [ "$orig_digest" != "$new_digest" ]; then
        echo "BLOCKED signer mismatch: $name" >&2
        rm -f "$tmp"
        exit 5
    fi
    old_sha=$(sha256sum "$old" | sed 's/[[:space:]].*//')
    new_sha=$(sha256sum "$new" | sed 's/[[:space:]].*//')
    printf '%s\t%s\t%s\t%s\n' "$name" "$orig_digest" "$old_sha" "$new_sha" >> "$tmp"
    echo "OK: $name certificate matches"
    total=$((total + 1))
done
if [ "$total" -eq 0 ]; then
    echo "BLOCKED: no APK pairs found" >&2
    rm -f "$tmp"
    exit 6
fi
mv "$tmp" "$OUT"
echo "Signature preflight passed for $total APKs; report: $OUT"
echo "This does not establish device compatibility or produce a flashable artifact."
