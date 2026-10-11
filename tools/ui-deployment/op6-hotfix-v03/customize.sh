#!/system/bin/sh
# KernelSU's module installer sources customize.sh.
ui_print '  uwuAOSP hotfix v0.3 (stability first)'
case "$(getprop ro.product.device)" in
  OnePlus6|enchilada) : ;;
  *) abort 'Only OnePlus 6 (enchilada) is supported' ;;
esac
[ "$(getprop ro.build.version.sdk)" = 37 ] || abort 'Requires Android 17 (API 37)'
[ -d "$MODPATH" ] || abort 'KernelSU module path missing'
for f in service.sh apply.sh common.sh action.sh uninstall.sh; do
  [ -f "$MODPATH/$f" ] || abort "Missing $f"
  set_perm "$MODPATH/$f" 0 0 0755
done
set_perm "$MODPATH/options.conf" 0 0 0644
: > "$MODPATH/skip_mount" || abort 'Failed to set skip_mount'
ui_print '  Retains stable module ID; installs over v0.1/v0.2'
ui_print '  Unverified gesture/clock forcing is removed; reboot to apply'
ui_print '  DPI 420 applied only if verified and safe to adjust'
