#!/system/bin/sh
# One-shot post-boot: verify actual Mountify-mounted APK bytes before
# changing SystemUI options. No daemon, polling service, or forced restart.
MODDIR=${0%/*}
MANIFEST="$MODDIR/payload-apks.sha256"
STATUS="$MODDIR/last_runtime_status.txt"
ROOT=/data/adb/uwu-ui-live-hotfix-state
log() { printf '%s\n' "$1" > "$STATUS" 2>/dev/null || :; }
case "$(getprop ro.product.device)" in OnePlus6|enchilada) :;; *) log 'PAUSED: device mismatch'; exit 0;; esac
[ "$(getprop ro.build.version.sdk)" = 37 ] || { log 'PAUSED: API mismatch'; exit 0; }
[ "$(getprop ro.build.id)" = CP2A.260605.016 ] || { log 'PAUSED: ROM changed'; exit 0; }
[ ! -e "$MODDIR/skip_mount" ] || { log 'PAUSED: OTA mount lock'; exit 0; }
[ -r "$MANIFEST" ] && [ -s "$MANIFEST" ] || { log 'PAUSED: missing payload hashes'; exit 0; }
waited=0
until [ "$(getprop sys.boot_completed)" = 1 ]; do
  [ "$waited" -lt 45 ] || { log 'PAUSED: boot not ready'; exit 0; }
  sleep 2
  waited=$((waited+1))
done
# Compare mounted live files, not just what's in the KSU /data directory.
# If Mountify failed to mount, old APK hashes won't match this manifest.
sysui_ok=0
count=0
while IFS='|' read -r origin expected; do
  [ -n "$origin" ] || continue
  case "$origin" in
    /system/system_ext/priv-app/SystemUI/SystemUI.apk|\
    /system/system_ext/priv-app/Settings/Settings.apk|\
    /system/system_ext/priv-app/Launcher3QuickStep/Launcher3QuickStep.apk|\
    /system/system_ext/priv-app/uwuSettingsExt/uwuSettingsExt.apk|\
    /system/system_ext/priv-app/ThemePicker/ThemePicker.apk) : ;;
    *) log 'PAUSED: unexpected mount target'; exit 0 ;;
  esac
  case "$expected" in ''|*[!0-9a-f]*) log 'PAUSED: bad digest'; exit 0;; esac
  [ "${#expected}" -eq 64 ] || { log 'PAUSED: digest size'; exit 0; }
  [ -r "$origin" ] || { log 'PAUSED: APK not visible'; exit 0; }
  actual=$(sha256sum "$origin" 2>/dev/null | cut -d' ' -f1)
  [ "$actual" = "$expected" ] || { log "PAUSED: module payload not visible at $origin"; exit 0; }
  [ "$origin" != /system/system_ext/priv-app/SystemUI/SystemUI.apk ] || sysui_ok=1
  count=$((count+1))
done < "$MANIFEST"
[ "$count" -gt 0 ] || { log 'PAUSED: no APK mounted'; exit 0; }
umask 077
mkdir -p "$ROOT" || exit 0
chmod 0700 "$ROOT" 2>/dev/null || :
# Only activate the clock/pill flags on builds that contain *compiled*
# fixed SystemUI. Never turn these on after an RRO-only or Settings-only boot.
if [ "$sysui_ok" = 1 ] && [ ! -e "$ROOT/v06_ui_flags_applied" ]; then
  if settings --user 0 put secure clock_seconds 1 >/dev/null 2>&1 &&
     settings --user 0 put secure uwu_hide_gesture_handle 1 >/dev/null 2>&1; then
     : > "$ROOT/v06_ui_flags_applied"
  fi
fi
# Explicit user preference: 420 DPI. Validate reading before writing, and
# only write once. After a manual change, do not compete every boot.
if [ ! -e "$ROOT/v06_density_written" ]; then
  info=$(wm density 2>/dev/null) || { log 'ACTIVE: APKs mounted; WindowManager unreadable'; exit 0; }
  dpi=$(printf '%s\n' "$info" | sed -n 's/^Override density: *\([0-9][0-9]*\).*$/\1/p' | head -n 1)
  [ -n "$dpi" ] || dpi=$(printf '%s\n' "$info" | sed -n 's/^Physical density: *\([0-9][0-9]*\).*$/\1/p' | head -n 1)
  case "$dpi" in ''|*[!0-9]*) log 'ACTIVE: APKs mounted; DPI unparseable'; exit 0;; esac
  if [ "$dpi" != 420 ]; then
    if wm density 420 >/dev/null 2>&1; then
      : > "$ROOT/v06_density_written"
    else
      log 'ACTIVE: APKs mounted; wm density write failed'
      exit 0
    fi
  fi
fi
log "ACTIVE: $count compiled APK(s) verified, DPI target 420, SystemUI=$sysui_ok"
exit 0
