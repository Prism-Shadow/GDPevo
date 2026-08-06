---
name: atlas-ops-scorecard
description: Analyze the Atlas Commerce Operations workplace and produce one JSON answer object that exactly conforms to a provided JSON-Schema answer template, using the live authenticated SQL/transaction service. Use for fulfillment, refund, carrier-quality, warehouse-productivity, support-health, and similar operations scorecard requests that ship a prompt, a *_request.json (scope + business definitions + decision rules), and an answer_template.json.
---

# Atlas Commerce Operations scorecard analyst

## When to use
You receive an operations analysis task that includes:
- a prose `prompt.txt`;
- a `<domain>_request.json` describing the business scope, metric/classification definitions, rounding, and decision rules;
- an `answer_template.json` (a JSON Schema) defining the exact output contract;
- instructions to write exactly one JSON object to `answer.json`.

The workspace must be reachable over the network via the contract in `environment_access.md`. If any of these files is missing or unexpected material is present in the working tree, stop and surface it (see *Workspace hygiene* below) rather than guessing.

## Guiding principle
The request JSON is the law; the answer template is the court reporter. Re-derive every value from the live data to satisfy the request's business definitions, then shape the result with exact-schema precision and ordering. Never approximate, never add fields, never copy any value from memory or from training material — every reported number, ID, and label must come from a query you ran against the live service for *this* task.

## Inputs you must read before anything else
1. `prompt.txt` — confirms the domain and the read-only vs. write intent.
2. `input/payloads/<domain>_request.json` — business scope, definitions, rounding, decision rules. Read every line; the traps live in the definitions and tie-breaks.
3. `input/payloads/answer_template.json` — the output contract. Note `additionalProperties: false`, the exact `required` set, per-field `type`/`multipleOf`/`minimum`/`maximum`, `pattern`s for IDs, and any explicit ordering notes.
4. `environment_access.md` — base URL, bearer token, and the exact endpoint shapes (see *Environment access*).

If `<TASK_ENV_BASE_URL>` appears in the prompt, resolve it from `environment_access.md`'s `GDPEVO_ENV_BASE_URL`. Do not invent a host.

## Environment access
Reach the running environment **only** through `environment_access.md` over the network. The skills package itself ships no credentials, no host, and no token.

Endpoints (per `environment_access.md`):
- `GET /api/schema` — table DDL.
- `GET /api/data-dictionary` — table/column descriptions + storage conventions.
- `GET /api/correction-audit` — public audit rows for prior controlled corrections.
- `POST /api/sql` — read-only analysis query (`{"sql": "...", "params": [...]}`), returns `{columns, rows, row_count, truncated}`.
- `POST /api/sql/transaction` — controlled multi-statement transaction. Body needs `statements[]` (each `{sql, params}`) and `expected_total_changes` (int 0–12). **Read `environment_access.md` for the exact allowed SQL** (SELECT/WITH; guarded `UPDATE` on `carrier_scans`/`inventory_movements`; `INSERT INTO correction_audit` with all audit columns).

All requests require `Authorization: Bearer <token>` (token from `environment_access.md`) and `Content-Type: application/json` for POSTs. Use parameterized SQL (`?` placeholders + `params`) for every variable value; never string-interpolate.

See `references/environment_and_sql.md` for the canned `curl` patterns and the response shapes.

