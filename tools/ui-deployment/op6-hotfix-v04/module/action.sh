#!/system/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh" || exit 1
valid_target || { echo 'Unsupported device/API'; exit 1; }
echo 'uwuAOSP hotfix v0.4: verifying RRO'
/system/bin/sh "$MODDIR/rro-verify.sh"
[ -r "$STATE_DIR/last_status.txt" ] && cat "$STATE_DIR/last_status.txt"
if read_density; then
    echo "DPI: $EFFECTIVE_DPI (target 420)"
    if [ "$EFFECTIVE_DPI" != 420 ]; then
        echo 'DPI is not 420; use a separate user-authorized density adjustment if desired.'
    fi
else
    echo 'WindowManager density is unreadable; no blind write was attempted.'
fi
exit 0
