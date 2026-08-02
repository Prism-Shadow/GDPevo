---
name: atlas-ops-reporting
description: >-
  Produce exact JSON answers for Atlas Commerce Operations reporting and
  data-correction requests. Use when a task provides an environment_access.md
  for an Atlas / "workplace" service (GET /api/schema, /api/data-dictionary,
  /api/correction-audit, POST /api/sql, POST /api/sql/transaction) plus a
  request payload JSON and an answer_template.json, and asks you to compute a
  scorecard, reconciliation, quality/health/productivity review, backlog, or an
  approved canonical correction and write it to answer.json. Covers cohort/
  eligibility scoping, cutoff-based state, rate/median/FX metrics, top-N/worst-N
  ranking, exact ID lists, tiered status classification, and audited mutations.
---

# Atlas Commerce Operations reporting & correction

You are given an analytical (or correction) request against the **Atlas Commerce
Operations** service and must emit **one JSON object** that conforms *exactly* to
a provided `answer_template.json`. These tasks share one structure; follow the
procedure below rather than improvising per task.

## 1. Read the three authoritative inputs (in this order)

1. **`environment_access.md`** — the base URL, `Authorization: Bearer <token>`,
   and the list of available endpoints. Always read it fresh; never hardcode the
   URL or token — they are supplied per task.
2. **The request payload** `input/payloads/<something>_request.json` — this is
   the **authoritative business spec**: cohort/scope, business definitions,
   rollups, rounding, money/FX policy, ranking order, and the status/risk
   thresholds. When the prose prompt and the payload seem to differ, the payload
   governs; the `prompt.txt` is only framing.
3. **`input/payloads/answer_template.json`** — the **exact output contract**
   (a JSON Schema). It fixes the key names, types, enum spellings, ID regex
   patterns, array `minItems`/`maxItems`, ordering notes, and rounding
   (`multipleOf` / `decimal_places` / `precision`). `additionalProperties:false`
   means emit exactly the `required` keys and nothing else.

Map every business concept named in the request to a concrete answer field
before writing any SQL.

## 2. Discover the data model — do not guess columns

- `GET /api/schema` and `GET /api/data-dictionary` to learn the real table and
  column names and, critically, **field semantics** (which column is the
  canonical/effective value, which flags production vs test, how status /
  currency / timestamps are represented).
- The SQL gate **rejects introspection** (`sqlite_master`, `information_schema`,
  `version()` and similar are refused as "query rejected"). Get structure only
  from the schema/data-dictionary endpoints, then query the real business tables.
- If a GET returns a transient `{"error":"service error"}`, retry a few times.

## 3. Query via POST /api/sql (read-only)

- Body `{"sql": "<one SELECT>"}`; response is
  `{"columns":[...],"rows":[[...]],"row_count":N,"truncated":bool}`.
- Dialect is **SQLite** (3.46). Use single-quoted string literals.
- **Always check `truncated`.** If true, aggregate/paginate so no rows are
  silently dropped — every count, list, and rate must be over the full cohort.
- A `{"error":"query rejected"}` means the query violated the read-only /
  allowlist gate (introspection, non-allowed function, or a write on /api/sql).
  Rewrite as a plain `SELECT` over business tables.
- Prefer computing metrics in SQL, then **verify each headline number with an
  independent query** (e.g. eligible == complete + incomplete).

## 4. Apply the cohort and cutoff exactly

Every task narrows to a precise population before any metric. Apply all stated
filters, in combination:

- **Production population** only (exclude test/non-production) when stated.
- **Time window** (created/opened/service window): treat timestamps as **exact
  UTC boundaries** and honor the stated inclusivity (`inclusive` → `>=`/`<=`).
- **As-of cutoff**: evaluate every state (open/delivered/resolved/complete) **as
  of the cutoff**, not "now". A thing done after the cutoff counts as not-yet-done.
- **Membership predicates** (segment, region, tier, campaign, "has an effective
  scan in the named batch at/before cutoff", etc.) exactly as written.
- Use the **effective/canonical** value where raw and canonical layers exist; the
  data dictionary says which column that is.

## 5. Compute metrics per the written definitions

See `references/metric-and-output-rules.md` for the full checklist. Core rules:

- **Rates**: numerator/denominator exactly as defined; keep failing/incomplete
  items in the denominator when the spec says so. Compute **unrounded** for
  comparisons and ordering; round **only the final reported value** to the stated
  decimals.
- **Aggregate ratios** (e.g. units-per-hour): sum numerator and denominator
  across the group *then* divide — never average per-row ratios.
- **Median**: sort the values; for an even count average the two central values.
- **Money / FX**: convert each row with the **daily rate for that row's own
  service_date and currency**, compare/aggregate in the reporting currency (USD),
  and round the displayed total to the stated decimals.
- **Exact ID lists**: return the business IDs matching the predicate, unique,
  matching the template's regex, sorted as specified (usually id ascending).

## 6. Ranking (top-N / worst-N)

Order on the **unrounded** metric, applying the full multi-key sort in the stated
order and ending with the id tie-break (almost always id ascending). Return
exactly the required count (`minItems == maxItems`). Round each reported metric
only after selection.

## 7. Tiered status / risk classification

Evaluate the tiers in their listed order and assign the **first** tier whose
condition holds — the tiers run best→worst (e.g. HEALTHY→WATCH→CRITICAL,
STABLE→PRESSURED→AT_RISK, LOW→MODERATE→HIGH, CONTROLLED→ELEVATED→SEVERE), and the
final tier is the catch-all "otherwise". Test conditions against **unrounded**
rates, and respect strict vs inclusive wording ("at least"/`>=` vs "below"/`<`).

## 8. Correction tasks (only when the request explicitly approves one)

Some requests approve a single minimal canonical correction (identified as one
raw-vs-canonical contradiction) and ask for pre- and post-correction metrics.

- Identify the one affected row/field; **change the canonical field only** via
  `POST /api/sql/transaction`. Never modify raw source values, source-identity
  fields, or unrelated rows.
- Write the audit record using the request-supplied `reason_code`, `actor`,
  `audit_id`, `correction_key`, and `corrected_at`; read it back via
  `GET /api/correction-audit`.
- **Success rule**: exactly one business row **and** one audit row committed, and
  a post-change `SELECT` confirms the new canonical value → `correction_status:
  "APPLIED"`. Any other outcome → `"NOT_APPLIED"` reporting the values actually
  observed.
- Compute the backlog/metrics both before and after per the template.
- If the request does not approve a correction, stay strictly read-only.

## 9. Write answer.json

- Exactly one JSON object, the `required` keys only, nesting/types per the
  template. Integers as integers; rates/amounts as numbers at the exact decimals;
  enum strings spelled exactly; arrays at the required size and order.
- **No commentary, markdown, or extra fields** in the file.
- Before finishing, re-validate the object against `answer_template.json` and
  re-derive each headline number with a second query. See the checklist in
  `references/metric-and-output-rules.md`.
