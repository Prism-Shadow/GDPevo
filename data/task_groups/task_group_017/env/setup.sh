#!/usr/bin/env bash
set -euo pipefail

cd /app
python generate_data.py
exec python app.py
