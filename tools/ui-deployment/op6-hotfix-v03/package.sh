#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OUTPUT="$ROOT/out/uwuAOSP hotfix v0.3.zip"
mkdir -p "$ROOT/out"
for f in module.prop options.conf customize.sh common.sh service.sh apply.sh action.sh uninstall.sh README_CN.txt; do
  [ -f "$ROOT/$f" ] || { echo "Missing $f" >&2; exit 1; }
done
for f in "$ROOT"/*.sh; do sh -n "$f"; done
(cd "$ROOT" && zip -X -q -9 "$OUTPUT" module.prop options.conf customize.sh common.sh service.sh apply.sh action.sh uninstall.sh README_CN.txt)
unzip -t "$OUTPUT" >/dev/null
printf '%s\n' "$OUTPUT"
