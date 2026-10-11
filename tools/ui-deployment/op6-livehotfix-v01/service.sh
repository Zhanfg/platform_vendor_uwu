#!/system/bin/sh
MODDIR=${0%/*}
# Late-start service, one run per boot. No daemon or polling after setup.
exec /system/bin/sh "$MODDIR/apply.sh"
