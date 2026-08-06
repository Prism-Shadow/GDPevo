---
name: atlas-commerce-ops-review
description: Solve Atlas Commerce Operations cutoff-based analytical review tasks (fulfillment, refund, carrier, warehouse, support). Read request + template contracts literally, replay event history at a cutoff, dedup imported rows, and produce a JSON object that conforms exactly to the answer template.
---

# Atlas Commerce Operations Review

These tasks ask for a **cutoff-based operational review**: take a cohort of production business records, freeze their state at an as-of cutoff, apply stated business definitions/SLAs/status policies, and emit one JSON object conforming **exactly** to an answer template. The plumbing (query service, schema, data dictionary, auth) is provided in the environment; this skill is the analytical methodology.

## 0. Read the contract before writing a line of SQL

Every task ships two JSON files in `input/payloads/`:
- a **request** (`*_request.json`): scope, windows, cutoff, business definitions, thresholds, status rules, ordering/tie-breaks.
- an **answer template** (`answer_template.json`): the exact output schema.

Treat both as load-bearing contracts:
- The **template** is the output law. `required`, `additionalProperties:false`, `minItems/maxItems`, `pattern`, `multipleOf`, and each field's `description` / `x-precision` define what to compute and how to format it. Emit **only** the schema's fields, in its shape, no commentary, no extra keys. Mismatched precision or an extra key fails the whole object.
- The **request definitions** are literal. Every clause carries weight: `inclusive`/`exclusive`, `at or before` vs `strictly before`, `more than 24 hours`, `below` (strict `<`) vs `at least` (>=), which count is the **denominator**. Decide each threshold operator from the wording; `>` vs `>=` flips borderline counts and everything downstream (rates, status, IDs).

If a definition and the template field description disagree, reconcile both before computing; the template field description usually restates the precise formula.

## 1. Two timestamps you must never conflate: window vs cutoff

- **Eligibility window** (e.g. `created_at`/`opened_at` in `[start, end]`): selects the cohort. Boundary inclusivity comes from the request.
- **As-of cutoff**: where you **freeze state** to measure elapsed time and terminal status. Events after the cutoff do not exist for this review.

A record is eligible by its window; its *state and metrics* are measured at the cutoff. Do not pull state from after the cutoff.

## 2. Production/test/internal scoping

- Always exclude test rows (`is_test = 0`).
- "Production accounts" scope: also exclude internal accounts (`is_internal = 0`) unless the request explicitly includes them. This is the most common population error — decide it deliberately from the request's `population` field.
- Segment/tier/region/warehouse filters come from the request's `account_scope`/cohort. Note whether region is the **account's** region or the **warehouse's** region — regional rollups use the assigned facility's region, not the customer's.

## 3. Imported rows are append-only and duplicated — dedup first

Raw event/scan/attempt tables receive import retries. The same logical event arrives multiple times under the same `source_system` + `external_event_id` with different `ingested_at`. Before any analysis, **dedup by `(source_system, external_event_id)` keeping the earliest `ingested_at`**. This applies to lifecycle event tables (support case events, warehouse task events) and to carrier scans.

Logical-business-row dedup is different: e.g. a `refund_id` is one logical refund that may have multiple settled rows — keep one row per logical id (min row id) to avoid double counting. Know which identity is the *logical* id vs the *physical* row id for each table; the data dictionary states this.

## 4. Derive state from event replay, never the status snapshot

Header tables carry a `current_status` convenience column the dictionary warns **"may lag append-only event history."** Never trust it. Replay the **deduped, cutoff-filtered** events in `(event_at, row_id)` order to derive the true state at the cutoff. Examples:
- support case open/resolved/reopened — terminal state is whatever the last relevant event leaves it as.
- warehouse task completed/rework — completeness comes from `COMPLETED`/`REWORK` events ≤ cutoff, not `current_status`.
- carrier shipment status — the latest canonical scan ≤ cutoff by `(canonical_event_at, scan_row_id)`.

## 5. Recurring / terminal events: first vs last

A status event can recur (e.g. `RESOLVED` followed by another `RESOLVED`). When measuring "time to resolution" you almost always want the **final** occurrence of the terminal event, not the first — the work was actually completed at the last one. Decide per definition; for *state-at-cutoff* questions, replay gives the final state automatically. Getting first-vs-last wrong shifts medians and breach tallies silently.

## 6. Breach populations and elapsed-time clocks

A "breach" metric is measured on the **whole eligible population**, not only cases that reached a terminal state:
- A **resolved/closed** case uses elapsed time from its start to its terminal event.
- A **still-open** case uses elapsed time from its start **to the cutoff** (the definition says "an active case uses active elapsed time at the cutoff").

Measure each case to its own endpoint. Do not restrict the breach count to resolved cases only.

### Support active-time clock
"Support active time" excludes periods the case sat waiting on the customer. Implement a clock that:
- starts at the case `opened_at`;
- **pauses** on `WAITING_CUSTOMER`;
- **resumes** on `CUSTOMER_REPLIED`, `REOPENED`, or `OPENED`;
- ignores other events for the waiting state.

Walk deduped events ≤ endpoint in `(event_at, case_event_id)` order accumulating only non-waiting seconds. First-response time = active time to the first `AGENT_RESPONDED`; if none, active time to the cutoff. Resolution time = active time to the (final) `RESOLVED`, or active time to the cutoff if still open. Thresholds are per priority and compared strictly (`exceeds` = `>`).

