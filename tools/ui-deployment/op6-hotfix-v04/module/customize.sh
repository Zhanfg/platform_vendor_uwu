#!/system/bin/sh
ui_print '  uwuAOSP hotfix v0.4'
case "$(getprop ro.product.device)" in OnePlus6|enchilada) :;; *) abort 'OnePlus 6 only';; esac
[ "$(getprop ro.build.version.sdk)" = 37 ] || abort 'Requires Android 17 (API 37)'
[ "$(getprop ro.build.id)" = "CP2A.260605.016" ] || abort 'Unverified ROM baseline, refusing SystemUI overlay'
BASE=/system/system_ext/priv-app/SystemUI/SystemUI.apk
[ -r "$BASE" ] || abort 'SystemUI APK missing or unreadable'
actual=$(sha256sum "$BASE" 2>/dev/null | cut -d' ' -f1)
[ "$actual" = "47e4e849e99a695b3c698566fb451cf3cd671ddb17f3e5844d15b2b35188f841" ] ||
    abort 'SystemUI mismatch, overlay not installed'
[ -f "$MODPATH/system/system_ext/overlay/uwuGesturePillRRO.apk" ] ||
    abort 'Overlay payload missing'
for f in service.sh apply.sh common.sh action.sh rro-verify.sh uninstall.sh; do
    [ -f "$MODPATH/$f" ] || abort "Missing $f"
    set_perm "$MODPATH/$f" 0 0 0755
done
set_perm "$MODPATH/system/system_ext/overlay/uwuGesturePillRRO.apk" 0 0 0644
set_perm "$MODPATH/options.conf" 0 0 0644
# Previous v0.1-v0.3 modules deliberately had no system payload.
rm -f "$MODPATH/skip_mount"
ui_print '  Systemless RRO: visual handle radius=0, gesture region preserved'
ui_print '  Mountify TMPFS required; this is an experimental first RRO build'
ui_print '  No APK override, no platform signature replacement'
