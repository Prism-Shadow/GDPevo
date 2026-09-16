---
name: medbridge-sales-ops
description: MedBridge Sales Ops API workflows for humanitarian medical supply chain. Prepares quote decision packages (pricing, freight comparison, policy checks), indicative module RFQ quotes (EXW-only, module-level), and engagement reconciliations (milestone cross-referencing, revenue recognition, collection follow-ups, event/voucher invite tasks). Use for tasks referencing MedBridge Sales Ops, TASK_ENV_BASE_URL, quote IDs prefixed Q-TR, Q-TE, or Q-DIS, RFQ IDs prefixed RFQ-TR or RFQ-TE, opportunity IDs prefixed OPP-TR, customer IDs prefixed CUST-, and medical product codes like WC-KIT, IEHK, LD-REAGENT, MAT-EMERG, CHOL, FCLINIC, or PPE.
---

# MedBridge Sales Ops

Workflows for the MedBridge Sales Ops API: a shared CRM, quote, logistics, and milestone engagement data service for humanitarian medical supply chain at base URL `<TASK_ENV_BASE_URL>` (provided by the task runner).

## Quick Reference

- [API Schema](references/api_schema.md) — full collection list, record shapes, cross-reference keys
- [Business Rules](references/business_rules.md) — tier matching, payment terms, freight validation, revenue recognition, event/voucher tasks

Load the corresponding reference when you need detailed field paths or rule specifics while executing a workflow.

## Overall Approach

1. Identify which workflow the prompt describes: quote decision package, indicative module quote, or engagement reconciliation.
2. Fetch all required API records in parallel where possible. Start with the target record (quote, RFQ, or opportunity), then fan out to linked records (customer, product, freight, invoices, payments, revenue journals, events, vouchers, policies).
3. Apply the business rules from [business_rules.md](references/business_rules.md) to derive computed values.
4. Fill the answer template exactly — every field populated, no invented values, no markdown wrapper.

---

## Workflow 1: Quote Decision Package

**Triggers:** Revised quote with freight comparison. Prompt mentions a quote ID (`Q-TR-WC-...`, `Q-TR-LD-...`, `Q-TE-...`), customer name, product code, confirmed quantity, and quote date. Template keys include `quote_summary`/`pricing`, `freight_options`/`transport_decisions`, and `policy_flags`/`client_warnings`.

### Step 1 — Fetch Core Records

Fetch in parallel:
- `GET /api/quotes/<quote_id>` — the quote
- `GET /api/customers/<quote.customer_id>` — the customer
- `GET /api/products/<quote.primary_product_code>` — the product
- `GET /api/freight-quotes` — all freight records (filter by `quote_id` client-side)
- `GET /api/policies` — all policies (filter by policy_area client-side)

### Step 2 — Determine Pricing

Read the confirmed quantity from the quote or its line items. Match the product's price tier:
- Iterate `product.price_tiers` in order.
- Select the first tier where `min_qty <= confirmed_quantity` and (`max_qty` is null or `confirmed_quantity <= max_qty`).
- Extract `unit_price_usd`, `lead_time_days`, `shelf_life_months`.

Compute `exw_total_usd = confirmed_quantity * unit_price_usd` to two decimals.

### Step 3 — Build Freight Options

Filter freight records to those with `quote_id == <target_quote_id>`. Exclude records where `status` is `stale` or `mismatch`. For each remaining record:

- **Validity:** `valid_until >= quote_date` → VALID; otherwise STALE, `source_is_stale = true`.
- **Grand total:** `exw_total_usd + freight.cost_usd`.
- **Risk:** Uppercase `route_risk`. Derive `risk_flag` from route risk and `risk_notes`.
- Collect AIR, SEA, ROAD in that order.

### Step 4 — Recommend Mode

Pick the lowest-cost valid (non-stale) freight option. If a valid option has HIGH route risk, skip it and recommend the next lowest-cost valid option. If no valid option survives, flag and default to the lowest-cost overall with a warning.

### Step 5 — Policy Flags and Warnings

- `freight_reconfirmation_required`: always true when freight options are included (POL-FREIGHT-RECONFIRM).
- `all_freight_options_valid_on_quote_date`: true only if every collected freight record has `valid_until >= quote_date`.
- `payment_terms`: resolve from customer profile (see business rules).
- For templates with `client_warnings`: include a `freight_warning` if any freight option is stale or has HIGH risk.
- `quote_basis`: `"EXW"` or `"EXW_PLUS_FREIGHT_OPTIONS"` based on incoterm.

### Step 6 — Fill the Template

Use only the exact keys from `answer_template.json`. All money to two decimals. All dates as `YYYY-MM-DD`. Return raw JSON.

---

## Workflow 2: Indicative Module Quote

**Triggers:** RFQ-based module quote with no freight. Prompt mentions an RFQ ID (`RFQ-TR-...`), customer name, module product codes, EXW-only basis. Template keys include `quote_header`, `line_items`, and `quote_controls`.

### Step 1 — Fetch Core Records

Fetch in parallel:
- `GET /api/rfqs/<rfq_id>` — the RFQ
- `GET /api/customers/<rfq.customer_id>` — the customer
- `GET /api/products/<each_requested_module.product_code>` — one per module
- `GET /api/policies` — all policies

### Step 2 — Verify EXW-Only Condition

