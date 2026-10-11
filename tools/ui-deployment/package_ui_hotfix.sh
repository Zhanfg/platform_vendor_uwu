#!/bin/sh
# No-argument build-host packager; cannot flash or install anything.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
STAGE="$ROOT/staging"
TEMPLATE="$ROOT/ksu-hotfix"
ORIGINAL="$STAGE/original"
BUILT="$STAGE/built"
PROPS="$STAGE/target.properties"
OUT="$ROOT/out"
for bin in apksigner sha256sum zip; do
    command -v "$bin" >/dev/null 2>&1 || { echo "Missing $bin" >&2; exit 2; }
done
[ -f "$PROPS" ] || { echo "Missing $PROPS" >&2; exit 2; }
[ -f "$TEMPLATE/module.prop" ] && [ -f "$TEMPLATE/post-fs-data.sh" ] || exit 2
for k in device sdk build_id; do
    [ "$(grep -c "^$k=" "$PROPS" || :)" -eq 1 ] || { echo "Missing or duplicate $k" >&2; exit 2; }
done
grep -qx 'device=OnePlus6' "$PROPS" || { echo 'Wrong device' >&2; exit 3; }
grep -qx 'sdk=37' "$PROPS" || { echo 'Wrong Android API' >&2; exit 3; }
grep -qx 'build_id=CP2A.260605.016' "$PROPS" || { echo 'Unexpected ROM, re-baseline after OTA' >&2; exit 3; }
[ -d "$ORIGINAL" ] && [ -d "$BUILT" ] || { echo 'Missing original/built APK dirs' >&2; exit 2; }
sh "$ROOT/verify_apk_signatures.sh"
mkdir -p "$OUT"
TEMP=$(mktemp -d "$OUT/build.XXXXXX")
trap 'rm -rf "$TEMP"' EXIT HUP INT TERM
cp "$TEMPLATE/module.prop" "$TEMPLATE/post-fs-data.sh" "$TEMP/"
cp "$PROPS" "$TEMP/target.properties"
chmod 0755 "$TEMP/post-fs-data.sh"
: > "$TEMP/base-apks.sha256"
files=0
for name in SystemUI.apk Settings.apk Launcher3QuickStep.apk uwuSettingsExt.apk; do
    [ -f "$BUILT/$name" ] || continue
    [ -f "$ORIGINAL/$name" ] || { echo "Missing baseline for $name" >&2; exit 3; }
    case "$name" in
        SystemUI.apk) path=system_ext/priv-app/SystemUI/SystemUI.apk ;;
        Settings.apk) path=system_ext/priv-app/Settings/Settings.apk ;;
        Launcher3QuickStep.apk) path=system_ext/priv-app/Launcher3QuickStep/Launcher3QuickStep.apk ;;
        uwuSettingsExt.apk) path=system_ext/priv-app/uwuSettingsExt/uwuSettingsExt.apk ;;
    esac
    hash=$(sha256sum "$ORIGINAL/$name" | sed 's/[[:space:]].*//')
    printf '/system/%s|%s\n' "$path" "$hash" >> "$TEMP/base-apks.sha256"
    mkdir -p "$TEMP/system/$(dirname "$path")"
    cp "$BUILT/$name" "$TEMP/system/$path"
    files=$((files + 1))
done
[ "$files" -gt 0 ] || { echo 'No recognized built APKs' >&2; exit 4; }
for apk in "$BUILT"/*.apk; do
    [ -f "$apk" ] || continue
    case "${apk##*/}" in SystemUI.apk|Settings.apk|Launcher3QuickStep.apk|uwuSettingsExt.apk) ;;
        *) echo "Unrecognized APK $apk" >&2; exit 4 ;;
    esac
done
rm -f "$OUT/uwu-ui-hotfix.zip"
(cd "$TEMP" && zip -qr "$OUT/uwu-ui-hotfix.zip" .)
echo "Prepared $OUT/uwu-ui-hotfix.zip ($files checked APK pairs), NOT installed."
