---
name: atlas-commerce-ops-scorecard
description: Solve Atlas Commerce Operations cutoff-based analytics scorecard tasks — fulfillment, refund, carrier-quality, warehouse-productivity, and support-health reviews produced from a live read-mostly SQL workplace service. Use at the start of any task whose input is a prompt.txt + a JSON request (scope + business definitions) + an answer_template.json output contract, backed by an authenticated SQL/schema/data-dictionary service.
---

# Atlas Commerce Operations Scorecard

This skill solves the family of Atlas Commerce Operations "scorecard / reconciliation / health review" tasks. Each task gives you: a `prompt.txt`, a JSON **request** file (scope, business definitions, status/risk policies), and an `answer_template.json` (the exact output contract). The workplace data lives behind an authenticated read-mostly SQL service (schema, data-dictionary, read SQL, and a controlled SQL transaction for approved corrections). Your job is to compute the requested metrics from the live data and emit one JSON object that conforms exactly to the template.

Run the steps in order. Do not skip the verification step.

## 0. What kind of task is this?

Trigger this skill when the task matches this shape:
- Inputs are `input/prompt.txt`, a JSON request under `input/payloads/*request*.json`, and `input/payloads/answer_template.json`.
- The prompt references a workplace/service base URL and endpoints like `GET /api/schema`, `GET /api/data-dictionary`, read-only `POST /api/sql`, and (for correction tasks) `POST /api/sql/transaction` plus `GET /api/correction-audit`.
- The output is a single JSON object written to `answer.json`, conforming exactly to the template, with no commentary.

If those match, this is an Atlas scorecard task. Read on.

## 1. Read every input verbatim before querying

Read `prompt.txt`, the request JSON, and `answer_template.json` completely. Capture, literally:
- **Scope filters**: account tier/segment/region, "production" population, campaign id, warehouse id, batch id, and every date/timestamp boundary (note whether inclusive). Treat all timestamps as exact UTC (they end in `Z`).
- **Cutoff timestamp(s)**: the cutoff used for "by the cutoff" / "as-of" / "at cutoff" predicates, distinct from any case/event **opened/created window**.
- **Business definitions**: each metric's exact wording (complete vs on-time, severe exception, leakage candidate, units_per_hour, SLA breach, etc.). The wording is the spec — do not paraphrase it.
- **Rounding**: which values round and to how many decimals ("round only final reported rates"; display decimals). Rank keys and tie-breaks for every array ("… ascending, then … ascending"; "EXCEEDS" = strictly greater, not `>=`).
- **Status / risk policies**: ordered rules (HEALTHY/WATCH/CRITICAL, STABLE/PRESSURED/AT_RISK, LOW/MODERATE/HIGH, CONTROLLED/ELEVATED/SEVERE, etc.) — evaluate top-down, first match wins.
- **Output contract**: required fields, `additionalProperties:false` (no extra fields), enums, array min/max sizes, ID patterns (e.g. `^ORD-[0-9]{6}$`). The submitted object must match this exactly.

## 2. Learn the schema, then map "production" / scope terms to columns

Call `GET /api/schema` and `GET /api/data-dictionary` and read them. Key gotchas encoded in the data:
- `accounts` has `is_internal` and `is_test` integer flags. **"Production" accounts / orders / shipments / cases = `is_test=0 AND is_internal=0`.** Test accounts are named "Sandbox…"; internal accounts are named "Internal Account…". Exclude both from any cohort whose scope says PRODUCTION_* or "production accounts". Other tiers/segments/regions filter literally on their columns.
- Many tables carry a denormalized `current_status`/`promised_at`-style snapshot. The data dictionary states these "may lag append-only event history." **Prefer append-only event/scan tables** (order_events, carrier_scans, case_events, warehouse_task_events, refund_attempts) over the snapshot column whenever a metric depends on state "at the cutoff."
- Raw vs canonical: tables like `carrier_scans` and `inventory_movements` keep `raw_*` source values AND `canonical_*` normalized values. Operational analytics use the canonical fields.

## 3. Query safely — the SQL service has hard limits

The read SQL endpoint silently caps results and rejects some shapes. Follow these rules or your counts will be quietly wrong:
- **Every result is hard-capped at 5000 rows regardless of any `LIMIT`.** The response carries `row_count` and `truncated`. If `truncated` is true, the rows are incomplete — your aggregate is wrong. Always check `truncated` before using a result.
- To stay under the cap, **aggregate in SQL** (`GROUP BY`, `MIN`/`MAX`/`COUNT`, `SUM`) and **restrict to the in-scope cohort** with `WHERE <key> IN (SELECT … FROM … WHERE <scope>)`. A single level of `IN (subquery)` is allowed and is the main tool for keeping result sets small.
- **Nested subqueries-in-FROM that themselves contain a subquery (or a self-join subquery) are rejected** with HTTP 400 `{"error":"query rejected"}`. Keep to at most one FROM-subquery level. `SELECT alias.*` and deeply nested aggregates also get rejected. Plain `COUNT(DISTINCT …)` and `GROUP BY … HAVING` are fine.
- Pass literals via `params` (positional `?`) for safety. Timestamps are ISO-8601 UTC strings (`…Z`); dates are `YYYY-MM-DD`.
- If a query you need is too large to return, fetch the **in-scope cohort's keys first** (small result), then query each child table restricted to those keys, and join/reduce in your own code.

## 4. Reconcile "effective" state and dedup retries before counting

