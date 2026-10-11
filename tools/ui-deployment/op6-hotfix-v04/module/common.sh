#!/system/bin/sh
# Production tools resolve only Android executables. CI can supply mock tools
# with an explicit test marker; never source untrusted external config.
if [ "${UWU_HOTFIX_TESTING:-0}" = 1 ]; then
  PATH="${UWU_HOTFIX_TEST_BIN:?}:$PATH"
  STATE_DIR="${UWU_HOTFIX_TEST_STATE:?}"
  WAIT_LIMIT=0
else
  PATH="/system/bin:/system/xbin:/vendor/bin:/product/bin:/sbin:$PATH"
  STATE_DIR=/data/adb/uwu-ui-live-hotfix-state
  WAIT_LIMIT=45
fi
export PATH
umask 077
log_status() {
  mkdir -p "$STATE_DIR" 2>/dev/null || return 0
  printf '%s\n' "$1" > "$STATE_DIR/last_status.txt" 2>/dev/null || :
}
valid_target() {
  case "$(getprop ro.product.device 2>/dev/null)" in OnePlus6|enchilada) :;; *) return 1;; esac
  [ "$(getprop ro.build.version.sdk 2>/dev/null)" = 37 ]
}
read_secure() { settings --user 0 get secure "$1" 2>/dev/null; }
restore_secure() {
  case "$2" in
    null) settings --user 0 delete secure "$1" >/dev/null 2>&1 ;;
    0|1) settings --user 0 put secure "$1" "$2" >/dev/null 2>&1 ;;
    *) return 1 ;;
  esac
}
# Check wm output; an incomplete Binder response must never be treated as a
# reason to write arbitrary dpi values.
read_density() {
  WM_RESULT=$(wm density 2>&1) || return 1
  EFFECTIVE_DPI=$(printf '%s\n' "$WM_RESULT" | sed -n 's/^Override density: *\([0-9][0-9]*\).*$/\1/p' | head -n 1)
  [ -n "$EFFECTIVE_DPI" ] || EFFECTIVE_DPI=$(printf '%s\n' "$WM_RESULT" | sed -n 's/^Physical density: *\([0-9][0-9]*\).*$/\1/p' | head -n 1)
  case "$EFFECTIVE_DPI" in ''|*[!0-9]*) return 1;; esac
  [ "$EFFECTIVE_DPI" -ge 200 ] && [ "$EFFECTIVE_DPI" -le 800 ] || return 1
}
