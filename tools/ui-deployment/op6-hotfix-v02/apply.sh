#!/system/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh" || exit 1

hotfix_supported || {
    hotfix_log 'PAUSED: device/API mismatch; no setting changed'
    exit 0
}

# Bounded wait for framework SettingsProvider, not a background daemon.
case "$MAX_WAIT" in ''|*[!0-9]*) MAX_WAIT=0;; esac
count=0
while [ "$(getprop sys.boot_completed 2>/dev/null)" != 1 ]; do
    if [ "$count" -ge "$MAX_WAIT" ]; then
        hotfix_log 'SKIPPED: boot completion timeout'
        exit 0
    fi
    sleep 2
    count=$((count + 1))
done

[ -f "$MODDIR/options.conf" ] || {
    hotfix_log 'SKIPPED: options file unavailable'
    exit 0
}
mkdir -p "$STATE_DIR" || exit 1
chmod 0700 "$STATE_DIR" 2>/dev/null || :

apply_key() {
    key="$1"
    backup="$STATE_DIR/original_$key"
    active="$STATE_DIR/managed_$key"
    override="$STATE_DIR/user_override_$key"
    manual_off="$STATE_DIR/manual_off_$key"
    pending="$STATE_DIR/pending_$key"
    [ ! -e "$override" ] && [ ! -e "$manual_off" ] || return 2
    current="$(hotfix_setting_get "$key")" || return 1
    case "$current" in 0|1|null) :;; *) return 1;; esac

    if [ -f "$backup" ]; then
        if [ -e "$pending" ]; then
            original="$(head -n 1 "$backup")"
            if [ "$current" = 1 ]; then
                rm -f "$pending"
                : > "$active" || return 1
                return 0
            fi
            # A previous SettingsProvider write failed; retry only if the
            # runtime value still matches the value we originally read.
            [ "$current" = "$original" ] || {
                rm -f "$pending"
                : > "$override" || return 1
                return 2
            }
            hotfix_setting_put "$key" 1 || return 1
            rm -f "$pending"
            : > "$active" || return 1
            return 0
        fi
        # v0.1 upgrade: original exists but had no managed marker. If the
        # current value is not our former requested 1, assume a user change.
        if [ ! -f "$active" ]; then
            if [ "$current" != 1 ]; then
                : > "$override" || return 1
                return 2
            fi
            : > "$active" || return 1
        fi
        if [ "$current" != 1 ]; then
            : > "$override" || return 1
            return 2
        fi
        return 0
    fi

    # First install: preserve ABSENT (null) separately from an explicit 0.
    hotfix_atomic_save "$backup" "$current" || return 1
    if [ "$current" != 1 ]; then
        : > "$pending" || return 1
        hotfix_setting_put "$key" 1 || return 1
        rm -f "$pending"
    fi
    : > "$active" || return 1
    return 0
}

failed=0
skipped=0
if hotfix_enabled clock_seconds; then
    apply_key clock_seconds || {
        status=$?
        if [ "$status" -eq 2 ]; then skipped=$((skipped + 1)); else failed=$((failed + 1)); fi
    }
fi
if hotfix_enabled hide_gesture_handle; then
    apply_key uwu_hide_gesture_handle || {
        status=$?
        if [ "$status" -eq 2 ]; then skipped=$((skipped + 1)); else failed=$((failed + 1)); fi
    }
fi
if [ "$failed" -gt 0 ]; then
    hotfix_log "PARTIAL_FAILURE: $failed failed, $skipped skipped; review permissions"
elif [ "$skipped" -gt 0 ]; then
    hotfix_log "APPLIED_WITH_USER_OVERRIDES: $skipped intentionally skipped"
else
    hotfix_log 'APPLIED: settings checked once; no SystemUI restart'
fi
exit 0