Several metrics hinge on "effective" state at the cutoff. Apply these consistently:
- **Retry dedup**: append-only tables can re-ingest the same upstream event. Dedup by keeping the row with the **latest `ingested_at` per `(source_system, external_event_id)`** before any "effective" aggregation. (You will see duplicate rows that are otherwise content-identical.)
- **Effective final carrier status** of a shipment = the `canonical_status` of its latest scan at/before the cutoff — rank scans by `canonical_event_at` then `ingested_at` then `scan_row_id`, after dedup. A shipment is "delivered by the cutoff" only when this **final** scan is `DELIVERED`, *not* merely when some DELIVERED scan exists. (Earliest-delivered vs final-status diverges on real data; final-status is the operational model the dictionary intends.)
- **Carrier backlog** ("effective final carrier status is not DELIVERED") is the count of in-scope shipments whose effective final status ≠ DELIVERED. Compute it over the *production* cohort.
- **Support case state at cutoff**: replay case events ≤ cutoff; the case is active (open) at cutoff unless its last terminal event is `RESOLVED`; `REOPENED` after a `RESOLVED` makes it active again. `open_at_cutoff` = Open ∪ Reopened active states; `reopened_at_cutoff` = the Reopened subset. Do **not** trust `support_cases.current_status` (it lags).
- **Warehouse task completion/rework**: a task is completed/reworked when it has an effective (deduped) `COMPLETED`/`REWORK` event at/before the state cutoff — again prefer events over `warehouse_tasks.current_status`.

## 5. Compute clocks and money exactly per the policy

- **Support active time (SUPPORT_ACTIVE_TIME)**: the clock runs while the case is agent-active and **pauses during `WAITING_CUSTOMER`** (resume on `CUSTOMER_REPLIED`/next agent event). Start the clock at the case's **`opened_at` header field, not the `OPENED` event timestamp** (they differ by minutes; the data is seeded so `opened_at` lands cases just over the SLA thresholds). For `first_response`, use active time from open to the first `AGENT_RESPONDED`; an unresponded case uses active elapsed time to the cutoff. For resolution, a resolved case uses active time open→`RESOLVED`; an active case uses active elapsed to the cutoff. SLA thresholds come from the request per priority; a breach **exceeds** the threshold (strictly `>`).
- **Median active resolution hours**: across cases resolved at the cutoff; for an even count average the two central values; round to the stated decimals.
- **Money / FX**: convert each row's minor units to USD by the **daily** `fx_rates.usd_per_unit` for that row's currency AND that row's service_date. The USD rate itself varies by date — do **not** hardcode 1.0. Sum full-precision and round only the final reported value to the stated decimals.
- **Refund model**: `refund_attempts.status` is consistent per `refund_id` (one effective status per logical refund). `SETTLED` = effective refund; `REVERSED` rows (carrying `linked_refund_id`) = linked reversals. Count in-scope linked reversals **even when they target a non-settled refund**, and **subtract their USD value from net refund amount** (net = Σ settled USD − Σ in-scope reversed USD). Leakage compares each order's effective settled refund USD against its gross order USD (gross valued in the order's own currency at the refund's service_date rate), OR ≥2 unreversed effective settled refunds sharing a normalized reason code.

## 6. Correction tasks (carrier quality / minimal canonical correction)

When the request asks to apply an approved minimal canonical correction:
1. Find the **single** raw/canonical contradiction in the named import batch: `WHERE import_batch_id = ? AND raw_status <> canonical_status` (also bound by the cutoff). The affected scan row and its shipment are the correction target; the canonical field should be set to match the raw value.
2. Apply the correction in **one** `POST /api/sql/transaction` with two statements: a guarded `UPDATE carrier_scans SET canonical_<field> = ?, corrected_at = ?, correction_reason = ? WHERE scan_row_id = ? AND canonical_<field> = ?` (scope the WHERE to that one row and its old value so it changes exactly one business row) and an `INSERT INTO correction_audit` with **all** audit columns (audit_id, correction_key, entity_type, entity_id, source_row_id, field_name, old_value, new_value, reason_code, corrected_at, actor) from the request's `approved_correction` block. Set `expected_total_changes` to 2.
3. The result is `APPLIED` only when `total_changes == 2` (one business row + one audit row) AND a follow-up read query confirms the new canonical value on that scan row. Otherwise report `NOT_APPLIED` with the actually observed results.
4. Report backlog over the **production** cohort (production shipments with an effective scan in the named batch at/before the cutoff): pre-correction count, post-correction count (recompute after the UPDATE), their delta, and the post-correction delivered count. Use effective final carrier status (step 4).
5. Leave raw source values, source identity fields, and unrelated rows unchanged — only the one canonical field is corrected.

## 7. Assemble, rank, round, and validate against the template

- Build the single output object with exactly the template's required keys, no extras.
- For every array, apply the stated ordering and tie-breaks (e.g. worst regions/accounts "by rate ascending, then id ascending"; top reason codes "by net USD descending, then code ascending"). Sort ID arrays ascending unless told otherwise.
- Round only the final reported numeric values to the stated decimals (`multipleOf`/`decimal_places` in the template). Sort/rank on **unrounded** values, then round for output.
- Evaluate status/risk from the **unrounded** rates against the ordered policy rules, first match wins.
- Validate the object against `answer_template.json` before finishing: correct types, enums, `additionalProperties:false` (no stray keys), array size bounds, and ID regex patterns. Write the final JSON to `answer.json` with no commentary outside the JSON.

## Supporting references

- `references/data-model.md` — the concrete domain models (production filter, effective final carrier status, refund/reversal chain, support active-time, warehouse task events) distilled for quick lookup.
- `references/query-patterns.md` — safe and rejected SQL shapes against this service, and the truncation guard.
- `references/pitfalls.md` — the recurring traps that quietly corrupt counts, with the resolution for each.
