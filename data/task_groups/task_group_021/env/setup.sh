#!/bin/sh
set -eu

BASE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DB_PATH="$BASE_DIR/data/asteria_quality.db"
MANIFEST_PATH="$BASE_DIR/manifest.json"
TRUTH_PATH="$BASE_DIR/construction_truth.json"

if [ "${1:-}" = "--regenerate" ]; then
    python3 "$BASE_DIR/generate_data.py" \
        --output "$DB_PATH" \
        --manifest "$MANIFEST_PATH" \
        --truth "$TRUTH_PATH"
    shift
fi

if [ ! -f "$DB_PATH" ] || [ ! -f "$MANIFEST_PATH" ] || [ ! -f "$TRUTH_PATH" ]; then
    python3 "$BASE_DIR/generate_data.py" \
        --output "$DB_PATH" \
        --manifest "$MANIFEST_PATH" \
        --truth "$TRUTH_PATH"
fi

python3 "$BASE_DIR/generate_data.py" \
    --verify \
    --output "$DB_PATH" \
    --manifest "$MANIFEST_PATH" \
    --truth "$TRUTH_PATH"

exec python3 "$BASE_DIR/service.py" "$@"
