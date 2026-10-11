#!/system/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh" || exit 1
valid_target || { log_status 'RRO PAUSED: device/API mismatch'; exit 0; }
[ "$(getprop ro.build.id)" = CP2A.260605.016 ] || {
    log_status 'RRO PAUSED: changed ROM build; revalidation required'
    exit 0
}
# This is read-only unless OverlayManager confirms our own overlay is
# installed and disabled; never touch another vendor/ROM overlay.
RRO=com.uwuaosp.hotfix.gesturepill.v04
status=$(cmd overlay list --user 0 com.android.systemui 2>&1) || {
    log_status 'RRO UNKNOWN: OverlayManager query failed'; exit 0;
}
case "$status" in
    *"$RRO"*) : ;;
    *) log_status 'RRO NOT REGISTERED: Mountify system_ext overlay not active'; exit 0 ;;
esac
if ! printf '%s\n' "$status" | grep -F -e "[x] $RRO" -e "[X] $RRO" >/dev/null; then
    cmd overlay enable --user 0 "$RRO" >/dev/null 2>&1 || {
        log_status 'RRO NOT ENABLED: OverlayManager rejected requested overlay'
        exit 0
    }
fi
# Resource lookup is a *check*, not a new mutation. Numeric formatting
# varies by Android branch so do not claim it has taken effect on all builds.
radius=$(cmd overlay lookup --user 0 com.android.systemui \
    com.android.systemui:dimen/navigation_handle_radius 2>&1) || {
    log_status 'RRO ENABLED: effective radius could not be confirmed'; exit 0;
}
log_status "RRO CHECK: $radius"
exit 0
