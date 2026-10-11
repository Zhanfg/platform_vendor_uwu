#!/system/bin/sh
# KernelSU manager Action: explicitly recheck/reapply 420 when user asks.
MODDIR=${0%/*}
. "$MODDIR/common.sh" || exit 1
valid_target || { echo 'Device/API mismatch'; exit 1; }
if ! read_density; then echo 'Cannot read DPI; no change'; exit 1; fi
echo "Current effective DPI: $EFFECTIVE_DPI"
if [ "$EFFECTIVE_DPI" = 420 ]; then echo 'Already 420; unchanged'; exit 0; fi
if ! wm density 420 >/dev/null 2>&1; then echo 'wm density failed'; exit 1; fi
if ! read_density || [ "$EFFECTIVE_DPI" != 420 ]; then
  echo 'DPI 420 could not be confirmed; do not retry repeatedly'
  exit 1
fi
mkdir -p "$STATE_DIR" || exit 1
: > "$STATE_DIR/v03_density_adjusted"
log_status 'DPI 420 explicitly reapplied using KernelSU Action'
echo 'DPI now 420. No change to gesture regions or clock settings.'
