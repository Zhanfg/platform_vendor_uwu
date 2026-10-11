#!/system/bin/sh
# Sourced by KernelSU module installer; no writes to system partitions.
ui_print '  uwuAOSP hotfix v0.2'
case "$(getprop ro.product.device)" in
    OnePlus6|enchilada) : ;;
    *) abort 'Only OnePlus 6 (enchilada) is supported' ;;
esac
[ "$(getprop ro.build.version.sdk)" = 37 ] || abort 'Requires Android 17 (API 37)'
[ -d "$MODPATH" ] || abort 'KernelSU module path missing'
for file in service.sh apply.sh action.sh restore.sh common.sh uninstall.sh; do
    [ -f "$MODPATH/$file" ] || abort "Incomplete archive: $file"
    set_perm "$MODPATH/$file" 0 0 0755
done
set_perm "$MODPATH/options.conf" 0 0 0644
: > "$MODPATH/skip_mount" || abort 'Cannot set skip_mount'
ui_print '  No system APK, no Mountify TMPFS memory copy'
ui_print '  Settings originals remain outside module root across upgrades'
ui_print '  Reboot to apply once after Android starts'
