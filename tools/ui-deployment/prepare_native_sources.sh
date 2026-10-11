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
# Shared Material 3 Expressive Switch palette: use onSurfaceVariant for
# legible off-state thumbs and the same tonal track color for its border.
# This patches the common Compose component, not dozens of individual
# Settings/Prism screens; it does not add LSP hooks or runtime listeners.
SWITCH_PATCH="$SRC/patches/uwu-sdk-md3e-switch-contrast.patch"
[ -r "$SWITCH_PATCH" ] || { echo 'Missing MD3E switch patch' >&2; exit 2; }
if git -C "$ANDROID_ROOT/uwu-sdk" apply --reverse --check "$SWITCH_PATCH" 2>/dev/null; then
  echo 'Already patched: MD3E Switch off-state dynamic palette'
else
  git -C "$ANDROID_ROOT/uwu-sdk" apply --check "$SWITCH_PATCH" ||
    { echo 'Wrong uwu-sdk source or conflicting Switch styles' >&2; exit 4; }
  git -C "$ANDROID_ROOT/uwu-sdk" apply "$SWITCH_PATCH"
  echo 'Applied: MD3E Switch off-state dynamic palette'
fi

# Shared MD3E search and dialog inputs: consistent dynamic tonal fill, a
# visible primary focus outline, and a low-contrast unfocused border.
# Keep the underlying layout and input geometry stable at 420 dpi.
INPUT_PATCH="$SRC/patches/uwu-sdk-md3e-input-tonal-focus.patch"
[ -r "$INPUT_PATCH" ] || { echo 'Missing MD3E input component patch' >&2; exit 2; }
if git -C "$ANDROID_ROOT/uwu-sdk" apply --reverse --check "$INPUT_PATCH" 2>/dev/null; then
  echo 'Already patched: MD3E shared input dynamic focus'
else
  git -C "$ANDROID_ROOT/uwu-sdk" apply --check "$INPUT_PATCH" ||
    { echo 'Wrong uwu-sdk source or conflicting input styling' >&2; exit 4; }
  git -C "$ANDROID_ROOT/uwu-sdk" apply "$INPUT_PATCH"
  echo 'Applied: MD3E shared search/dialog input focus treatment'
fi

# ThemePicker/uwuPrism are a second signing domain. The original files
# were found and hashed in the user-provided ROM101 reference archive, so
# ThemePicker must now be built at the pinned MD3E accessibility revision.
# The product uwuPrism RRO is kept unchanged and verified at mount time.
lock packages/apps/ThemePicker 0859e053a7de17180b4e8168705732b46515b787 ThemePicker
echo 'Native source gate READY. Compile in the full Android 17 tree using'
echo 'the ROM-compatible platform/Launcher/ThemePicker signing configuration.'
echo 'Never replace the installed privileged APK if signer identity differs.'
