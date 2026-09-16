---
name: investigation-review-hub-json
description: Produce schema-conformant structured JSON legal review outputs from an Investigation Review Hub. Use for subpoena, grand jury, SEC, DOJ, production-readiness, retention, preservation, privilege-log, QC, custodian-source, and remediation dashboard tasks that require hub-only evidence, stable record IDs, category rollups, metrics, and prioritized action plans.
---

# Investigation Review Hub JSON

## Objective

Produce a single JSON object that conforms exactly to the task's local answer template by using the
running Investigation Review Hub as the source of record.

## Workflow

1. Read the prompt and every task-local payload. Extract the matter ID, base URL placeholder or
   provided base URL, optional SQL/API key header, required top-level keys, enum choices, field
   definitions, numeric precision, and ordering rules.
2. Do not inspect local environment source files, database files, generated manifests, hidden notes,
   evaluator code, prior answers, or standard answer files. Use only task-local payloads and hub
   endpoints.
3. Query the hub endpoints relevant to the template: schema, matters, categories, productions,
   custodian sources, documents/search, privilege log, QC findings, retention events, remediation
   actions, and the read-only SQL endpoint if the task permits it.
4. Build an evidence table keyed by stable hub IDs. Track each record's matter, affected categories,
   status, source/record type, dates, counts, production impact, privilege attributes, and proposed
   remediation.
5. Read [references/review-mapping.md](references/review-mapping.md) before selecting issues,
   computing category rollups, metrics, or action plans.
6. Fill only the keys required by the answer template. Use the template's exact field names, enums,
   sort orders, integer/null conventions, and JSON-only output rule.
7. Validate the final object against the template manually before responding: no prose, no extra keys
   unless allowed, all required keys present, sorted arrays, stable IDs unchanged, and metrics matching
   the selected evidence.

## Hub Collection Helper

Use the optional helper when a quick endpoint snapshot is useful:

```bash
python3 skill/scripts/collect_review_hub.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --matter-id "$MATTER_ID" \
  --api-key-header "$HEADER_NAME" \
  --api-key "$API_KEY" \
  --out /tmp/review_hub_snapshot.json
```

Omit `--api-key-header` and `--api-key` when the task does not provide them. The helper retries
standard GET endpoints with and without a `matter_id` query parameter and records failures instead of
guessing facts.

## Output Discipline

- Treat the answer template as authoritative over any general legal-review expectation.
- Prefer hub-provided remediation records for action IDs, owners, ranks, priorities, and due dates.
- Keep every category-code list and record-reference list sorted unless the template states another
  order.
- Use `0` for non-applicable numeric counts and `null` only for fields whose template allows null.
- Return exactly one JSON object and no markdown, comments, or explanatory text when the task asks
  for JSON only.
