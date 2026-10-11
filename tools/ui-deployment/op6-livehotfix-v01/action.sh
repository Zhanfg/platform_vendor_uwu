#!/system/bin/sh
# One action in KernelSU Manager: toggle gesture pill preference.
# A fresh boot is not required for an already working ContentObserver.
PATH="/system/bin:/system/xbin:/vendor/bin:/product/bin:/sbin:$PATH"
MODDIR=${0%/*}
CONFIG="$MODDIR/options.conf"
[ -f "$CONFIG" ] || { echo 'Configuration is missing'; exit 1; }
case "$(getprop ro.product.device)" in OnePlus6|enchilada) :;; *) echo 'Unsupported device'; exit 1;; esac
[ "$(getprop ro.build.version.sdk)" = 37 ] || { echo 'Unsupported Android version'; exit 1; }
if grep -q -x 'hide_gesture_handle=1' "$CONFIG"; then
    OLD=1; NEW=0
else
    OLD=0; NEW=1
fi
TEMP="$CONFIG.tmp.$$"
sed "s/^hide_gesture_handle=[01]$/hide_gesture_handle=$NEW/" "$CONFIG" > "$TEMP" || exit 1
mv -f "$TEMP" "$CONFIG" || exit 1
chmod 0644 "$CONFIG" 2>/dev/null || :
if [ "$NEW" = 1 ]; then
    settings --user 0 put secure uwu_hide_gesture_handle 1 >/dev/null 2>&1 || {
        echo 'Saved toggle, but SettingsProvider write failed'; exit 1;
    }
    echo 'Gesture-handle hiding: REQUESTED (ON).'
else
    # Restore the original setting rather than force arbitrary state.
    BACKUP=/data/adb/uwu-ui-live-hotfix-state/original_uwu_hide_gesture_handle
    if [ -r "$BACKUP" ]; then
        original="$(head -n 1 "$BACKUP")"
        case "$original" in
            null) settings --user 0 delete secure uwu_hide_gesture_handle >/dev/null 2>&1 || : ;;
            0|1) settings --user 0 put secure uwu_hide_gesture_handle "$original" >/dev/null 2>&1 || : ;;
            *) echo 'Unexpected original value; no runtime change' ;;
        esac
    else
        echo 'No original value recorded; not altering phone setting.'
    fi
    echo 'Gesture-handle hiding: OFF (module request removed).'
fi
echo 'Seconds display remains enabled. No SystemUI process was restarted.'
echo 'Note: current ROM may still render the gesture pill until SystemUI source fixes are compiled.'