### Other elapsed clocks
Warehouse/productivity tasks use **productive minutes** attached to completion events (units / productive_minutes × 60), not wall-clock time. Use the unit each metric specifies.

## 7. Money, FX, and reversals

- Monetary amounts are **minor units** (smallest unit of the row's currency). Convert the minor amount by `(amount_minor / 100) * usd_per_unit`.
- `fx_rates.usd_per_unit` is **USD per one unit** of the named currency, keyed by `(rate_date, currency)`. Use the rate for the **transaction's service date and the row's currency** — not the order's date — unless the request names a different basis.
- **Effective** = settled minus reversals. A reversal links to its parent via `linked_refund_id`; count a reversal only if its parent is an in-scope effective settled logical refund. Net = Σ settled USD − Σ effective reversal USD.
- Comparison FX basis: when comparing a refund value to an order's gross, value the order gross **in its own currency at the refund's service-date rate** (per the request's `order_gross_comparison` clause).

## 8. Corrections (carrier/inventory) — minimal canonical, never raw

When a task approves a canonical correction:
- Correct **one canonical field on one business row** with a guarded `UPDATE`. Never touch raw source values, source-identity fields (`source_system`, `external_event_id`, row ids), or unrelated rows.
- Append **one** `correction_audit` row carrying every audit column (audit_id, correction_key, entity_type, entity_id, source_row_id, field_name, old_value, new_value, reason_code, corrected_at, actor) using the approved values from the request.
- Run the update + audit insert in one transaction with the stated `expected_total_changes`.
- Report `APPLIED` **only if** exactly one business row and one audit row commit **and** a post-change read query confirms the new canonical value. Any other outcome → `NOT_APPLIED` with the results actually observed. Do not claim success without the verifying read.
- Backlog/quality counts are taken **after** the correction (post state), and only over the in-scope cohort (e.g. shipments with an effective scan in the named batch at/before the cutoff).

## 9. Rankings, rollups, and ordering

- Honor the request's **order list exactly**, including tie-breaks. "Rate descending then id ascending," "first two by rate ascending then region ascending," "top three by units/hour then employee_id ascending" — each key and its direction is significant; ties resolved by the next key.
- Regional/segment rollups: pick the entity the request names (assigned warehouse region for fulfillment; account tier/segment for refunds).
- Re-derive each ranking from the same deduped, cutoff-frozen population as the counts — a different scoping for the rollup vs the totals is a common silent error.

## 10. Status classification

Apply the status rules **in the order written** (e.g. HEALTHY → WATCH → CRITICAL; STABLE → PRESSURED → AT_RISK; LOW → MODERATE → HIGH; CONTROLLED → ELEVATED → SEVERE). The last rule is the catch-all ("otherwise" / "all other outcomes"). Rates use the **specified denominator** (often eligible count — incomplete/active cases stay in the denominator). Evaluate conditions at full precision.

## 11. Rounding and precision

- Round **only final reported values** to the precision the template/request states (e.g. rates to 4 decimals, money to 2, medians to 2). Keep full float precision through every intermediate step; rounding mid-pipeline drifts rates and status boundaries.
- Median: over the resolved-at-cutoff population; for an even count, average the two central values, then round. `x-precision: 0` means integer.

## 12. Self-verification before submitting

- **Schema-check**: validate the emitted JSON against the template keys, types, precision (`multipleOf`), array lengths/uniqueness, and that no extra fields exist. A single schema slip fails the object.
- **Population consistency**: does the sum of mutually-exclusive states (open + resolved, complete + incomplete) equal the eligible count? Do rate numerators/denominators use the populations the request named?
- **Variant cross-check**: when a definition is genuinely ambiguous (first vs last terminal event; breach over resolved-only vs all cases; include internal or not), compute every defensible variant and pick the one matching the literal wording. If feedback indicates an error, the wrong field is almost always **downstream of one interpretation choice** — isolate which metric moved rather than re-rolling the whole answer.
- **Sanity bounds**: breach rates, completion rates, medians should sit in plausible ranges; a median at exactly a threshold or a 0%/100% rate usually means an off-by-one or a population bug.

## Quick task-type map

- **Fulfillment scorecard**: order cohort by campaign + creation window; complete = ≥1 physical shipment AND all physical shipments effectively DELIVERED by cutoff; on-time = every shipment delivered ≤ its promised_delivery_at; severe-exception by the 24h-over-promise rule; worst regions by unrounded regional rate asc then region asc.
- **Refund reconciliation**: dedup logical refunds, settle−reversals net in USD via service-date FX, top reasons by net USD desc then reason asc, leakage candidates (refund > gross in USD, OR ≥2 same-recode settled refunds), cohort risk by candidate rate + net USD thresholds.
- **Carrier quality**: one raw/canonical contradiction → minimal canonical correction + audit + post-verify; backlog = cohort whose final carrier status ≠ DELIVERED.
- **Warehouse productivity**: completion/rework from events ≤ cutoff; units/hour per employee from completed-event units & productive minutes; top employees and lowest team by stated orders; delayed high-priority = HIGH/URGENT, due before cutoff, not completed by cutoff.
- **Support health**: eligible case population; active-case state at cutoff; first-response and resolution active-time breaches over all cases (open cases measured to cutoff); severe-active = open/reopened at cutoff AND URGENT/HIGH AND beyond resolution threshold; worst 3 accounts by severe desc, breach desc, account asc; resolved-at-cutoff active-time median; risk by severe + first-response rates.
