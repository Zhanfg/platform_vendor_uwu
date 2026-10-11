#!/system/bin/sh
MODDIR=${0%/*}
. "$MODDIR/common.sh" || exit 1
valid_target || { log_status 'PAUSED: different device/API'; exit 0; }
count=0
while [ "$(getprop sys.boot_completed 2>/dev/null)" != 1 ]; do
  [ "$count" -lt "$WAIT_LIMIT" ] || { log_status 'SKIPPED: boot not complete'; exit 0; }
  sleep 2
  count=$((count+1))
done
mkdir -p "$STATE_DIR" || exit 1
chmod 0700 "$STATE_DIR" 2>/dev/null || :
# v0.1/v0.2 could have activated risky SystemUI callbacks. Roll back only
# values they actually backed up; skip user overrides and one-time migrations.
rollback_key() {
  KEY=$1
  BACKUP="$STATE_DIR/original_$KEY"
  FINISHED="$STATE_DIR/v03_rollback_$KEY"
  [ -e "$FINISHED" ] && return 0
  [ -f "$BACKUP" ] || { : > "$FINISHED"; return 0; }
  [ ! -e "$STATE_DIR/user_override_$KEY" ] || { : > "$FINISHED"; return 0; }
  [ ! -e "$STATE_DIR/manual_off_$KEY" ] || { : > "$FINISHED"; return 0; }
  BEFORE=$(head -n 1 "$BACKUP")
  case "$BEFORE" in 0|1|null) :;; *) return 1;; esac
  CURRENT=$(read_secure "$KEY") || return 1
  case "$CURRENT" in 0|1|null) :;; *) return 1;; esac
  # v0.1/v0.2 requested 1, but users may have changed it afterwards.
  if [ "$CURRENT" = 1 ] && [ "$BEFORE" != 1 ]; then
    restore_secure "$KEY" "$BEFORE" || return 1
  fi
  : > "$FINISHED"
  return 0
}
ERRORS=0
rollback_key clock_seconds || ERRORS=$((ERRORS+1))
rollback_key uwu_hide_gesture_handle || ERRORS=$((ERRORS+1))
# DPI is the only new v0.3 feature. If it is already 420, *never* run wm.
# If not, make at most one automatic change for this installation; a second
# drift later is reported instead of entering a competing-override loop.
DPI_RESULT=unknown
if read_density; then
  if [ "$EFFECTIVE_DPI" = 420 ]; then
    DPI_RESULT=already_420
  elif [ -f "$STATE_DIR/v03_density_adjusted" ]; then
    DPI_RESULT="drift_$EFFECTIVE_DPI; no repeated override"
  else
    if wm density 420 >/dev/null 2>&1 && read_density && [ "$EFFECTIVE_DPI" = 420 ]; then
      : > "$STATE_DIR/v03_density_adjusted"
      DPI_RESULT=applied_420
    else
      DPI_RESULT='write_failed_or_unverified; no retry loop'
      ERRORS=$((ERRORS+1))
    fi
  fi
else
  DPI_RESULT='wm_read_failed; no changes'
  ERRORS=$((ERRORS+1))
fi
if [ "$ERRORS" -ne 0 ]; then
  log_status "PARTIAL_FAILURE($ERRORS): guarded DPI=$DPI_RESULT; clock/pill not forced"
else
  log_status "SAFE: guarded DPI=$DPI_RESULT; clock/pill not forced"
fi
exit 0
