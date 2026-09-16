# Final Answer Checks

Before returning the final JSON:

1. Start from the required keys in `payloads/answer_template.json`. Do not add top-level or nested keys the template forbids.
2. Check every requested focus id, scoped decision id, watchlist id, alias id, transaction id, charge id, event id, control case, and ranking limit from `case_scope.json` is represented exactly once where required.
3. Enforce ordering:
   - lexicographic id arrays and grouped ids
   - template-specific rank ordering
   - source snapshot id arrays sorted lexicographically
   - focus panels sorted by the template's id field
4. Reconcile counts:
   - raw rows equal fetched in-scope rows
   - logical rows equal distinct retained logical ids
   - duplicate raw count equals raw minus logical where applicable
   - valid plus quarantine/unresolved/invalid partitions match the template's definitions
   - grouped readiness disposition counts sum to their total populations
5. Recompute monetary and physical totals from retained, non-quarantined logical rows and compare aggregate totals to per-class sums after rounding tolerance.
6. Ensure code fields use only enums allowed by the template and match the evidence condition in `references/codes.md`.
7. Validate the final object with Python:

```bash
python -m json.tool answer.json >/dev/null
```

If the template is JSON Schema and `jsonschema` is available:

```bash
python - <<'PY'
import json, sys
import jsonschema
schema = json.load(open("payloads/answer_template.json"))
answer = json.load(open("answer.json"))
jsonschema.validate(answer, schema)
PY
```

Return only the JSON object. No Markdown, no comments, no explanation.
