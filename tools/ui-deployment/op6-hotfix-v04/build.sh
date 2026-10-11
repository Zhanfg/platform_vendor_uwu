#!/bin/sh
# Host-only reproducible RRO + single KernelSU ZIP build. No arguments.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SDK=${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}
[ -n "$SDK" ] || { echo 'Android SDK missing' >&2; exit 2; }
BUILD_TOOLS="$SDK/build-tools/35.0.0"
AAPT2="$BUILD_TOOLS/aapt2"
ZIPALIGN="$BUILD_TOOLS/zipalign"
APKSIGNER="$BUILD_TOOLS/apksigner"
ANDROID_JAR="$SDK/platforms/android-35/android.jar"
for f in "$AAPT2" "$ZIPALIGN" "$APKSIGNER" "$ANDROID_JAR"; do
    [ -r "$f" ] || { echo "Missing SDK dependency: $f" >&2; exit 2; }
done
for bin in keytool zip unzip; do command -v "$bin" >/dev/null || exit 2; done
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
mkdir -p "$HERE/out"
"$AAPT2" compile --dir "$HERE/rro/res" -o "$WORK/rro-res.zip"
"$AAPT2" link -o "$WORK/rro-unsigned.apk" \
    -I "$ANDROID_JAR" --manifest "$HERE/rro/AndroidManifest.xml" \
    --min-sdk-version 31 --target-sdk-version 35 \
    --no-resource-deduping --no-resource-removal "$WORK/rro-res.zip"
"$ZIPALIGN" -f -p 4 "$WORK/rro-unsigned.apk" "$WORK/rro-aligned.apk"
keytool -genkeypair -noprompt -alias overlay -keyalg RSA -keysize 2048 \
    -validity 3650 -keystore "$WORK/overlay.jks" -storepass changeit \
    -keypass changeit -dname 'CN=uwuAOSP User Overlay, O=uwuAOSP, C=US' >/dev/null 2>&1
"$APKSIGNER" sign --ks "$WORK/overlay.jks" --ks-key-alias overlay \
    --ks-pass pass:changeit --key-pass pass:changeit \
    --out "$WORK/uwuGesturePillRRO.apk" "$WORK/rro-aligned.apk"
"$APKSIGNER" verify --verbose "$WORK/uwuGesturePillRRO.apk"
"$AAPT2" dump xmltree --file AndroidManifest.xml "$WORK/uwuGesturePillRRO.apk" > "$WORK/manifest-dump.txt"
grep -q 'com.android.systemui' "$WORK/manifest-dump.txt" || {
    echo 'Wrong RRO target' >&2; exit 4;
}
R="$WORK/pkg"
mkdir -p "$R/system/system_ext/overlay"
cp "$WORK/uwuGesturePillRRO.apk" "$R/system/system_ext/overlay/"
for f in module.prop customize.sh common.sh apply.sh service.sh \
         action.sh rro-verify.sh uninstall.sh options.conf README_CN.txt; do
    [ -f "$HERE/module/$f" ] || { echo "Missing module source: $f" >&2; exit 2; }
    cp "$HERE/module/$f" "$R/"
done
for f in "$R"/*.sh; do sh -n "$f"; chmod 0755 "$f"; done
OUT="$HERE/out/uwuAOSP hotfix v0.4.zip"
(cd "$R" && zip -X -q -9 -r "$OUT" module.prop customize.sh \
    common.sh apply.sh service.sh action.sh rro-verify.sh \
    uninstall.sh options.conf README_CN.txt system)
unzip -t "$OUT" >/dev/null
echo "Built: $OUT"
