#!/system/bin/sh
# KernelSU regular post-fs-data executes before the metamodule's mount handler.
# Never mount, reboot, or modify ROM partitions here.
MODDIR=${0%/*}
STATUS="$MODDIR/last_guard_status.txt"
BLOCK="$MODDIR/skip_mount"
CONFIG="$MODDIR/target.properties"
BASES="$MODDIR/base-apks.sha256"

write_state() { printf '%s\n' "$1" > "$STATUS" 2>/dev/null || :; }
block() {
    write_state "PAUSED: $1"
    : > "$BLOCK" 2>/dev/null || :
    exit 0
}

[ -r "$CONFIG" ] && [ -s "$BASES" ] || block 'missing manifest'
read_prop() { sed -n "s/^$1=//p" "$CONFIG" | head -n 1; }
expected_device=$(read_prop device)
expected_sdk=$(read_prop sdk)
expected_id=$(read_prop build_id)
[ -n "$expected_device" ] && [ -n "$expected_sdk" ] && [ -n "$expected_id" ] || block 'invalid properties'
[ "$(getprop ro.product.device)" = "$expected_device" ] || block 'different device'
[ "$(getprop ro.build.version.sdk)" = "$expected_sdk" ] || block 'different Android API'
[ "$(getprop ro.build.id)" = "$expected_id" ] || block 'different ROM build ID'
command -v sha256sum >/dev/null 2>&1 || block 'sha256sum unavailable'
count=0
while IFS='|' read -r origin hash; do
    [ -n "$origin" ] || continue
    case "$origin" in
        /system/system_ext/priv-app/SystemUI/SystemUI.apk|\
        /system/system_ext/priv-app/Settings/Settings.apk|\
        /system/system_ext/priv-app/Launcher3QuickStep/Launcher3QuickStep.apk|\
        /system/system_ext/priv-app/uwuSettingsExt/uwuSettingsExt.apk) ;;
        *) block 'unexpected target path' ;;
    esac
    case "$hash" in ''|*[!0-9a-f]*) block 'invalid digest' ;; esac
    [ "${#hash}" -eq 64 ] || block 'invalid digest length'
    probe_path="$origin"
    # Test harness only; do not set on actual device.
    if [ -n "${UWU_GUARD_TEST_ROOT:-}" ]; then
        probe_path="$UWU_GUARD_TEST_ROOT$origin"
    fi
    [ -r "$probe_path" ] || block 'baseline file missing'
    actual=$(sha256sum "$probe_path" 2>/dev/null | sed 's/[[:space:]].*//') || block 'hash read failed'
    [ "$actual" = "$hash" ] || block 'baseline APK hash mismatch (OTA or conflicting module)'
    count=$((count + 1))
done < "$BASES"
[ "$count" -gt 0 ] || block 'empty baseline list'
# Sticky skip_mount must be cleared only after user re-enables a verified update.
if [ -e "$BLOCK" ]; then
    write_state 'COMPATIBLE BUT PAUSED: explicit reenable required'
else
    write_state 'COMPATIBLE: eligible for KernelSU metamodule mount'
fi
exit 0
