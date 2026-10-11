#!/system/bin/sh
# KernelSU-Next late-load mode may skip post-fs-data.sh.
# Run exactly the same fail-closed compatibility check before metamodule mounts.
MODDIR=${0%/*}
exec /system/bin/sh "$MODDIR/post-fs-data.sh"
