#!/system/bin/sh
# Shell helpers. Never source options.conf as shell code.
if [ "${UWU_HOTFIX_TESTING:-0}" = 1 ]; then
    PATH="${UWU_HOTFIX_TEST_PATH:-/system/bin}:$PATH"
    STATE_DIR="${UWU_HOTFIX_TEST_STATE_DIR:?}"
    MAX_WAIT="${UWU_HOTFIX_TEST_MAX_WAIT:-20}"
else
    PATH="/system/bin:/system/xbin:/vendor/bin:/product/bin:/sbin:$PATH"
    STATE_DIR=/data/adb/uwu-ui-live-hotfix-state
    MAX_WAIT=30
fi
export PATH
umask 077

hotfix_log() {
    mkdir -p "$STATE_DIR" 2>/dev/null || return 0
    printf '%s\n' "$1" > "$STATE_DIR/last_status.txt" 2>/dev/null || :
}

hotfix_supported() {
    case "$(getprop ro.product.device 2>/dev/null)" in
        OnePlus6|enchilada) : ;;
        *) return 1 ;;
    esac
    [ "$(getprop ro.build.version.sdk 2>/dev/null)" = 37 ]
}

hotfix_setting_get() {
    settings --user 0 get secure "$1" 2>/dev/null
}
hotfix_setting_put() {
    settings --user 0 put secure "$1" "$2" >/dev/null 2>&1
}
hotfix_setting_restore() {
    case "$2" in
        null) settings --user 0 delete secure "$1" >/dev/null 2>&1 ;;
        0|1) hotfix_setting_put "$1" "$2" ;;
        *) return 1 ;;
    esac
}
hotfix_enabled() {
    grep -Fxq "$1=1" "$MODDIR/options.conf" 2>/dev/null
}
hotfix_atomic_save() {
    # Args: path value. No append; the exact original is kept across upgrades.
    _hs_file="$1"
    _hs_value="$2"
    _hs_temp="$_hs_file.tmp.$$"
    printf '%s\n' "$_hs_value" > "$_hs_temp" || return 1
    chmod 0600 "$_hs_temp" 2>/dev/null || :
    mv -f "$_hs_temp" "$_hs_file"
}
