#!/system/bin/sh
# Read-only KernelSU Action: one atomic, coherent five-component UI release.
# Use the KernelSU Manager module enable/disable control to roll back ALL
# components together. Never mix half-old SystemUI with half-new Settings.
MODDIR=${0%/*}
echo 'uwuAOSP hotfix v0.7 — native MD3E/SystemUI'
echo 'Mountify TMPFS / KernelSU; no LSPosed hooks.'
echo
[ -r "$MODDIR/module.prop" ] || { echo 'Module metadata missing'; exit 1; }
[ ! -e "$MODDIR/skip_mount" ] || echo 'OTA GUARD: PAUSED (not mounted)'
[ ! -e "$MODDIR/disable" ] || echo 'Module disabled'
if [ -r "$MODDIR/last_guard_status.txt" ]; then
  echo 'Before-mount gate:'
  cat "$MODDIR/last_guard_status.txt"
fi
if [ -r "$MODDIR/last_runtime_status.txt" ]; then
  echo 'Live payload / UI status:'
  cat "$MODDIR/last_runtime_status.txt"
fi
echo
for f in SystemUI Settings Launcher3QuickStep uwuSettingsExt ThemePicker; do
  case "$f" in
    Launcher3QuickStep) dest=Launcher3QuickStep/Launcher3QuickStep.apk ;;
    *) dest="$f/$f.apk" ;;
  esac
  if [ -r "$MODDIR/system/system_ext/priv-app/$dest" ]; then
    echo "$f: staged"
  else
    echo "$f: missing (incomplete build!)"
  fi
done
echo
echo 'To disable ALL changes, toggle this single module in KernelSU Manager.'
echo 'Never toggle individual APKs; preserve cross-component MD3E consistency.'
exit 0
