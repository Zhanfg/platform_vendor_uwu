#!/system/bin/sh
# Optional KernelSU "Action" panel / no-argument terminal menu.
# Moves an APK between enabled system/ and disabled inactive/system/,
# without duplicating file bytes. Changes apply on the NEXT reboot.
MODDIR=${0%/*}
[ -d "$MODDIR" ] || { echo "Cannot locate module"; exit 1; }
[ -f "$MODDIR/base-apks.sha256" ] || { echo "Missing component manifest"; exit 1; }
show_one() {
    label="$1"
    target="$2"
    enabled="$MODDIR/system/$target"
    parked="$MODDIR/inactive/system/$target"
    if [ -f "$enabled" ]; then
        state=ON
    elif [ -f "$parked" ]; then
        state=OFF
    else
        state=NOT_INCLUDED
    fi
    printf '%-16s %s\n' "$label" "$state"
}
echo "uwuAOSP UI Hotfix component manager"
[ -e "$MODDIR/skip_mount" ] && echo "OTA GUARD: PAUSED; component toggles cannot override this lock"
show_one SystemUI system_ext/priv-app/SystemUI/SystemUI.apk
show_one Settings system_ext/priv-app/Settings/Settings.apk
show_one Launcher3 system_ext/priv-app/Launcher3QuickStep/Launcher3QuickStep.apk
show_one uwuSettingsExt system_ext/priv-app/uwuSettingsExt/uwuSettingsExt.apk
echo "Choose a component to toggle: 1=SystemUI 2=Settings 3=Launcher3 4=uwuSettingsExt 0=cancel"
IFS= read -r choice || exit 0
case "$choice" in
  1) target=system_ext/priv-app/SystemUI/SystemUI.apk ;;
  2) target=system_ext/priv-app/Settings/Settings.apk ;;
  3) target=system_ext/priv-app/Launcher3QuickStep/Launcher3QuickStep.apk ;;
  4) target=system_ext/priv-app/uwuSettingsExt/uwuSettingsExt.apk ;;
  0|"") exit 0 ;;
  *) echo "Invalid choice"; exit 1 ;;
esac
grep -Fqx "/system/$target|$(sed -n "s@^/system/$target|@@p" "$MODDIR/base-apks.sha256")" "$MODDIR/base-apks.sha256" ||
    { echo "Component not included in this package"; exit 1; }
on="$MODDIR/system/$target"
off="$MODDIR/inactive/system/$target"
if [ -f "$on" ]; then
    mkdir -p "$(dirname "$off")" || exit 1
    mv "$on" "$off" || exit 1
    echo "Component DISABLED for next boot. APK moved, not duplicated."
elif [ -f "$off" ]; then
    mkdir -p "$(dirname "$on")" || exit 1
    mv "$off" "$on" || exit 1
    echo "Component ENABLED for next boot, subject to compatibility guard."
else
    echo "No staged APK found"; exit 1
fi
echo "Reboot required. ROM slots and original system files are untouched."
