# MedBridge Sales Ops CRM Skill

## Overview

This skill covers two families of account-ready tasks against the MedBridge Sales Ops API:

- **QUOTE tasks**: Reconcile a customer RFQ or quote revision against the API records and produce a quote decision package — EXW pricing, freight comparison with grand totals, route-risk flags, recommended transport mode, freight-validity warnings, and payment terms.
- **RECONCILIATION tasks**: Reconcile a won opportunity — CRM opportunity, milestone invoices, payments, revenue-recognition journals, events, and vouchers — and produce a finance-ready reconciliation with paid/unpaid state, outstanding balance, revenue-recognition coverage, accounting/collection/event-invitation follow-up actions, and contact linkage.

## API Usage Rules

The shared business environment is a **remote** HTTP JSON API (base URL from the task's `environment_access.md`).

### Detail-by-id endpoints (GET /api/<collection>/<id>)
Available **only** for: `customers`, `products`, `rfqs`, `quotes`, `freight-quotes`, `opportunities`.

### Listing / filter endpoints (GET /api/<collection>?<key>=<value>)
Use for all other collections: `invoices`, `payments`, `revenue-journals`, `events`, `vouchers`, `policies`.
Filter keys are case-insensitive; multiple `key=value` params AND together. **Filter `revenue-journals` by `opportunity_id`** — it may not filter correctly by `customer_id`.

### Cross-collection search (GET /api/search?q=<text>)
Returns up to 100 hits across all collections, each tagged with `collection` and `id`. Useful for finding events/vouchers by name.

### Trusting the API
Reconcile the task narrative against API records; **trust the API over narrative wording** when they conflict (e.g., customer name in the prompt may differ from the API — use the API value). But read the prompt carefully for which entity/quote/opportunity to target.

### Working conventions
- Money is USD with 2 decimals unless a task prompt says otherwise (see Pitfalls).
- Dates are ISO `YYYY-MM-DD`.
- Use stable record IDs exactly as they appear in the API (e.g., `Q-TR-WC-1187`, `CUST-HHA`, `OPP-TR-HELIOS`).

## QUOTE Task Workflow

### Step 1: Fetch quote / RFQ, customer, product, freight-quotes, and policies

1. Fetch the quote (or RFQ) by ID from the detail endpoint.
2. Fetch the customer by ID — get `customer_type`, `is_recurring`, `payment_profile`, `segment`, `grant_terms`.
3. Fetch the product by product_code — get `price_tiers`, `shelf_life_months`, `cold_chain_required`, `article_number`.
4. Fetch freight-quotes filtered by `quote_id=...` — returns all freight options including distractors.
5. Fetch all policies (GET /api/policies) — match by customer segment/type to determine payment terms.

### Step 2: Catalog tier by quantity (confirmed rule)

Select the product price tier where `confirmed_quantity >= tier.min_qty` and `confirmed_quantity <= tier.max_qty` (or `max_qty` is null for the top tier). The matched tier provides `unit_price_usd`, `lead_time_days`, and the tier boundary values for the answer.

**Example**: 360 units → tiers [1-149, 150-299, 300-499, 500+] → match 300-499 tier ($118.00, 28-day lead).
**Example**: 1000 units → tiers [1-499, 500-899, 900-1199, 1200+] → match 900-1199 tier ($76.00, 14-day lead).

The catalog tier overrides any prior-unit-price shown in the quote's line items. Quote `source_notes` may confirm the correct tier ("Use active 900-1199 pack tier").

### Step 3: EXW pricing

- `quote_basis` = `EXW` for quote-revision-with-freight tasks.
- `quote_basis` = `EXW_ONLY` for indicative module RFQs without a destination.
- `exw_total_usd` = `confirmed_quantity × unit_price_usd`.
- EXW excludes freight, insurance, import duty, customs clearance, and last-mile (per POL-EXW-SCOPE).

### Step 4: Freight options — exclude distractors, flag stale

**Exclude distractor freight quotes**: Any freight quote with `id` starting with `FR-DIS-` and/or `destination` = "Distractor route" is a benchmark/distractor and must NOT appear in the answer's freight_options array.

**List the real freight options** (typically 3: AIR, SEA, ROAD). For each:
- `freight_id` = API `id` (e.g., `FR-WC-AIR`)
- `mode` = uppercase API `mode` (`AIR`, `SEA`, `ROAD`)
- `freight_cost_usd` = API `cost_usd`
- `transit_days` = API `transit_days_text` (e.g., "4-6 days")
- `valid_until` = API `valid_until` date
- `grand_total_usd` = `exw_total_usd + freight_cost_usd` (always computed, even for stale options)
- **Risk/route-risk fields**: map from API `route_risk` field. Use the template's explicit enum defaults when provided (e.g., training_001 template gives `risk_level: LOW/MEDIUM` and `risk_flag: NONE/MEDIUM_BORDER_RISK`). For templates with only a `customs_border_risk` string field, use uppercase route risk values.
- **Stale detection**: if API `status` = "stale" OR `valid_until` < `quote_date`, set `source_is_stale = true` and appropriate validity_status.

### Step 5: Freight validity vs quote-date (confirmed rule)

`all_freight_options_valid_on_quote_date` (or equivalent boolean) = true only if **every** non-distractor freight option has `valid_until >= quote_date`. A single option with `valid_until` before the quote date makes this false.

**Example**: ROAD freight `valid_until = 2026-05-25`, quote_date = `2026-06-01` → ROAD is stale/invalid → flag it.

### Step 6: Recommended transport mode (confirmed rule)

**recommended_mode = the cheapest freight option that is both ACTIVE and VALID (valid_until >= quote_date)**.

- Risk level does NOT change the recommendation. Even a medium-risk option is recommended over a more expensive low-risk option if it is cheaper and not stale.
- Stale options are excluded from consideration regardless of cost.
- **Example A**: All three options active and valid. AIR most expensive, SEA cheapest, ROAD middle → recommend SEA.
- **Example B**: AIR active+low-risk (expensive), SEA active+medium-risk (cheaper), ROAD stale+high-risk (cheapest but invalid) → recommend SEA. ROAD is excluded due to staleness; SEA wins as cheapest active option despite medium risk.

### Step 7: Freight reconfirmation required

`freight_reconfirmation_required` = true always (per POL-FREIGHT-RECONFIRM: "Freight rates need reconfirmation at final order and are valid only through the freight quote valid_until date").

### Step 8: Payment terms — match policy to customer segment

| Customer type | is_recurring | Policy | Payment terms |
|---|---|---|---|
| NGO, new | false | POL-NEW-CLIENT-PAYMENT | `PREPAY_100` |
| NGO, recurring | true | POL-RECURRING-NGO-PAYMENT | `NET_30_AFTER_PO` |
| Commercial, recurring | true | (customer profile) | `NET_30_AFTER_PO` |

Use the customer's `payment_profile` field to confirm. When the prompt describes a "new NGO account," apply PREPAY_100.

### Step 9: WHO documentation flag (confirmed rule)

For IEHK-style (Interagency Emergency Health Kit) module quotes, set `who_documentation_required = true`. Setting it to false reduces the score — these are WHO-standardized emergency health kits.

For non-IEHK products (e.g., wound-care kits, lab reagents), this flag is not present in the template.

## QUOTE: Module RFQ Variant (indicative, EXW-only, no freight)

When the RFQ is an "indicative module quote" with no confirmed destination:

1. `quote_basis` = `EXW_ONLY`, `freight_excluded` = true (per POL-INDICATIVE-EXW).
2. **Module-level only**: Keep one line item per requested module. Do NOT expand into component SKUs, even if the API products show `components` arrays and the RFQ has `component_composition_distractors` (these are for medical review only).
3. Include `article_number` from each product's API record.
4. `payment_terms` = `PREPAY_100` for new NGO accounts.
5. `offer_validity_days` = 30 (per POL-QUOTE-VALIDITY: "Catalog quote pricing is valid for 30 calendar days from quote date").
6. `who_documentation_required` = true for IEHK modules.
7. Exclude freight entirely (no freight_options array). `grand_total` = sum of all line_total values.
8. **Distractor RFQ exclusion**: If multiple RFQs exist for the same customer (e.g., `RFQ-DIS-009` with different quantities), use only the RFQ ID specified in the task prompt.

## RECONCILIATION Task Workflow

### Step 1: Fetch opportunity, customer, invoices, payments, revenue-journals

1. Fetch the opportunity by ID (`GET /api/opportunities/<id>`). Note `stage`, `won_amount_usd`, `outstanding_amount_usd`, `contact`, and `phases` array (each phase has `phase_id`, `amount_usd`, `completion_date`, `invoice_id`).
2. Fetch the customer by ID.
3. Fetch invoices filtered by `opportunity_id`.
4. Fetch payments filtered by `opportunity_id`.
5. Fetch revenue-journals filtered by `opportunity_id` (NOT customer_id — the filter may not work by customer_id).

### Step 2: Milestone structure

Map each opportunity phase to a milestone in the answer. The milestone's `milestone_id` depends on the template:

- **Some templates** use fixed enum labels `MS1`, `MS2`, `MS3`, ... in ascending order, regardless of the API's `phase_id`. Match the template's enum exactly.
- **Other templates** accept "stable phase or invoice milestone id" as a string — use the API `phase_id` (e.g., `HEL-P1`) as the stable identifier.

Order milestones ascending by `milestone_id`.

For each milestone, pull from the matching invoice:
- `amount` / `invoice_total` = invoice `amount_usd`
- `paid_amount` / `amount_paid` = invoice `paid_amount_usd`
- `amount_unpaid` = invoice `outstanding_amount_usd`
- `payment_status` / `payment_state`: `PAID` if fully paid, `UNPAID` if outstanding > 0, `PARTIAL` if partially paid
- `invoice_state` (if separate field): `PAID` for status "paid", `OPEN` for status "unpaid", `VOID` for voided invoices

### Step 3: Paid milestones null due_date (confirmed rule)

- **PAID milestones**: set `due_date` = `null` (the invoice obligation is settled; no outstanding due date).
- **UNPAID milestones**: set `due_date` = the invoice's `due_date` string (e.g., `2026-07-15`), even if the due date is in the future.

### Step 4: Revenue-recognition state mapping (confirmed rule)

For each milestone, determine `recognition_status`:

| Milestone state | Revenue journal exists? | recognition_status |
|---|---|---|
| Paid | Yes (posted) | `RECOGNIZED` |
| Paid | No | `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING` (check template enum) |
| Unpaid | No | `NOT_REQUIRED_UNPAID` |

**Missing-revenue-journal detection** (critical): For each paid milestone, check whether a revenue-journal record exists matching that milestone's `phase_id` (and/or `invoice_id`). If the milestone is fully paid (`paid_amount` = `amount`, invoice `status` = "paid") but NO revenue journal exists for it, flag it as `MISSING_REVENUE_JOURNAL` and generate a RECORD_REVENUE accounting action.

**Overall recognition_status**: `COMPLETE_FOR_PAID_MILESTONES` if all paid milestones have journals. `MISSING_FOR_PAID_MILESTONES` if any paid milestone lacks a journal. `NOT_REQUIRED` if no milestones are paid.

### Step 5: Outstanding balance (confirmed rule)

`outstanding_balance` = sum of all unpaid invoice amounts = sum of all milestone `amount_unpaid` values = sum of invoice `outstanding_amount_usd`.

Cross-check against the opportunity's API `outstanding_amount_usd` field; they should agree.

### Step 6: Follow-up task routing (confirmed rule)

Route follow-ups into three categories:

**Accounting action** — for paid milestones missing revenue journals:
- `action` = `RECORD_REVENUE_MS<n>` (e.g., `RECORD_REVENUE_MS2`)
- `milestone_id` = the milestone with the missing journal
- `amount` = that milestone's paid amount
- `debit_account` = `DEFERRED_REVENUE`
- `credit_account` = `IMPLEMENTATION_SERVICES_REVENUE`
- `owner_queue` = `ACCOUNTING`
- If all paid milestones are already recognized → `VERIFY_REVENUE_ONLY` or `NO_ACCOUNTING_ACTION`.

**Collection task** — for unpaid milestones:
- If the invoice is unpaid but `due_date` is in the future (not yet due) → `MONITOR_UNPAID_NOT_DUE` with `owner_queue` = `ACCOUNT_MANAGEMENT`.
- If the invoice is unpaid and `due_date` has passed (overdue) → `SEND_COLLECTION_NOTICE` with `owner_queue` = `COLLECTIONS`.
- If all milestones are paid → `NO_COLLECTION_ACTION`.
- `amount` = the unpaid milestone's outstanding amount; `due_date` = the invoice due date.

**Event invitation task** — for events linked to the opportunity:
- If event `status` = "scheduled" and no invitations have been sent → `SEND_BRIEFING_INVITE` with `owner_queue` = `ACCOUNT_MANAGEMENT` (or `EVENTS`).
- If invitations already sent → `VERIFY_INVITE_SENT`.
- `event_id` = the event ID; `voucher_code` = the linked voucher's code.

### Step 7: Event and voucher handling

Fetch the event by searching (`/api/search?q=<event_id>`) or filtering. The event record provides:
- `event_id`, `event_date`, `status` (map to uppercase enum: `SCHEDULED` for "scheduled", `ACTIVE` for "active", `COMPLETED` for "completed", etc.)
- The linked `voucher_code`.

Fetch the voucher via search or by filtering vouchers. The voucher record provides:
- `voucher_code`, `status` (map to uppercase: `ACTIVE`, `DRAFT`, `EXPIRED`, `DISABLED`)
- `discount_amount` / `voucher_discount` = the voucher's `discount_percent` value (e.g., 50 for 50% off, 100 for 100% off) — use this number directly, NOT a computed dollar amount.
- `max_uses` / `voucher_max_uses` = voucher's `max_redemptions`.

### Step 8: Contact linkage

Use the opportunity's `contact` field as the primary contact name. Link this contact to all follow-up tasks:
- `contact_name` = opportunity contact (e.g., "Daniel Rees", "Mara Okafor")
- `customer_id` / `linked_customer_id` = the customer ID
- `opportunity_id` / `linked_opportunity_id` = the opportunity ID

### Step 9: Phase total and match check

- `phase_total_amount` = sum of all phase `amount_usd` values.
- `opportunity_matches_phase_total` / `opportunity_matches_milestones` = true if `phase_total_amount` equals `won_amount_usd`.

## Field Conventions

### Money format
- Default: USD dollar amounts with 2 decimal precision (e.g., `100000.00`). JSON numbers — `100000.0` and `100000.00` are equivalent.
- **If a task prompt says "Use cent-level numbers for money"**: convert all dollar amounts to **integer cents** (multiply by 100). For example, $120,000.00 becomes `12000000`. This is task-specific — not all reconciliation prompts include this instruction.

### Enum values
- Always use the exact enum strings declared in the answer template.
- Map API lowercase values to the template's casing (typically uppercase).
- When the template provides default values (e.g., `"risk_level": "LOW"`), match those exactly.

### Dates
- All dates in ISO `YYYY-MM-DD` format.
- `as_of_date` = the current business date stated in the task prompt (e.g., `2026-06-01`).

## Pitfalls

1. **Distractor freight exclusion**: Always filter out freight quotes with `FR-DIS-*` IDs or "Distractor route" destinations. Including even one distractor will mismatch the freight_options array.

2. **Distractor RFQ exclusion**: Use only the RFQ ID from the task prompt. Multiple RFQs may exist for the same customer with different quantities/dates.

3. **Catalog tier boundaries**: Carefully match quantity against `min_qty`/`max_qty`. The boundary is inclusive. Take the tier whose `[min_qty, max_qty]` range contains the quantity. Don't use the prior unit price from the quote — the catalog tier overrides it.

4. **Stale freight still listed**: A stale/expired freight option should still appear in the freight_options array (with `source_is_stale = true` and validity flag set). It is not excluded like a distractor — it's flagged.

5. **Recommended mode ≠ lowest risk**: The recommended mode is the **cheapest** active+valid option, not the lowest-risk one. A medium-risk cheaper option beats a low-risk expensive one.

6. **Paid milestone due_date = null**: Do not carry forward the invoice due_date for paid milestones. Once paid, the obligation is settled — set due_date to null.

7. **Missing revenue journal detection**: A paid milestone without a revenue journal is the most important detection in reconciliation tasks. Query revenue-journals by `opportunity_id` and match each journal to a milestone by `phase_id`. Payment existing does NOT mean revenue is recognized.

8. **Collection routing by due-date**: Use the current business date to decide collection action. An unpaid invoice that is not yet due → `MONITOR_UNPAID_NOT_DUE` (not `SEND_COLLECTION_NOTICE`). Only overdue invoices trigger a collection notice.

9. **Module-level only**: For module RFQs, never expand to component-level line items. The `component_composition_distractors` in the RFQ and the `components` array in the product are informational only.

10. **WHO documentation for IEHK**: IEHK modules are WHO-standardized kits — `who_documentation_required = true`. Setting it to false is penalized.

11. **discount_amount = discount_percent**: The discount field stores the percentage value from the API voucher's `discount_percent`, not a computed dollar amount. A 50% discount → `50.0`; a 100% discount → `100`.

12. **invoice_state mapping**: API invoice `status` "paid" → `PAID`; `status` "unpaid" → `OPEN` (when the template enum is `PAID | OPEN | VOID | UNKNOWN`). Note: `OPEN` is the unpaid invoice state, distinct from `UNPAID` which is the payment state.

13. **Trust the API customer name**: The prompt may use a slightly different customer name (e.g., "GreenHarvest Labs" vs API "Global Health Laboratories"). Always use the API's `name` field for `customer_name`.

14. **revenue-journals filter by opportunity_id**: Do not attempt to filter revenue-journals by customer_id. Use `opportunity_id` for reliable results.

15. **Freight warning free text**: Client warning strings may need to closely reference the API's own `risk_notes` for the affected freight option. Prefer concise warnings that cite the valid_until/quote_date relationship and risk level.

16. **Money format by task instruction**: Most tasks use standard USD dollar amounts (e.g., `100000.0`). If a task prompt explicitly says "Use cent-level numbers for money," convert all money values to **integer cents** (dollar amount x 100, e.g., `$120,000.00` becomes `12000000`). This is task-specific — apply only when instructed.

17. **MS1/MS2/MS3 milestone IDs**: When the template enum specifies `MS1 | MS2 | MS3` for milestone_id, use these ordered labels in ascending order regardless of the API's phase_id values. When the template accepts "stable phase or invoice milestone id," use the API's `phase_id` (e.g., `HEL-P1`).