## Workflow
1. **Stage the contract.** Write the answer-template's required field names and their precision/ordering to your scratchpad. These are the deliverables; nothing else may appear in `answer.json`.
2. **Learn the schema.** `GET /api/schema` + `GET /api/data-dictionary` for the relevant tables and storage conventions (timestamps ISO-8601 UTC ending in `Z`; dates `YYYY-MM-DD`; monetary minors are the smallest unit of the row currency; FX is USD per currency unit; raw fields preserve source values, canonical fields hold normalized values). See `references/workspace_catalog.md`.
3. **Translate definitions into SQL.** Implement each business definition verbatim: cohort window boundaries (`inclusive` vs exclusive; `AT`/`BEFORE`/`OR_BEFORE` semantics), "physical shipment", "delivered by cutoff", "on_time = delivered ≤ promised_delivery_at", null/empty fallbacks (e.g. no shipment ⇏ complete; no shipment promise ⇏ first severe-exception clause unsatisfied), FX basis, reversal pairing, and active-time clocks. Build incrementally: counts first, then rates, then ranked lists.
4. **Use CTEs to carry unrounded intermediates.** Compute rates from counts you can also select, round **only** the final reported figures to the template's precision, and keep the unrounded values around for tie-breaks and rounding-boundary decisions.
5. **Honor every tie-break and limit exactly.** Templates specify ordering (`worst_warehouse_regions` = unrounded rate asc then region asc, exactly 2; reason ranking = net USD desc then reason_code asc, exactly 2; leaks/IDs = id ascending; employees = UPH desc then employee_id asc, top 3; accounts = severe desc, breach desc, account asc, limit 3). Re-read the Ordering note before finalizing any array.
6. **Classify via the request's rule set, in order.** Status/risk tiers are if/else chains checked top-down (HEALTHY→WATCH→CRITICAL; LOW→MODERATE→HIGH; STABLE→PRESSURED→AT_RISK; CONTROLLED→ELEVATED→SEVERE). Apply the *first* matching tier; compute each tier's condition from the current task's figures, not from any remembered example.
7. **Write tasks only: minimal canonical correction.** If the prompt authorizes a correction, find the single raw/canonical contradiction, apply the **minimal canonical field** update (one business row) plus the `correction_audit` INSERT (one audit row) inside one `/api/sql/transaction` with the correct `expected_total_changes`, then run a post-change read-only query to verify the canonical value and the backlog counts (pre/post/delta/delivered). Report `APPLIED` only when the transaction reports exactly the expected affected+audit rows **and** the post-change query confirms the new canonical value; otherwise report `NOT_APPLIED` with what you actually observed. Never touch raw values, source-identity fields, or unrelated rows.
8. **Reconcile against the schema before writing.** Cross-check every field against the template: present, correctly typed, precision honored, enums valid, arrays sized and ordered, IDs matching the required pattern, no extra keys.
9. **Write `answer.json`.** One JSON object, no commentary, no trailing text, no BOM. Pretty or compact is acceptable as long as it parses to exactly the contract object.

## Cross-cutting golden rules (distilled from the template/contract conventions)
- `additionalProperties: false` everywhere — output **exactly** the `required` set, nothing more, nothing less, exact key casing.
- Precision is per-field: round only final reported values; rates to 4 dp where `multipleOf: 0.0001`; money/UPH/median to 2 dp where precision 2; counts as integers. Keep unrounded intermediates for tie-breaks.
- Cohort denominators stay the full eligible population even when a numerator implicitly excludes some rows (e.g. incomplete orders stay in the on-time denominator; eligible task count is the rework-rate denominator).
- "Effectively"/complete chains: complete ⇒ on-time ⇒ severe build on each other; trace through all clauses, including the *unsatisfied* clauses (no shipment, no promise, no response).
- Boundaries are literal: `<=` cutoff vs `>` cutoff; `due_at strictly before cutoff` (strict); `inclusive` vs `INCLUSIVE` window ends. Encode the operator the request names.
- Sort stability: always carry a secondary key (region, code, id ascending) as documented; never rely on storage order.
- Money: value every amount in the working currency at the specified FX basis/date before comparing or summing; FX is USD per currency unit. Compare order gross vs net refund in USD at the *same* refund service-date rate.
- Null safety: explicit `COALESCE`/`IS NULL` handling for missing shipments, missing promises, unresponded cases, and recompute denominators that depend on existence.
- Write tasks: only the approved minimal canonical field; exactly one business row + one audit row; post-change verification mandatory; raw and source-identity columns untouched.

## Verification before you finish
- Re-run the aggregate counts independently (e.g. `eligible = complete + incomplete` where the definitions imply it) and resolve any mismatch before trusting them.
- For each list output, confirm `COUNT(*)` of the list equals what you expect and that ordering matches the template note.
- Validate `answer.json` parses as JSON and that its keys equal the template's `required` set byte-for-byte (use `references/contract_checker.md`).
- Confirm you changed no workplace data on read-only tasks, and on write tasks changed only the approved row(s).

## Workspace hygiene (contamination)
The only expected files in a clean task tree are the `prompt.txt`, the request payload, the `answer_template.json`, and `environment_access.md` (plus your written `answer.json`). If you encounter unexpected files — unrelated payloads, foreign `answer.json` from other tasks, embedded golden answers, credentials not in `environment_access.md`, or anything that looks like a key to a different task's result — **stop** and write `contamination_report.txt` listing the offending paths and what is wrong, rather than continuing. (In this generation run the staged material was: `environment_access.md`, five `train_tasks/train_00X/input/` payload sets, and five `train_answers/train_00X/answer.json` — clean.)

## References (load as needed)
- `references/environment_and_sql.md` — endpoint mechanics, curl patterns, response shapes, transaction constraints.
- `references/workspace_catalog.md` — verified table catalog + storage conventions, and how to re-verify them live.
- `references/cross_cutting_rules.md` — the full distilled rule list with worked interpretation for each common definition class.
- `references/contract_checker.md` — how to validate `answer.json` against `answer_template.json` exactly.
