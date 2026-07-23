#!/usr/bin/env bash
# Fetch the full clinical bundle for one patient from the EHR governance API.
# Reusable: takes the base URL and patient ID as arguments; contains no
# task-specific values. Source of truth for the base URL is environment_access.md.
#
# Usage: fetch_patient_bundle.sh <base_url> <patient_id>
# Example: fetch_patient_bundle.sh "http://task-env:9015" "P-12345"
#
# Only calls the allowed GET endpoints. Prints each resource labelled.

set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <base_url> <patient_id>" >&2
  exit 2
fi

BASE="${1%/}"
PID="$2"

for sub in "" "conditions" "medications" "allergies" "encounters" \
           "immunizations" "documents" "service-requests" "disclosures"; do
  if [ -z "$sub" ]; then
    echo "=== patient $PID ==="
    curl -s -m 20 "${BASE}/api/patients/${PID}"
  else
    echo "=== /api/patients/${PID}/${sub} ==="
    curl -s -m 20 "${BASE}/api/patients/${PID}/${sub}"
  fi
  echo
done
