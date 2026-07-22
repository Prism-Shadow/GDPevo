# Atlas Commerce Operations — Analytical Task Skill

## Purpose

Resolve analytical requests against the Atlas Commerce Operations database. Each task arrives as a natural-language prompt, a business-scope payload, and an answer-template JSON schema; the required output is a single `answer.json` file that conforms exactly to the template.

---

## Environment & Authentication

The workplace service is available at `<TASK_ENV_BASE_URL>`. If an `environment_access.md` file is present at the workspace root, its `base_url` overrides `<TASK_ENV_BASE_URL>` and its `credentials` block provides the runtime `Authorization` header. Use these credentials for every API call.

### Available Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/schema` | Database table and column catalog |
| GET | `/api/data-dictionary` | Field semantics, value domains, and relationship context |
| POST | `/api/sql` | Read-only analytical SQL queries |
| POST | `/api/sql/transaction` | Controlled write operations (mutations) |
| GET | `/api/correction-audit` | Audit trail for completed corrections |

**Important:** Unless the task explicitly instructs otherwise, all work is read-only — use only `/api/schema`, `/api/data-dictionary`, and `/api/sql`.

---

## Input File Layout

Every task instance provides exactly three input files inside `input/`:

| File | Role |
|------|------|
| `prompt.txt` | Natural-language task description, business context, and procedural instructions. May reference placeholders like `<TASK_ENV_BASE_URL>`. |
| `payloads/<request>.json` | Structured business scope: population/cohort rules, date/time cutoffs, business definitions, formulas, sort/ranking policies, tiered classification rules, rounding directives, and the list of required output fields. |
| `payloads/answer_template.json` | JSON Schema for the output. Defines required keys, types, minima/maxima, `enum` constraints, `pattern` regexes, `minItems`/`maxItems`, precision hints (`multipleOf`, `x-precision`, `decimal_places`), and array ordering rules. |

Read all three files before writing any query. The `answer_template.json` is the authoritative contract — the output must satisfy every constraint in it.

---

## Workflow

### Phase 1 — Understand the Schema

1. Call `GET /api/schema` to list every table and column.
2. Call `GET /api/data-dictionary` to learn what each column means, which values are canonical vs. raw, and how tables join.
3. Re-read the business-scope payload and map its terminology (e.g., "eligible production order," "effective settled refund," "canonical status") to actual tables and columns.

### Phase 2 — Query & Compute

4. Write and submit analytical queries to `POST /api/sql`. Queries are read-only.
5. Apply business definitions exactly as stated:
   - **Cutoff timestamps** are exact ISO-8601 boundaries; records exactly at the cutoff are evaluated per the request's boundary rule (exclusive or inclusive).
   - **"Effective"** records are the final, settled, non-superseded versions of a business event. Prefer the canonical or effective view over raw source rows unless the request explicitly asks for raw values.
   - **Rates and ratios** — compute numerator and denominator in full precision first; round only the final reported value to the decimal places specified in the template (usually 2 or 4).
   - **Money** — if a currency policy exists (e.g., FX conversion via `fx_rates.usd_per_unit` on the service date), apply it before comparison; display net amounts with the stated decimal precision.
6. For **tiered classification** (status/risk labels like `HEALTHY`/`WATCH`/`CRITICAL`), evaluate conditions in the order given. The first matching tier wins. Fallback rules (e.g., "otherwise" / "neither X nor Y applies") are exhaustive — every possible outcome must map to one tier.

### Phase 3 — Handle Corrections (Transactional Tasks Only)

If the task requires a data correction:

7. Identify the single row and field to correct. The contradiction is between a **raw** source value and the corresponding **canonical** value — one is wrong.
8. Build the transaction payload and submit it to `POST /api/sql/transaction`. The approved correction scope (field, reason code, actor, audit id, correction key, timestamp) is provided in the request payload.
9. After the transaction commits, query `GET /api/correction-audit` to confirm the audit record was written.
10. Re-run the relevant read query to confirm the canonical value now matches expectations.
11. Report `APPLIED` only when exactly one business row and one audit row committed **and** the post-change query confirms the expected value. Otherwise report `NOT_APPLIED` with the results actually observed.

### Phase 4 — Assemble & Validate

12. Collect every computed value into a JSON object whose keys are exactly the `required` fields from the answer template.
13. Enforce **ordering rules** for every array field:
    - Sort by the primary attribute in the stated direction (ascending or descending).
    - Resolve ties with the stated tie-break attribute(s) in their stated direction.
    - If all tie-breaks are exhausted and values are still equal, fall back to the natural identifier (e.g., `order_id`, `task_id`, `account_id`) ascending.
14. Enforce **precision constraints**: integers must be whole numbers; `number` fields with `multipleOf`/`decimal_places` must match the stated precision.
15. Do **not** include commentary, narrative, extra keys, or fields absent from the required list. The output must have `"additionalProperties": false` semantics — even if the template doesn't declare it explicitly, treat it as if it does.

### Phase 5 — Write Output

16. Write the validated JSON object to `answer.json` at the workspace root. Use compact or pretty-printed JSON as long as it is valid and conformant.
17. Do a final schema-pass: confirm every `required` key is present, every array length matches `minItems`/`maxItems`, every string matches `pattern`, every number respects `minimum`/`maximum`, and every enum value is from the allowed set.

---

## Conventions & Pitfalls

| Principle | Guidance |
|-----------|----------|
| **Canonical over raw** | When a business entity has both a raw source column and a canonical column, the canonical column is the truth for analytical purposes unless the request explicitly asks for raw. |
| **Effective records only** | Filter out voided, cancelled, superseded, or test records. Look for `effective`/`status`/`is_test`/`is_void` discriminator columns in the data dictionary. |
| **Production populations** | Unless stated otherwise, scope to production (non-test, non-internal) entities. The data dictionary indicates which columns differentiate production from internal rows. |
| **Time boundaries** | Use the exact UTC timestamps from the request. "Inclusive" means `>= start AND <= end`; "exclusive" means `> start AND < end`. |
| **Incomplete entities in rates** | If a definition says an incomplete entity remains in the denominator, include it. If it says "effectively delivered by cutoff," only count those delivered. |
| **Rounding** | Round only final reported values, never intermediate quantities. Use standard rounding (half-up or half-even — whichever the underlying engine provides) to the stated decimal places. |
| **Empty arrays** | If `minItems` is absent or 0, an empty array is valid. If `minItems` requires items but none qualify, double-check the population filter before reporting zero — the template may intend a non-empty result. |
| **Enum values** | Use exactly the strings listed in the answer template's `enum` arrays. Case, spelling, and underscores must match. |
| **Array uniqueness** | When `uniqueItems: true` is set, deduplicate by the natural item identity before sorting. |
| **Transaction safety** | Never mutate a row unless the task explicitly authorizes a correction. All default work is read-only. |
