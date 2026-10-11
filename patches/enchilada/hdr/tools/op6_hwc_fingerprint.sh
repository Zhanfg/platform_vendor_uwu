#!/system/bin/sh
# OnePlus 6 / uwuAOSP 17.0 - Qualcomm HWC provenance probe.
# Read only; no arguments; no su required; does not touch boot, dtbo or vendor.
PATH=/system/bin:/system/xbin:/vendor/bin:/vendor/bin/hw:/product/bin:/sbin:$PATH
export PATH
umask 077
TS=$(date +%Y%m%d_%H%M%S 2>/dev/null)
[ -n "$TS" ] || TS=unknown
DEST=/sdcard/Download
[ -d "$DEST" ] || DEST=.
OUT="$DEST/OP6_HWC_Fingerprint_$TS.txt"

section() { printf '\n========== %s ==========\n' "$1"; }
property() { printf '%s=' "$1"; getprop "$1" 2>/dev/null; }
record_file() {
    f="$1"
    [ -f "$f" ] || return 0
    echo "FILE: $f"
    ls -lZ "$f" 2>/dev/null || ls -l "$f" 2>/dev/null || :
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$f" 2>/dev/null || echo "SHA256 unavailable"
    fi
    for reader in llvm-readelf readelf; do
        if command -v "$reader" >/dev/null 2>&1; then
            "$reader" -n "$f" 2>/dev/null |
                grep -i -A 2 -B 1 'build id' | head -n 8 || :
            break
        fi
    done
}
{
    echo "OnePlus 6 HDR HWC file identity probe - READ ONLY"
    echo "This probe does not require HDR content and never writes system settings."
    section "Device build (selected properties only)"
    for k in ro.product.device ro.build.version.release ro.build.id ro.vendor.build.id ro.vendor.build.version.incremental ro.vendor.build.security_patch ro.hardware; do
        property "$k"
    done
    section "Composer / mapper / gralloc component hashes"
    for f in \
        /vendor/bin/hw/vendor.qti.hardware.display.composer-service \
        /vendor/lib64/libsdmcore.so \
        /vendor/lib64/libsdmutils.so \
        /vendor/lib64/libdisplayconfig.qti.so \
        /vendor/lib64/libqservice.so \
        /vendor/lib64/libqdutils.so \
        /vendor/lib64/libgrallocutils.so \
        /vendor/lib64/hw/gralloc.qcom.so \
        /vendor/lib64/hw/android.hardware.graphics.mapper@4.0-impl-qti-display.so; do
        record_file "$f"
    done
    section "Composer init service declarations"
    for f in /vendor/etc/init/*composer*.rc /vendor/etc/init/hw/*composer*.rc; do
        [ -r "$f" ] || continue
        echo "RC: $f"
        grep -E '^service |^    /vendor/bin/hw/|^    class |^    user |^    group |^    seclabel ' "$f" |
            head -n 25 || :
    done
    section "Vendor graphics service status"
    for k in init.svc.vendor.qti.hardware.display.composer init.svc.surfaceflinger init.svc.vendor.qti.hardware.display.allocator; do
        property "$k"
    done
    section "Relevant panel display configuration file paths"
    for d in /vendor/etc/displayconfig /odm/etc/displayconfig /product/etc/displayconfig \
             /vendor/etc /odm/etc /product/etc; do
        [ -d "$d" ] || continue
        ls "$d" 2>/dev/null | grep -i -E 'displayconfig|qdcm|hdr|color.*xml|brightness' |
            head -n 35 | sed "s|^|$d/|" || :
    done
    section "Existing read-only color-mode status"
    dumpsys display 2>/dev/null |
        grep -i -E 'supportedColorModes|hdrSdrRatio|mHdrBrightnessData' |
        cut -c 1-320 | head -n 12 || :
    echo
    echo "Do not install any new vendor composer binary until ABI and rollback are validated."
} > "$OUT" 2>&1
echo "Saved: $OUT"
