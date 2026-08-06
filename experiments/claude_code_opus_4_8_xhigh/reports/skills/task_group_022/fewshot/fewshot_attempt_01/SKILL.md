---
name: atlas-ops-reporting
description: >-
  Produce exact JSON answers for Atlas Commerce Operations analytical and
  data-correction requests. Use whenever a task points at an authenticated
  "Atlas Commerce Operations" / "Atlas workplace" service (a base URL plus a
  Bearer token in environment_access.md, exposing /api/schema,
  /api/data-dictionary, /api/sql, /api/sql/transaction, and
  /api/correction-audit) and asks you to compute a scorecard, reconciliation,
  productivity/health review, backlog, or minimal canonical correction against
  a supplied request payload and answer_template.json, writing the result to
  answer.json. Covers fulfillment scorecards, refund/settlement reconciliation,
  carrier-quality corrections, warehouse productivity, and support-health
  reviews.
---

# Atlas Commerce Operations reporting & correction

You are given an analytical (sometimes correction) request against a live
"Atlas Commerce Operations" database reached over the network. Each task ships:

- `prompt.txt` — the business ask and pointers to the files below.
- `input/payloads/<something>_request.json` — the **authoritative** scope,
  business definitions, rollups, rounding, ordering, thresholds, and status
  rules. Treat this JSON as the spec; the prose in `prompt.txt` only summarizes it.
- `input/payloads/answer_template.json` — a JSON Schema the output must satisfy
  **exactly**.
- `environment_access.md` — base URL, `Authorization: Bearer <token>`, and the
  list of API endpoints.

Your job: compute the required figures from the live database and write **one**
JSON object to `answer.json` that conforms to `answer_template.json`, with no
prose or extra keys.

## The API (transport)

Read `environment_access.md` for the base URL and bearer token. Every request
needs `Authorization: Bearer <token>` (missing token → `401 unauthorized`).

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/schema` | GET | Tables, columns, keys — the structural source of truth. |
| `/api/data-dictionary` | GET | Field semantics, enum meanings, raw-vs-canonical rules, transaction/audit body shapes. |
| `/api/sql` | POST | Read-only analysis. Body is **exactly** `{"sql":"<one statement>"}`. |
| `/api/sql/transaction` | POST | Controlled writes for approved corrections only. |
| `/api/correction-audit` | GET | View of applied corrections / audit rows. |

`/api/sql` returns `{"columns":[...],"rows":[[...]],"row_count":N,"truncated":bool}`.
Notes learned from the service:
- The `/api/sql` body must contain **only** `sql`; adding any other key (e.g.
  `limit`) → `{"error":"invalid request"}`.
- `{"error":"query rejected"}` means the validator did not accept your query —
  almost always an unknown/misspelled table or column, or a non-SELECT verb on
  the read endpoint. **Consult `/api/schema` first**; do not treat it as a
  transport outage. If `truncated` is `true`, your result set was capped —
  aggregate/paginate so the full population is counted.

Use the bundled helper to avoid re-writing curl each time:

```bash
python3 skill/scripts/atlas_api.py schema          # GET /api/schema
python3 skill/scripts/atlas_api.py dict            # GET /api/data-dictionary
python3 skill/scripts/atlas_api.py sql "SELECT ..."  # or:  ... sql -   (stdin)
python3 skill/scripts/atlas_api.py audit key=value   # GET /api/correction-audit
python3 skill/scripts/atlas_api.py tx body.json      # POST /api/sql/transaction
```

It locates `environment_access.md` from the current directory upward (or
`$ATLAS_ENV_FILE`) and passes your SQL / transaction body through unchanged.

## Workflow

1. **Read the two payload files completely.** The request JSON is the spec —
   scope filters, every business definition, rounding, ordering/tie-breaks,
   threshold ladders, and the exact `required_output`. The answer template
   fixes types, key names, `additionalProperties:false`, id `pattern`s, array
   `minItems/maxItems`, and numeric precision (`multipleOf`/`decimal_places`).
   Build a checklist of every required output field.
2. **Discover the real schema.** `GET /api/schema` then `GET /api/data-dictionary`.
   **Never assume table or column names** — they differ per deployment and a
   guess yields `query rejected`. The data dictionary is where "production",
   "effective", "canonical", "active time", currency, and cutoff semantics are
   pinned down; map every business term in the request to concrete columns
   before writing SQL.
3. **Translate each definition into SQL** against `/api/sql`. Keep queries
   read-only. Verify the population count first, then layer each metric. See
   `reference/patterns.md` for the recurring idioms (eligibility/production
   filters, cutoff-as-of state, effective/canonical resolution, FX to USD,
   rates and rounding, worst-N ordering, medians, threshold ladders).
4. **(Correction tasks only)** Follow `reference/correction-procedure.md`:
   locate the single raw-vs-canonical contradiction read-only, apply the
   minimal canonical-field-only write via `/api/sql/transaction` with the audit
   record whose values come from the request payload, verify post-change, and
   set the status enum strictly by the request's success rule.
5. **Assemble and validate the output.** Emit only the template's required
   keys (no extras — `additionalProperties:false`). Round only the final
   reported values to the stated precision; use unrounded values for ordering
   and tie-breaks. Sort id arrays as specified and honor patterns/limits.
6. **Write `answer.json`** containing just the JSON object — no commentary,
   code fences, or trailing text. Validate it against the template before
   finishing.

## Non-negotiables

- The **request payload wins** over prose whenever they seem to differ, and the
  **answer template wins** over any assumption about output shape.
- **Read-only means read-only.** Only ever write when the task explicitly
  approves a correction, and then only the single approved canonical field —
  never raw/source values, source-identity fields, or unrelated rows.
- Boundaries are **inclusive UTC** unless stated otherwise; "as of cutoff"
  counts only events at or before the cutoff and treats still-open items by
  their elapsed/pending state at the cutoff.
- Evaluate status/risk ladders **top-down**: the first tier whose condition
  holds wins; the final tier is the catch-all.
- Do not copy any figure from an example answer; every number must come from
  the live data for the task at hand.

See `reference/patterns.md` and `reference/correction-procedure.md` for detail.
