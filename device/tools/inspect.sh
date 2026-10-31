#!/bin/sh
# Slickk-OS P0-003. No root, flash, unlock, dump, write partition, or identifiers.
set -eu
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: sh device/tools/inspect.sh OUTPUT.json [termux|adb]" >&2
  exit 2
fi
OUTPUT=$1
MODE=${2:-termux}
case "$MODE" in termux|adb) ;; *) echo "mode must be termux or adb" >&2; exit 2 ;; esac
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$SCRIPT_DIR/compat.py" collect --mode "$MODE" --output "$OUTPUT"
