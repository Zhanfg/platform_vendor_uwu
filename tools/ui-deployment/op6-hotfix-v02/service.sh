#!/system/bin/sh
MODDIR=${0%/*}
# KernelSU late_start service: one shot. No resident watcher or process restarts.
exec /system/bin/sh "$MODDIR/apply.sh"
