#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$ROOT/out"
OUTPUT="$ROOT/out/uwuAOSP hotfix v0.2.zip"
for file in module.prop customize.sh common.sh service.sh apply.sh action.sh restore.sh uninstall.sh options.conf README_CN.txt; do
    [ -f "$ROOT/$file" ] || { echo "Missing $file" >&2; exit 1; }
done
for f in "$ROOT"/*.sh; do sh -n "$f"; done
(cd "$ROOT" && zip -X -q -9 "$OUTPUT" \
   module.prop customize.sh common.sh service.sh apply.sh action.sh restore.sh uninstall.sh options.conf README_CN.txt)
unzip -t "$OUTPUT" >/dev/null
printf '%s\n' "$OUTPUT"
