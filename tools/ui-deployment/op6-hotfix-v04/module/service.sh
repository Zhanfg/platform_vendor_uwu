#!/system/bin/sh
MODDIR=${0%/*}
/system/bin/sh "$MODDIR/apply.sh"
/system/bin/sh "$MODDIR/rro-verify.sh"
exit 0
