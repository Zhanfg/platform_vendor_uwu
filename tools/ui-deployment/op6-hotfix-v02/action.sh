#!/system/bin/sh
# KernelSU Action: toggle gesture-hint REQUEST, retaining original settings.
MODDIR=${0%/*}
. "$MODDIR/common.sh" || exit 1
hotfix_supported || { echo 'Unsupported device/API'; exit 1; }
config="$MODDIR/options.conf"
[ -f "$config" ] || { echo 'Options missing'; exit 1; }
mkdir -p "$STATE_DIR" || exit 1
chmod 0700 "$STATE_DIR" 2>/dev/null || :
key=uwu_hide_gesture_handle
backup="$STATE_DIR/original_$key"
manual_off="$STATE_DIR/manual_off_$key"
override="$STATE_DIR/user_override_$key"
active="$STATE_DIR/managed_$key"
now="$(hotfix_setting_get "$key")" || { echo 'SettingsProvider unavailable'; exit 1; }
case "$now" in null|0|1) :;; *) echo 'Invalid system setting'; exit 1;; esac
# A module upgrade may replace options.conf with its default (1), while
# the manual-off marker intentionally survives outside the module directory.
if [ -e "$manual_off" ]; then
    new=1
elif grep -Fxq 'hide_gesture_handle=1' "$config"; then
    new=0
else
    new=1
fi

if [ "$new" -eq 1 ]; then
    if [ ! -f "$backup" ]; then
        hotfix_atomic_save "$backup" "$now" || exit 1
    fi
    # Explicit user action authorizes re-enabling even after manual opt-out.
    if [ "$now" != 1 ]; then
        hotfix_setting_put "$key" 1 || { echo 'Settings write failed; no config change'; exit 1; }
    fi
    : > "$active" || { echo 'Cannot save managed state'; exit 1; }
else
    if [ -r "$backup" ] && [ "$now" = 1 ]; then
        prev="$(head -n 1 "$backup")"
        hotfix_setting_restore "$key" "$prev" || {
            echo 'Original value could not be restored; option unchanged'; exit 1;
        }
    fi
fi
# Commit config only after runtime action succeeds; keep first line comments.
tmp="$config.tmp.$$"
sed "s/^hide_gesture_handle=[01]$/hide_gesture_handle=$new/" "$config" > "$tmp" || exit 1
if ! mv -f "$tmp" "$config"; then
    echo 'Config update failed; check runtime setting manually'
    exit 1
fi
chmod 0644 "$config" 2>/dev/null || :
if [ "$new" -eq 1 ]; then
    rm -f "$manual_off" "$override" "$STATE_DIR/pending_$key"
    echo 'uwuAOSP hotfix: gesture-hint hiding REQUESTED (ON)'
else
    : > "$manual_off" || exit 1
    echo 'uwuAOSP hotfix: gesture-hint hiding request OFF'
fi
echo 'Status bar seconds are unchanged. No SystemUI restart.'
echo 'White pill may remain until the unsigned SystemUI source fix is built and tested.'
