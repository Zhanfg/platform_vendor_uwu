#!/system/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh" || exit 1
[ -d "$STATE_DIR" ] || exit 0
hotfix_supported || {
    hotfix_log 'PAUSED_UNINSTALL: device/API changed; originals retained'
    exit 0
}

restore_key() {
    key="$1"
    backup="$STATE_DIR/original_$key"
    [ -r "$backup" ] || return 0
    original="$(head -n 1 "$backup")"
    case "$original" in 0|1|null) :;; *) return 1;; esac
    # If a user has opted out or disabled this setting in our own Action,
    # leave their chosen runtime value alone.
    if [ -e "$STATE_DIR/user_override_$key" ] ||
       [ -e "$STATE_DIR/manual_off_$key" ]; then
        return 0
    fi
    now="$(hotfix_setting_get "$key")" || return 1
    [ "$now" = 1 ] || return 0
    hotfix_setting_restore "$key" "$original"
}
failed=0
restore_key clock_seconds || failed=1
restore_key uwu_hide_gesture_handle || failed=1
if [ "$failed" -eq 0 ]; then
    for key in clock_seconds uwu_hide_gesture_handle; do
        rm -f "$STATE_DIR/original_$key" "$STATE_DIR/managed_$key" \
              "$STATE_DIR/user_override_$key" "$STATE_DIR/manual_off_$key" \
              "$STATE_DIR/pending_$key"
    done
    rm -f "$STATE_DIR/last_status.txt"
    rmdir "$STATE_DIR" 2>/dev/null || :
else
    hotfix_log 'RESTORE_FAILED: retained original records for manual recovery'
fi
exit 0
