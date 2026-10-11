#!/bin/sh
# No arguments. Run from the root of the exactly synced Android 17.0.101 tree.
# Fail closed: do not patch moving heads or silently compile mixed MD3E versions.
set -eu
ANDROID_ROOT=${ANDROID_BUILD_TOP:-"$PWD"}
[ -d "$ANDROID_ROOT/.repo" ] || { echo 'Run from the ROM .repo checkout root' >&2; exit 2; }
SRC=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
lock() {
  path="$1"; expected="$2"; label="$3"
  [ -d "$ANDROID_ROOT/$path/.git" ] || [ -f "$ANDROID_ROOT/$path/.git" ] ||
      { echo "Missing synced $label project: $path" >&2; exit 2; }
  sha=$(git -C "$ANDROID_ROOT/$path" rev-parse HEAD)
  [ "$sha" = "$expected" ] || {
    echo "BLOCKED: $label source is $sha, expected $expected" >&2
    echo 'Re-sync or checkout the pinned integration SHA before compiling.' >&2
    exit 3
  }
  echo "PIN OK: $label $sha"
}
lock frameworks/base 5f78233070530b853fcc6501776f19d00393ca63 SystemUI
lock packages/apps/Settings c3cfe7b63318bb17f6e8e542f4a7e33e1b38f94d Settings
lock packages/apps/Launcher3 601c7068193663506e154f1333f7dcc070f7fb49 Launcher3
lock packages/apps/uwuSettingsExt 289a20b44e68ce8b3836335b32793bbfd243213c uwuSettingsExt
lock uwu-sdk 75c696d97527dfbf5fd89471ae6ea1a13aeee4fd uwu-sdk
PATCH="$SRC/patches/uwu-sdk-md3e-a11y.patch"
[ -r "$PATCH" ] || { echo 'Missing pinned uwuCompose patch' >&2; exit 2; }
if git -C "$ANDROID_ROOT/uwu-sdk" apply --reverse --check "$PATCH" 2>/dev/null; then
  echo 'Already patched: uwuCompose navigate-up TalkBack label'
else
  git -C "$ANDROID_ROOT/uwu-sdk" apply --check "$PATCH" ||
    { echo 'Wrong uwu-sdk source or conflicting MD3E changes' >&2; exit 4; }
  git -C "$ANDROID_ROOT/uwu-sdk" apply "$PATCH"
  echo 'Applied: uwuCompose navigate-up native accessibility patch'
fi
# ThemePicker/uwuPrism are a second signing domain. The original files
# were found and hashed in the user-provided ROM101 reference archive, so
# ThemePicker must now be built at the pinned MD3E accessibility revision.
# The product uwuPrism RRO is kept unchanged and verified at mount time.
lock packages/apps/ThemePicker 0859e053a7de17180b4e8168705732b46515b787 ThemePicker
echo 'Native source gate READY. Compile in the full Android 17 tree using'
echo 'the ROM-compatible platform/Launcher/ThemePicker signing configuration.'
echo 'Never replace the installed privileged APK if signer identity differs.'
