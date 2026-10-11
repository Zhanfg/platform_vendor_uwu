#!/system/bin/sh
# KernelSU Installer entrypoint; sourced in the manager, no arguments.
ui_print '  uwuAOSP hotfix v0.7 - native KSU/Mountify'
case "$(getprop ro.product.device)" in OnePlus6|enchilada) :;; *) abort 'OnePlus 6 only';; esac
[ "$(getprop ro.build.version.sdk)" = 37 ] || abort 'Android 17 API 37 required'
[ "$(getprop ro.build.id)" = CP2A.260605.016 ] || abort 'Unknown ROM build; revalidate after OTA'
[ -d "$MODPATH" ] || abort 'KernelSU module installation path missing'
[ -s "$MODPATH/base-apks.sha256" ] || abort 'Empty signed-APK baseline manifest'
[ -s "$MODPATH/payload-apks.sha256" ] || abort 'Missing compiled APK digest manifest'
# One hotfix ID. The retired experimental developer ID may not be active
# alongside this module or the same privileged APK could be mounted twice.
OLD=/data/adb/modules/uwu-ui-hotfix
if [ -d "$OLD" ] && [ ! -e "$OLD/disable" ]; then
  abort 'Conflicting retired uwu-ui-hotfix module; disable/remove it first'
fi
for f in post-fs-data.sh late-load.sh service.sh action.sh; do
    [ -f "$MODPATH/$f" ] || abort "Missing $f"
    set_perm "$MODPATH/$f" 0 0 0755
done
ui_print '  Verified old APKs required; mount guard will check before every boot'
ui_print '  One system/ tree, zero LSPosed hooks or system partition writes'
