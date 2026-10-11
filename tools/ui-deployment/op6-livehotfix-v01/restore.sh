#!/system/bin/sh
# Conservative uninstall: only restore if the key still has our applied value.
PATH="${UWU_HOTFIX_TEST_PATH:-/system/bin:/system/xbin:/vendor/bin:/product/bin:/sbin}:$PATH"
STATE_DIR=${UWU_HOTFIX_TEST_STATE_DIR:-/data/adb/uwu-ui-live-hotfix-state}
export PATH
[ -d "$STATE_DIR" ] || exit 0
restore_key() {
    key="$1"
    backup="$STATE_DIR/original_$key"
    [ -r "$backup" ] || return 0
    previous="$(head -n 1 "$backup")"
    now="$(settings --user 0 get secure "$key" 2>/dev/null)" || return 0
    # Do not undo a value explicitly changed by the user since our last apply.
    [ "$now" = 1 ] || return 0
    case "$previous" in
        null) settings --user 0 delete secure "$key" >/dev/null 2>&1 || return 1 ;;
        0|1) settings --user 0 put secure "$key" "$previous" >/dev/null 2>&1 || return 1 ;;
        *) return 1 ;;
    esac
    return 0
}
err=0
restore_key clock_seconds || err=1
restore_key uwu_hide_gesture_handle || err=1
if [ "$err" -eq 0 ]; then
    rm -f "$STATE_DIR/original_clock_seconds" \
          "$STATE_DIR/original_uwu_hide_gesture_handle" \
          "$STATE_DIR/last_status.txt"
    rmdir "$STATE_DIR" 2>/dev/null || :
fi
exit 0
