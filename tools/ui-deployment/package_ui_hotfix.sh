#!/bin/sh
# Single ZIP, one KernelSU module; all payloads use one on-device copy.
# No arguments, no ROM flashing and no signing key access.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
STAGE="$ROOT/staging"
ORIGINAL="$STAGE/original"
BUILT="$STAGE/built"
PROPS="$STAGE/target.properties"
TEMPLATE="$ROOT/ksu-hotfix"
OUT="$ROOT/out"
FINAL="$OUT/uwuAOSP hotfix v0.6.zip"
for bin in apksigner sha256sum zip mktemp sed cmp grep cp; do
    command -v "$bin" >/dev/null 2>&1 || { echo "Missing $bin" >&2; exit 2; }
done
[ -f "$PROPS" ] || { echo "Missing $PROPS" >&2; exit 2; }
for name in module.prop customize.sh post-fs-data.sh late-load.sh service.sh action.sh; do
    [ -f "$TEMPLATE/$name" ] || { echo "Missing template $name" >&2; exit 2; }
done
for property in device sdk build_id; do
    [ "$(grep -c "^$property=" "$PROPS" || :)" -eq 1 ] || {
        echo "Invalid or missing $property" >&2; exit 3;
    }
done
grep -qx 'device=OnePlus6' "$PROPS" || { echo 'Wrong device' >&2; exit 3; }
grep -qx 'sdk=37' "$PROPS" || { echo 'Wrong API' >&2; exit 3; }
grep -qx 'build_id=CP2A.260605.016' "$PROPS" || {
    echo 'Unknown ROM baseline; revalidate after OTA' >&2; exit 3;
}
[ -d "$ORIGINAL" ] && [ -d "$BUILT" ] || { echo 'Missing APK staging' >&2; exit 2; }
for apk in "$BUILT"/*.apk; do
    [ -f "$apk" ] || continue
    case "${apk##*/}" in
        SystemUI.apk|Settings.apk|Launcher3QuickStep.apk|uwuSettingsExt.apk) : ;;
        *) echo "Unrecognized APK ${apk##*/}" >&2; exit 4 ;;
    esac
done
# A zero-diff APK should not take space on the phone; other APKs must
# retain exactly the original platform signer. Never patch signatures.
sh "$ROOT/verify_apk_signatures.sh"
mkdir -p "$OUT"
WORK=$(mktemp -d "$OUT/package.XXXXXXXX")
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
cp "$TEMPLATE/module.prop" "$TEMPLATE/customize.sh" \
   "$TEMPLATE/post-fs-data.sh" "$TEMPLATE/late-load.sh" \
   "$TEMPLATE/service.sh" "$TEMPLATE/action.sh" "$WORK/"
cp "$PROPS" "$WORK/target.properties"
chmod 0755 "$WORK/customize.sh" "$WORK/post-fs-data.sh" \
   "$WORK/late-load.sh" "$WORK/service.sh" "$WORK/action.sh"
: > "$WORK/base-apks.sha256"
: > "$WORK/payload-apks.sha256"
cp "$ROOT/MD3E_NATIVE_SOURCE_LOCK.txt" "$WORK/source-lock.txt"
count=0
for name in SystemUI.apk Settings.apk Launcher3QuickStep.apk uwuSettingsExt.apk; do
    [ -f "$BUILT/$name" ] || continue
    [ -f "$ORIGINAL/$name" ] || { echo "Missing baseline: $name" >&2; exit 5; }
    if cmp -s "$ORIGINAL/$name" "$BUILT/$name"; then
        echo "UNCHANGED: $name (not included)"
        continue
    fi
    case "$name" in
        SystemUI.apk) component=systemui; dest=system_ext/priv-app/SystemUI/SystemUI.apk ;;
        Settings.apk) component=settings; dest=system_ext/priv-app/Settings/Settings.apk ;;
        Launcher3QuickStep.apk) component=launcher; dest=system_ext/priv-app/Launcher3QuickStep/Launcher3QuickStep.apk ;;
        uwuSettingsExt.apk) component=settingsext; dest=system_ext/priv-app/uwuSettingsExt/uwuSettingsExt.apk ;;
    esac
    mkdir -p "$WORK/system/$(dirname "$dest")"
    cp "$BUILT/$name" "$WORK/system/$dest"
    old_hash=$(sha256sum "$ORIGINAL/$name" | sed 's/[[:space:]].*//')
    # Never allow an APK supplied from another OnePlus 6 OTA (or a stale
    # extracted image) to authorize mounting over the current user ROM.
    case "$name:$old_hash" in
      SystemUI.apk:47e4e849e99a695b3c698566fb451cf3cd671ddb17f3e5844d15b2b35188f841|\
      Settings.apk:16b8902482965ce7246e2c2e20bb29b627dbfff7472f9bd90e51ac47adf3ae98|\
      Launcher3QuickStep.apk:c20cb66069a8391005d2ef2de89cbb268bd7928d3874c6bfe773bc5c3a81a3b7|\
      uwuSettingsExt.apk:c3884c97ff320e4176e281abaaf4c43c81f1e6a521dd34507dc7885b230ddef7)
        : ;;
      *) echo "BLOCKED: $name is not the locked 17.0.101 APK" >&2; exit 5 ;;
    esac
    new_hash=$(sha256sum "$BUILT/$name" | sed 's/[[:space:]].*//')
    printf '/system/%s|%s\n' "$dest" "$old_hash" >> "$WORK/base-apks.sha256"
    printf '/system/%s|%s\n' "$dest" "$new_hash" >> "$WORK/payload-apks.sha256"
    count=$((count + 1))
    echo "INCLUDED: $component"
done
[ "$count" -gt 0 ] || { echo 'No modified APK; no hotfix package generated' >&2; exit 6; }
# One ZIP, no duplicate payload storage. Atomic replacement on host.
TMPZIP="$OUT/.uwuAOSP-hotfix-v0.6.$.zip"
trap 'rm -rf "$WORK"; rm -f "$TMPZIP"' EXIT HUP INT TERM
(cd "$WORK" && zip -q -9 -r "$TMPZIP" .)
[ -s "$TMPZIP" ] || { echo 'Empty ZIP' >&2; exit 7; }
mv -f "$TMPZIP" "$FINAL"
echo "ONE INSTALL: $FINAL ($count modified APK components)"
echo "Signed APKs are already compressed; mounted TMPFS RAM use is unchanged."
echo "Not flashed. Verify Mountify and rollback plan before device testing."
