#!/bin/sh
# OnePlus 6 Android 17 HWC build-tree preparation, no parameters.
# Run ONLY in a fully synced Android 17 build workspace after lunch enchilada.
# Modifies a local SOURCE working tree, never a device, vendor image or boot.
set -eu
say() { printf '%s\n' "$*"; }
fail() { say "ERROR: $*" >&2; exit 1; }
case "$(printenv TARGET_PRODUCT 2>/dev/null)" in
  *enchilada*) ;;
  *) fail "TARGET_PRODUCT must identify enchilada; load envsetup.sh and lunch first" ;;
esac
R="$PWD"
while [ ! -d "$R/hardware/qcom/sm7250/display" ] ||
      [ ! -f "$R/vendor/uwu/patches/enchilada/hdr/0001-legacy-hdr-render-intent.patch" ]; do
  [ "$R" != "/" ] || fail "No matching Android build workspace found"
  R="$(dirname "$R")"
done
SRC="$R/hardware/qcom/sm7250/display"
PATCH="$R/vendor/uwu/patches/enchilada/hdr/0001-legacy-hdr-render-intent.patch"
[ -f "$SRC/composer/hwc_display.cpp" ] || fail "Wrong HWC source layout"
grep -q 'void HWCColorMode::PopulateColorModes()' "$SRC/composer/hwc_display.cpp" ||
  fail "Expected Qualcomm HWC parser not present"
[ -d "$SRC/.git" ] || [ -f "$SRC/.git" ] ||
  fail "Cannot verify repository identity"
ORIGIN="$(git -C "$SRC" remote get-url origin 2>/dev/null || true)"
case "$ORIGIN" in
  *LineageOS/android_hardware_qcom_sm7250_display*|*Zhanfg/android_hardware_qcom_sm7250_display*) ;;
  *) fail "Unexpected HWC source origin: $ORIGIN" ;;
esac
BASE="$(git -C "$SRC" rev-parse HEAD)"
say "Source HEAD: $BASE"
say "Expected reference: d3fae6913731a30c135a6cd1fab803913da06998"
[ "$BASE" = "d3fae6913731a30c135a6cd1fab803913da06998" ] ||
  fail "HWC commit differs from the audited reference; review/retarget patch first"
if git -C "$SRC" apply --reverse --check "$PATCH" 2>/dev/null; then
  say "Already patched. No changes made."
elif git -C "$SRC" apply --check "$PATCH" 2>/dev/null; then
  [ -z "$(git -C "$SRC" status --porcelain -- composer/hwc_display.cpp)" ] ||
    fail "HWC source file is dirty; refusing to overwrite local modifications"
  git -C "$SRC" apply "$PATCH"
  say "Patched local HWC source only."
else
  fail "Patch does not apply or working tree diverged"
fi
[ -f "$R/build/envsetup.sh" ] || fail "Missing Android build infrastructure"
say "Source preparation OK. Next (from build root):"
say "  source build/envsetup.sh"
say "  lunch <your-existing-uwu-enchilada-target>"
say "  m vendor.qti.hardware.display.composer-service"
say "Do not deploy the resulting ELF until ABI, SELinux, VINTF and rollback gates pass."
