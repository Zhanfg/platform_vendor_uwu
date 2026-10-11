#!/system/bin/sh
# One-shot Secure settings apply. No SystemUI process kill or restart.
# Test overrides are used only by CI and are not enabled by the module.
PATH="${UWU_HOTFIX_TEST_PATH:-/system/bin:/system/xbin:/vendor/bin:/product/bin:/sbin}:$PATH"
MODDIR=${0%/*}
STATE_DIR=${UWU_HOTFIX_TEST_STATE_DIR:-/data/adb/uwu-ui-live-hotfix-state}
export PATH
umask 077

log() {
    mkdir -p "$STATE_DIR" 2>/dev/null || return 0
    printf '%s\n' "$1" > "$STATE_DIR/last_status.txt" 2>/dev/null || :
}

valid_environment() {
    case "$(getprop ro.product.device 2>/dev/null)" in OnePlus6|enchilada) :;; *) return 1;; esac
    [ "$(getprop ro.build.version.sdk 2>/dev/null)" = 37 ] || return 1
}
valid_environment || { log 'PAUSED: device or Android API changed'; exit 0; }

# Never leave a resident process. Bounds startup wait and exits on timeout.
max_wait=${UWU_HOTFIX_TEST_MAX_WAIT:-45}
count=0
while [ "$(getprop sys.boot_completed 2>/dev/null)" != 1 ]; do
    if [ "$count" -ge "$max_wait" ]; then
        log 'SKIPPED: Android did not finish booting within wait limit'
        exit 0
    fi
    sleep 2
    count=$((count + 1))
done

[ -f "$MODDIR/options.conf" ] || { log 'SKIPPED: missing configuration'; exit 0; }
mkdir -p "$STATE_DIR" || exit 0
chmod 0700 "$STATE_DIR" 2>/dev/null || :

option_enabled() { grep -q -x "$1=1" "$MODDIR/options.conf" 2>/dev/null; }
# Record original Secure values once, outside module root, surviving ZIP upgrades.
apply_setting() {
    key="$1"
    goal="$2"
    backup="$STATE_DIR/original_$key"
    current="$(settings --user 0 get secure "$key" 2>/dev/null)" || {
        log "SKIPPED: cannot query $key"; return 1;
    }
    [ -n "$current" ] || { log "SKIPPED: blank value for $key"; return 1; }
    if [ ! -f "$backup" ]; then
        temp="$backup.tmp.$$"
        printf '%s\n' "$current" > "$temp" || return 1
        mv -f "$temp" "$backup" || return 1
        chmod 0600 "$backup" 2>/dev/null || :
    fi
    if [ "$current" != "$goal" ]; then
        settings --user 0 put secure "$key" "$goal" >/dev/null 2>&1 || {
            log "FAILED: cannot write $key"; return 1;
        }
    fi
    return 0
}

# Respect the explicit module options; disable via KSU if desired.
if option_enabled clock_seconds; then
    apply_setting clock_seconds 1 || :
fi
if option_enabled hide_gesture_handle; then
    # This preference is already defined in uwuAOSP. The original ROM's
    # NavigationHandle bug may still prevent the pill disappearing.
    apply_setting uwu_hide_gesture_handle 1 || :
fi
log 'APPLIED: one-shot settings request; no APK replacement or SystemUI restart'
exit 0
