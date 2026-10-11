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

for tool in apksigner aapt2 sha256sum sed tr; do
    command -v "$tool" >/dev/null 2>&1 || { echo "Missing required command: $tool" >&2; exit 2; }
done
[ -d "$ORIGINAL" ] && [ -d "$BUILT" ] || {
    echo "Expected staging/original and staging/built APK directories" >&2; exit 2;
}

digest() {
    # The original and built APK must both pass Android's signature validation.
    apk="$1"
    # Check the actual target API level, not the runner's default. A v1-
    # only or otherwise invalid APK must never pass the platform signer gate.
    result=$(apksigner verify --min-sdk-version 37 --print-certs "$apk") || return 1
    # Identity is the *entire* signer set. Reject any multi-signer APK,
    # including signer #10+ (which the old #[2-9] regex missed).
    signer_count=$(printf '%s\n' "$result" |
        grep -Ec '^Signer #[0-9]+ certificate SHA-256 digest:' || :)
    [ "$signer_count" -eq 1 ] || return 1
    hash=$(printf '%s\n' "$result" |
        sed -n 's/^Signer #1 certificate SHA-256 digest:[[:space:]]*//p' |
        tr -d '[:space:]')
    [ ${#hash} -eq 64 ] || return 1
    printf '%s\n' "$hash"
}

# A matching signing certificate alone does NOT prove an APK is the expected
# Android package. Swapping in an unrelated platform-signed APK can leave
# SystemUI or Settings unable to start. Verify package identity before mount.
package_name() {
    output=$(aapt2 dump packagename "$1" 2>/dev/null) || return 1
    # aapt2 prints exactly one package name; never parse a free-form APK label.
    case "$output" in
        ''|*[!a-zA-Z0-9._]*) return 1 ;;
    esac
    printf '%s\n' "$output"
}

tmp="$OUT.tmp"
printf 'name\tpackage_name\tbaseline_cert_sha256\tbaseline_apk_sha256\tbuilt_apk_sha256\n' > "$tmp"
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
    old_package=$(package_name "$old") ||
        { echo "Cannot read package name: original $name" >&2; rm -f "$tmp"; exit 4; }
    new_package=$(package_name "$new") ||
        { echo "Cannot read package name: built $name" >&2; rm -f "$tmp"; exit 4; }
    if [ "$old_package" != "$new_package" ]; then
        echo "BLOCKED package identity mismatch: $name ($old_package vs $new_package)" >&2
        rm -f "$tmp"
        exit 5
    fi
    # These are platform-critical package names, not arbitrary signer domains.
    case "$name:$old_package" in
        SystemUI.apk:com.android.systemui|Settings.apk:com.android.settings) : ;;
        SystemUI.apk:*|Settings.apk:*)
            echo "BLOCKED unexpected platform package name: $name" >&2
            rm -f "$tmp"
            exit 5 ;;
    esac
    orig_digest=$(digest "$old") || { echo "Signature verification failed: original $name" >&2; rm -f "$tmp"; exit 4; }
    new_digest=$(digest "$new") || { echo "Signature verification failed: built $name" >&2; rm -f "$tmp"; exit 4; }
    if [ "$orig_digest" != "$new_digest" ]; then
        echo "BLOCKED signer mismatch: $name" >&2
        rm -f "$tmp"
        exit 5
    fi
    old_sha=$(sha256sum "$old" | sed 's/[[:space:]].*//')
    new_sha=$(sha256sum "$new" | sed 's/[[:space:]].*//')
    printf '%s\t%s\t%s\t%s\t%s\n' "$name" "$old_package" "$orig_digest" "$old_sha" "$new_sha" >> "$tmp"
    echo "OK: $name signer and Android package identity match"
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
