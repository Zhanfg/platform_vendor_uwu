#!/bin/sh
# No-argument build-host packager. One independently rollbackable module per APK.
# Never installs, mounts, signs or changes ROM partitions.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
STAGE="$ROOT/staging"
TEMPLATE="$ROOT/ksu-hotfix"
ORIGINAL="$STAGE/original"
BUILT="$STAGE/built"
PROPS="$STAGE/target.properties"
OUT="$ROOT/out"
for bin in apksigner sha256sum zip mktemp sed; do
    command -v "$bin" >/dev/null 2>&1 || { echo "Missing $bin" >&2; exit 2; }
done
[ -f "$PROPS" ] || { echo "Missing $PROPS" >&2; exit 2; }
[ -f "$TEMPLATE/module.prop" ] && [ -f "$TEMPLATE/post-fs-data.sh" ] || exit 2
for k in device sdk build_id; do
    [ "$(grep -c "^$k=" "$PROPS" || :)" -eq 1 ] || { echo "Missing or duplicate $k" >&2; exit 2; }
done
grep -qx 'device=OnePlus6' "$PROPS" || { echo 'Wrong device' >&2; exit 3; }
grep -qx 'sdk=37' "$PROPS" || { echo 'Wrong Android API' >&2; exit 3; }
grep -qx 'build_id=CP2A.260605.016' "$PROPS" || {
    echo 'Unknown ROM baseline: revalidate before packaging' >&2; exit 3;
}
[ -d "$ORIGINAL" ] && [ -d "$BUILT" ] || {
    echo "Missing original/built directories" >&2; exit 2;
}
for apk in "$BUILT"/*.apk; do
    [ -f "$apk" ] || continue
    case "${apk##*/}" in
        SystemUI.apk|Settings.apk|Launcher3QuickStep.apk|uwuSettingsExt.apk) : ;;
        *) echo "Unrecognized APK: ${apk##*/}" >&2; exit 4 ;;
    esac
done
# apksigner is mandatory: the producer must supply matching platform-signed APKs.
sh "$ROOT/verify_apk_signatures.sh"
mkdir -p "$OUT"
RELEASE=$(mktemp -d "$OUT/release.XXXXXXXX")
TEMP=$(mktemp -d "$OUT/work.XXXXXXXX")
trap 'rm -rf "$TEMP"' EXIT HUP INT TERM
files=0
for name in SystemUI.apk Settings.apk Launcher3QuickStep.apk uwuSettingsExt.apk; do
    [ -f "$BUILT/$name" ] || continue
    [ -f "$ORIGINAL/$name" ] || { echo "Missing baseline for $name" >&2; exit 5; }
    case "$name" in
        SystemUI.apk) component=systemui; path=system_ext/priv-app/SystemUI/SystemUI.apk ;;
        Settings.apk) component=settings; path=system_ext/priv-app/Settings/Settings.apk ;;
        Launcher3QuickStep.apk) component=launcher; path=system_ext/priv-app/Launcher3QuickStep/Launcher3QuickStep.apk ;;
        uwuSettingsExt.apk) component=settingsext; path=system_ext/priv-app/uwuSettingsExt/uwuSettingsExt.apk ;;
    esac
    # TMPFS copies full APKs into RAM: build one independent module per component.
    rm -rf "$TEMP/stage"
    mkdir -p "$TEMP/stage/system/$(dirname "$path")"
    cp "$TEMPLATE/module.prop" "$TEMP/stage/module.prop"
    cp "$TEMPLATE/post-fs-data.sh" "$TEMP/stage/post-fs-data.sh"
    cp "$TEMPLATE/late-load.sh" "$TEMP/stage/late-load.sh"
    cp "$PROPS" "$TEMP/stage/target.properties"
    sed -i "s/^id=.*/id=uwu-ui-hotfix-$component/" "$TEMP/stage/module.prop"
    sed -i "s/^name=.*/name=uwuAOSP Hotfix: $component/" "$TEMP/stage/module.prop"
    hash=$(sha256sum "$ORIGINAL/$name" | sed 's/[[:space:]].*//')
    printf '/system/%s|%s\n' "$path" "$hash" > "$TEMP/stage/base-apks.sha256"
    cp "$BUILT/$name" "$TEMP/stage/system/$path"
    chmod 0755 "$TEMP/stage/post-fs-data.sh" "$TEMP/stage/late-load.sh"
    (cd "$TEMP/stage" && zip -q -r "$RELEASE/uwu-ui-hotfix-$component.zip" .)
    files=$((files + 1))
    echo "STAGED: $component"
done
[ "$files" -gt 0 ] || { echo "No built APKs: no release produced" >&2; exit 6; }
printf 'base_build=CP2A.260605.016\ncomponents=%s\n' "$files" > "$RELEASE/manifest.txt"
echo "Created $RELEASE ($files independently protected modules; NOT installed)"