Check `rfq.destination` — if it says "pending" or "to be confirmed", freight must be excluded. Check `rfq.incoterm_requested` — if `"EXW"`, no freight. Apply policy POL-INDICATIVE-EXW.

### Step 3 — Build Line Items

For each entry in `rfq.requested_modules`:
- Fetch the product by `product_code`.
- Match the price tier to `quantity` (same tier logic as Workflow 1).
- Extract `unit_price`, `lead_time_days`, `shelf_life_months`.
- Compute `line_total = quantity * unit_price` to two decimals.
- Include `article_number` from the product record.

**Critical:** Do not split modules into components. Quote at the module product code level only. The `component_composition_distractors` field in the RFQ warns against this.

### Step 4 — Quote Controls

- `grand_total`: sum of all `line_total` values.
- `freight_excluded`: `true`.
- `payment_terms`: `PREPAY_100` for new NGO clients; otherwise from customer `payment_profile`.
- `offer_validity_days`: `30`.
- `who_documentation_required`: `true` for IEHK, cholera, or field clinic families.

### Step 5 — Fill the Template

Return raw JSON matching the template exactly.

---

## Workflow 3: Engagement Reconciliation

**Triggers:** Account review, milestone reconciliation, event briefing follow-up. Prompt mentions an opportunity ID (`OPP-TR-...`), customer ID (`CUST-...`), a contact name, and optionally event/voucher codes. Template keys include `account_status`/`engagement_reconciliation`, `milestones`, `revenue_recognition`/`invoice_actions`, `event`/`event_actions`, and `follow_up_tasks`.

### Step 1 — Fetch Core Records

Fetch in parallel:
- `GET /api/opportunities/<opportunity_id>` — the opportunity
- `GET /api/customers/<opportunity.customer_id>` — the customer
- `GET /api/invoices` — all invoices (filter by `opportunity_id` client-side)
- `GET /api/payments` — all payments (filter by `opportunity_id` client-side)
- `GET /api/revenue-journals` — all revenue journals (filter by `opportunity_id` client-side)
- `GET /api/events` — all events (filter by `opportunity_id` client-side)
- `GET /api/vouchers` — all vouchers (filter by `opportunity_id` client-side)

### Step 2 — Build Milestone Table

For each phase in `opportunity.phases`:
- Find the invoice by `phase.invoice_id`.
- Determine `payment_status`: PAID if `invoice.status == "paid"`, UNPAID for "unpaid"/"overdue"/"draft".
- `paid_amount` from `invoice.paid_amount_usd`. `unpaid_amount` from `invoice.outstanding_amount_usd`.
- For revenue recognition: if invoice is paid, check for a revenue journal matching `phase_id` or `invoice_id`. If found → RECOGNIZED; if paid but not found → MISSING_REVENUE_JOURNAL; if unpaid → NOT_REQUIRED_UNPAID.

### Step 3 — Reconciliation Summary

- `opportunity_matches_milestones`: sum of `phases[].amount_usd` == `won_amount_usd`.
- `outstanding_balance`: sum of invoice `outstanding_amount_usd` across all invoices for this opportunity.
- Revenue recognition status: COMPLETE_FOR_PAID_MILESTONES if every paid milestone has a journal, MISSING_FOR_PAID_MILESTONES if any paid milestone lacks one.

### Step 4 — Accounting Action

If any paid milestone lacks a revenue journal, generate an accounting action:
- `action`: `RECORD_REVENUE_MS<N>` (N = milestone number, 1-based from phase order).
- `debit_account`: `DEFERRED_REVENUE`.
- `credit_account`: `IMPLEMENTATION_SERVICES_REVENUE`.
- `amount`: the paid invoice amount.
- `owner_queue`: `ACCOUNTING`.

### Step 5 — Collection Task

For each unpaid invoice:
- If `due_date` > current business date → `MONITOR_UNPAID_NOT_DUE`, `owner_queue: ACCOUNT_MANAGEMENT`.
- If `due_date` <= current business date → `SEND_COLLECTION_NOTICE`, `owner_queue: COLLECTIONS`.
- Set `contact_name` to the contact from the prompt.

### Step 6 — Event and Invitation

For the event matching the opportunity:
- Map `event.status`: `"scheduled"` → `SCHEDULED`, `"confirmed"` → `SCHEDULED`, `"live"` → `ACTIVE`, `"completed"` → `COMPLETED`, `"tentative"` → `SCHEDULED`.
- Look up the voucher by `event.voucher_code` (or `voucher.code`). Map voucher `status`: `"active"` → `ACTIVE`, `"draft"` → `DRAFT`, `"expired"` → `EXPIRED`.
- For `voucher_discount`/`discount_amount`: use `discount_percent` from the voucher record.
- If event status is `scheduled` or `confirmed`: `invite_action` = `SEND_BRIEFING_INVITE` (or `SEND_EVENT_INVITATION`, matching the template's enum).
- Invite task `owner_queue`: `ACCOUNT_MANAGEMENT`.
- Set invite task `due_date`: typically 7-14 days before `event.event_date`, or the current business date if the event is sooner.

### Step 7 — Fill the Template

Return raw JSON matching the template exactly. Sort milestones ascending by milestone_id (MS1, MS2, MS3). All amounts to two decimals. All dates as `YYYY-MM-DD`.
