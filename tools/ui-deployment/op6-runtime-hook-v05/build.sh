#!/bin/sh
# Reproducible unsigned sources; APK is signed with a build-specific test key.
# Key must be kept for future APK upgrades; use private persistent signing in production.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SDK="\${ANDROID_HOME:-\${ANDROID_SDK_ROOT:-}}"
[ -n "$SDK" ] || { echo "ANDROID_HOME missing" >&2; exit 2; }
TOOLS="$SDK/build-tools/35.0.0"
AAPT2="$TOOLS/aapt2"
D8="$TOOLS/d8"
ALIGN="$TOOLS/zipalign"
SIGN="$TOOLS/apksigner"
JAR="$SDK/platforms/android-35/android.jar"
for b in "$AAPT2" "$D8" "$ALIGN" "$SIGN" "$JAR"; do
    [ -r "$b" ] || { echo "Missing $b" >&2; exit 2; }
done
for x in javac jar zip keytool unzip; do command -v "$x" >/dev/null || exit 2; done
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT HUP INT TERM
mkdir -p "$ROOT/out" "$WORK/stubclasses" "$WORK/classes" "$WORK/dexout"
find "$ROOT/stubs" -name '*.java' > "$WORK/stubs.list"
javac -encoding UTF-8 -source 8 -target 8 -d "$WORK/stubclasses" @"$WORK/stubs.list"
jar cf "$WORK/xposed-api-compile-only.jar" -C "$WORK/stubclasses" .
find "$ROOT/src" -name '*.java' > "$WORK/sources.list"
javac -encoding UTF-8 -source 8 -target 8 -cp "$JAR:$WORK/xposed-api-compile-only.jar" \
    -d "$WORK/classes" @"$WORK/sources.list"
jar cf "$WORK/our-code.jar" -C "$WORK/classes" .
"$D8" --min-api 30 --lib "$JAR" --output "$WORK/dexout" "$WORK/our-code.jar"
"$AAPT2" compile --dir "$ROOT/res" -o "$WORK/resources.zip"
"$AAPT2" link -o "$WORK/unsigned.apk" -I "$JAR" \
    --manifest "$ROOT/AndroidManifest.xml" \
    --min-sdk-version 30 --target-sdk-version 35 "$WORK/resources.zip"
mkdir -p "$WORK/assets"
cp "$ROOT/assets/xposed_init" "$WORK/assets/"
(cd "$WORK" && zip -q "$WORK/unsigned.apk" dexout/classes.dex assets/xposed_init)
# ZIP entries must be at APK root, not nested under dexout.
(cd "$WORK" && zip -q -j "$WORK/unsigned.apk" dexout/classes.dex)
zip -dq "$WORK/unsigned.apk" dexout/classes.dex || :
"$ALIGN" -f -p 4 "$WORK/unsigned.apk" "$WORK/aligned.apk"
keytool -genkeypair -noprompt -alias hotfix -keyalg RSA -keysize 2048 -validity 3650 \
    -keystore "$WORK/hotfix.jks" -storepass changeit -keypass changeit \
    -dname 'CN=uwuAOSP User SystemUI Hook, O=uwuAOSP, C=US' >/dev/null 2>&1
OUT="$ROOT/out/uwuAOSP hotfix v0.5.apk"
"$SIGN" sign --ks "$WORK/hotfix.jks" --ks-key-alias hotfix \
    --ks-pass pass:changeit --key-pass pass:changeit \
    --out "$OUT" "$WORK/aligned.apk"
"$SIGN" verify --verbose "$OUT"
unzip -t "$OUT" >/dev/null
unzip -Z1 "$OUT" | grep -Fx 'classes.dex' >/dev/null
unzip -Z1 "$OUT" | grep -Fx 'assets/xposed_init' >/dev/null
if unzip -Z1 "$OUT" | grep -q 'de/robv/android/xposed'; then
    echo 'Xposed compile-only stubs leaked into APK' >&2; exit 1
fi
echo "Built $OUT"
