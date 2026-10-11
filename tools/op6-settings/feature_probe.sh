#!/system/bin/sh
# Read-only OnePlus 6 UI / AOSP feature parity probe.
# No arguments; no rooting, system writes, service restarts, or user identifiers.
PATH=/system/bin:/system/xbin:/vendor/bin:/product/bin:/sbin:$PATH
DEST=/sdcard/Download
[ -d "$DEST" ] || DEST=.
TS=$(date +%Y%m%d_%H%M%S 2>/dev/null)
[ -n "$TS" ] || TS=unknown
OUT="$DEST/OP6_Settings_Feature_Probe_$TS.txt"
umask 077

get_property() {
    value=$(getprop "$1" 2>/dev/null)
    printf '%s=%s\n' "$1" "$value"
}
check_file() {
    path="$1"
    if [ -r "$path" ]; then
        printf 'READABLE: %s\n' "$path"
    elif [ -e "$path" ]; then
        printf 'EXISTS_BUT_RESTRICTED: %s\n' "$path"
    else
        printf 'NOT_FOUND: %s\n' "$path"
    fi
}
{
    echo 'uwuAOSP Android 17 / OnePlus 6 Settings feature parity'
    echo 'Read only. Not found != unsupported; a failed Binder query != hardware absence.'
    echo '== Baseline =='
    for key in ro.product.device ro.build.version.sdk ro.build.id ro.hardware; do
        get_property "$key"
    done
    echo '== Navigation mode and saved gesture pill preference =='
    printf 'Secure navigation_mode: '
    settings get secure navigation_mode 2>&1 || :
    printf 'Secure uwu_hide_gesture_handle: '
    settings get secure uwu_hide_gesture_handle 2>&1 || :
    echo '== AOSP settings / storage backend =='
    printf 'Secure automatic_storage_manager_enabled: '
    settings get secure automatic_storage_manager_enabled 2>&1 || :
    printf 'Global development_settings_enabled: '
    settings get global development_settings_enabled 2>&1 || :
    echo '== OnePlus feature packages (names only) =='
    if command -v pm >/dev/null 2>&1; then
        packages=$(pm list packages 2>&1)
        printf '%s\n' "$packages" | grep -iE 'oneplus|oplus|lineage|keyhandler|dirac|doze|livedisplay|pocket' | head -n 60 || :
        case "$packages" in *'Exception'*|*'Failed transaction'*) echo 'PackageManager query FAILED';; esac
    fi
    echo '== Vendor service names (filtered) =='
    if command -v service >/dev/null 2>&1; then
        service list 2>&1 | grep -iE 'oneplus|lineage|touch|livedisplay|composer|color|health' | head -n 75 || :
    fi
    echo '== Sensor support (filtered) =='
    if command -v dumpsys >/dev/null 2>&1; then
        dumpsys sensorservice 2>&1 |
            grep -iE 'oneplus.sensor|pocket|pickup|significant.motion|proximity' |
            head -n 50 || :
    fi
    echo '== Potential OnePlus sysfs support (presence only) =='
    for p in \
        /sys/class/power_supply/battery/op_disable_charge \
        /sys/class/power_supply/battery/charging_enabled \
        /sys/class/switch/tri-state-key/state \
        /sys/class/switch/tri_state_key/state \
        /sys/class/leds/lcd-backlight/brightness \
        /proc/touchpanel/gesture_enable \
        /proc/touchpanel/double_tap_enable \
        /sys/class/graphics/fb0/actual_fps; do
        check_file "$p"
    done
    echo '== Kernel input device labels (filtered) =='
    if [ -r /proc/bus/input/devices ]; then
        grep -iE 'N: Name=|tri-state|slider|oneplus|fingerprint|touchpanel' \
            /proc/bus/input/devices | head -n 80 || :
    fi
    echo '== Installed overlay identities (filtered) =='
    if command -v cmd >/dev/null 2>&1; then
        cmd overlay list --user 0 2>&1 |
            grep -iE 'oneplus|oplus|uwu|lineage|gesture|nav|display|theme|error|exception' |
            head -n 70 || :
    fi
    echo '== End =='
    echo 'No sysfs values were written. No package or ROM components were changed.'
} > "$OUT" 2>&1
echo "Saved: $OUT"
