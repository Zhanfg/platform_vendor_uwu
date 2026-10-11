#!/bin/sh
# Host-only, no-arguments reproducible installer creation.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
for name in module.prop customize.sh options.conf service.sh apply.sh \
        action.sh restore.sh uninstall.sh README_CN.txt; do
    [ -f "$HERE/$name" ] || { echo "Missing $name" >&2; exit 1; }
done
for file in "$HERE"/*.sh; do sh -n "$file" || exit 1; done
OUTPUT="$HERE/uwuAOSP_OP6_UI_LiveHotfix_v0.1_KSU.zip"
(cd "$HERE" && zip -X -9 -q -r "$OUTPUT" \
    module.prop customize.sh options.conf service.sh apply.sh \
    action.sh restore.sh uninstall.sh README_CN.txt)
unzip -t "$OUTPUT" >/dev/null
printf 'Built: %s\n' "$OUTPUT"
