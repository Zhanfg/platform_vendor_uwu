#!/system/bin/sh
# KernelSU Manager installation script: sourced by the installer.
# NO recovery installation and NO mutation of boot/system partitions.
ui_print '  uwuAOSP 17 | OnePlus 6 UI Live Hotfix v0.1'
DEVICE="$(getprop ro.product.device)"
MODEL="$(getprop ro.product.model)"
SDK="$(getprop ro.build.version.sdk)"
case "$DEVICE" in
  OnePlus6|enchilada) ;;
  *) abort "Unsupported device: $DEVICE ($MODEL). Requires OnePlus 6." ;;
esac
[ "$SDK" = 37 ] || abort "Unsupported API level: $SDK. Requires Android 17 (API 37)."
ui_print '  Supported: OnePlus 6 / Android 17'
ui_print '  No system payload, no Mountify RAM copy, no slot/OTA change'
ui_print '  Default: seconds ON; hide gesture hint REQUESTED'
# Only user-facing Android Secure settings are changed after boot.
# Module manager installs this ZIP to /data/adb/modules_update/$MODID.
[ -d "$MODPATH" ] || abort 'Module path missing'
for name in service.sh apply.sh action.sh uninstall.sh restore.sh; do
    [ -f "$MODPATH/$name" ] || abort "Incomplete package: $name"
    set_perm "$MODPATH/$name" 0 0 0755
 done
set_perm "$MODPATH/options.conf" 0 0 0644
# The module has no system/ tree. Mountify TMPFS is not needed.
: > "$MODPATH/skip_mount"
ui_print '  Reboot once after installing. Existing settings backed up on first successful run.'
