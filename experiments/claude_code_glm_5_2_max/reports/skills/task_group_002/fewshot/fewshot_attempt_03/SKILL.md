---
name: medbridge-sales-ops-reconcile
description: Reconcile MedBridge Sales Ops CRM tasks (B2B medical wholesale + implementation-services) against the remote Sales Ops API and emit the account-ready JSON answer. Covers QUOTE decision packages (EXW pricing, freight options, route risk, recommended mode, payment terms) and milestone RECONCILIATION packages (invoice/payment state, outstanding balance, revenue-recognition coverage, CRM follow-up routing, event/voucher linkage). Use whenever a task references MedBridge, quotes like Q-TR-*, RFQ-TR-*, opportunities like OPP-TR-*, milestones MS1/MS2/MS3, freight-quotes, revenue-journals, or the shared Sales Ops API base URL.
---

# MedBridge Sales Ops — Reconciliation & Quote Decision Skill

Executable rules for producing the single `answer.json` that matches `input/payloads/answer_template.json` exactly. Source of truth is the **remote Sales Ops HTTP API** (base URL supplied by the runner; treat `http://127.0.0.1:${PORT}` / `API_BASE_URL` placeholders in prompts as that same remote base). Trust API records over narrative wording for IDs and attributes, **except echo the customer name exactly as the task prompt states it** (see §7).

## 1. API access contract

- Base URL: the runner-provided `API_BASE_URL` (a remote host such as `<remote-env-url>`). Never start a local server; never read any `env/` directory.
- `GET /health` — sanity check.
- `GET /api` — lists `collections` and `endpoints`.
- `GET /api/<collection>` — list all records (`{collection, count, records}`).
- `GET /api/<collection>?<key>=<value>` — filter (case-insensitive, matches nested keys, numeric tolerance 2dp; multiple filters AND). Filter invoices/payments/revenue-journals/events/vouchers by `opportunity_id`; freight-quotes by `quote_id`.
- `GET /api/<collection>/<id>` — detail by id. **Detail-by-id works ONLY for:** `customers`, `products`, `rfqs`, `quotes`, `freight-quotes`, `opportunities`. For `invoices`, `payments`, `revenue-journals`, `events`, `vouchers`, `policies` use listing/filter (or `/api/search?q=...` which returns full records tagged with collection+id).
- `GET /api/search?q=<text>` — substring search across ALL collections (up to 100 hits). Use to resolve events/vouchers by code or id.
- Money = USD 2 decimals. Dates = ISO `YYYY-MM-DD`. Use stable record IDs verbatim.

Collections: `customers, products, rfqs, quotes, freight-quotes, policies, opportunities, invoices, payments, revenue-journals, events, vouchers`.

## 2. Pick the task family and template variant

Read the prompt + `answer_template.json` top-level keys first; the template dictates field names and enum values exactly.

- **QUOTE family** — prompt mentions a quote (`Q-TR-*`) or RFQ (`RFQ-TR-*`), confirmed quantity, EXW pricing, freight options, route risk, recommended mode, payment terms.
  - Variant A (keys: `quote_summary`, `freight_options`, `policy_flags`) — quote revision with freight, single product, EXW basis `EXW`.
  - Variant B (keys: `quote_header`, `line_items`, `quote_controls`) — **indicative module RFQ**, EXW-only, freight excluded, basis `EXW_ONLY`.
  - Variant C (keys: `pricing`, `transport_decisions`, `client_warnings`) — quote revision with freight, exposes `catalog_tier` block, validity_status/source_is_stale per freight option, basis `EXW_PLUS_FREIGHT_OPTIONS` in policy_terms.
- **RECONCILIATION family** — prompt mentions an opportunity (`OPP-TR-*`), milestones, invoices, payments, revenue recognition, event/voucher, follow-up tasks.
  - Variant R1 (keys: `account_status`, `milestones`, `revenue_recognition`, `event`, `follow_up_tasks`) — milestone rows use `payment_status`, `revenue_recognition_status` enum `RECOGNIZED|REQUIRED_MISSING|NOT_REQUIRED_UNPAID`; follow_up_tasks list with `task_type COLLECTION|EVENT_INVITATION`.
  - Variant R2 (keys: `engagement_reconciliation`, `invoice_actions`, `event_actions`) — milestone rows use `invoice_state`+`payment_state`+`recognition_status` (enum `RECOGNIZED|MISSING_REVENUE_JOURNAL|NOT_REQUIRED_UNPAID|UNKNOWN`); structured `accounting_action`/`collection_task`/`invite_task`.

Match the variant, then produce exactly those keys. Do not invent or rename fields.

## 3. QUOTE family — common data fetch

1. `GET /api/quotes/<quote_id>` (or `/api/rfqs/<rfq_id>` for variant B). Pull `customer_id`, `quote_date`, `primary_product_code`/`requested_modules`, `confirmed_quantity`, `incoterm`, `destination`, `quote_type`.
2. `GET /api/customers/<customer_id>` → `name`, `segment`, `is_recurring`, `customer_type`, `payment_profile`, `grant_terms`.
3. `GET /api/products/<product_code>` → `article_number`, `price_tiers`, `shelf_life_months`, `family`.
4. `GET /api/policies` (full list) — apply by `policy_area`.
5. For variants A/C: `GET /api/freight-quotes?quote_id=<quote_id>` → all freight options.

### 3.1 Catalog tier & EXW pricing
- Select the `price_tiers` entry where `min_qty <= confirmed_quantity <= max_qty` (treat `max_qty: null` as unbounded). Use that tier's `unit_price_usd` and `lead_time_days`.
- `shelf_life_months` comes from **product.shelf_life_months**, NOT the tier.
- `exw_total_usd` = `confirmed_quantity * unit_price_usd` (2 decimals).
- `article_number` = `product.article_number`.
- The quote may carry `prior_unit_price_usd`/`prior_quote_quantity` — **ignore**; the confirmed quantity's tier always overrides any prior price.

### 3.2 Freight selection — real options vs distractors
Freight collections include deliberate distractors. **Exclude** any record where: `id` starts with `FR-DIS-`, OR `destination` is `"Distractor route"`, OR `shipment_cbm`/`shipment_weight_kg` is inconsistent with the dominant (correct) shipment size for that quote. The remaining records (one per mode: air, sea, road) are the genuine options — include a stale one and flag it (do not silently drop it).

For each genuine freight option derive:
- `freight_id`, `mode` = `freight.mode` UPPERCASE (`AIR`/`SEA`/`ROAD`).
- `freight_cost_usd` = `cost_usd`.
- `transit_days` = `transit_days_text` (e.g. `"4-6 days"`) for Variant A; for Variant C use the bare `"<min>-<max>"` form (e.g. `"3-5"`) — match the template variant.
- `valid_until` = `valid_until`.
- `risk_level` (Variant A) = `route_risk` UPPERCASE (`LOW`/`MEDIUM`/`HIGH`).
- `risk_flag` (Variant A) = `NONE` when low risk; `MEDIUM_BORDER_RISK` when `route_risk=medium` and/or notes mention border risk; `HIGH_BORDER_RISK` when `route_risk=high`.
- `customs_border_risk` (Variant C) reflects **customs/border exposure**, not the general route risk: `HIGH` when `route_risk=high` or `risk_notes` mention high customs/border; `MEDIUM` when notes mention a medium border risk; otherwise `LOW`. (A medium route_risk that is purely transit/shelf-life, e.g. LD SEA, stays `LOW`.)
- `validity_status` (Variant C) = `VALID` when `status=="active"` AND `valid_until >= quote_date`; `STALE` when `status=="stale"` OR `valid_until < quote_date`.
- `source_is_stale` (Variant C) = true when `status=="stale"`.
- `grand_total_usd` = `exw_total_usd + freight_cost_usd`.

### 3.3 Recommended mode, reconfirmation, validity flags
- `recommended_mode` = mode of the **VALID** freight option (not stale, valid on quote date) with the **lowest `grand_total_usd`** among options whose customs/border risk is not `HIGH`. This yields `SEA` when SEA is valid and cheaper than AIR, with a stale/high-risk ROAD excluded. Reconfirm the rule against the actual options present.
- `freight_reconfirmation_required` = **always true** (policy `POL-FREIGHT-RECONFIRM` applies to every freight quote — rates must be reconfirmed at final order and are valid only through `valid_until`).
- `all_freight_options_valid_on_quote_date` (Variant A) = true iff every included option is `VALID` (active and `valid_until >= quote_date`). False if any is stale/expired.
- `road_quote_invalid_or_stale` (Variant C `client_warnings`) = true iff the ROAD option is stale or expired on the quote date.
- `freight_warning` (Variant C) = human sentence: `"Freight rates require reconfirmation at final order. <stale_freight_id> expired on <valid_until> and has high customs or border risk, so it should not be used without a fresh quote."` (omit the stale clause if none stale).

### 3.4 Payment terms & customer policy (all quote variants)
Read `customer.payment_profile` and cross-check `policies` (`payment_terms` area):
- `NEW_CLIENT_REVIEW` (or `is_recurring==false`, `segment=="new_ngo"`) → `PREPAY_100` (policy `POL-NEW-CLIENT-PAYMENT`: new NGO clients require prepay before production release).
- `NET_30_AFTER_PO` (recurring NGO or recurring commercial) → `NET_30_AFTER_PO` (policy `POL-RECURRING-NGO-PAYMENT`), unless grant terms explicitly restrict.
- `customer_policy` (Variant A) = `customer.segment` UPPERCASED with underscores (e.g. `recurring_ngo` → `RECURRING_NGO`, `recurring_commercial` → `RECURRING_COMMERCIAL`, `new_ngo` → `NEW_NGO`).

### 3.5 Variant B — indicative module RFQ specifics
- `quote_basis` = `EXW_ONLY`; `freight_excluded` = true (policies `POL-INDICATIVE-EXW` + `POL-EXW-SCOPE`: no destination ⇒ EXW only, freight/insurance/duty/customs/last-mile all excluded).
- One `line_items` entry per `rfq.requested_modules` item, **at module line level only** (policy `POL-MODULE-GRANULARITY`). Ignore `component_composition_distractors` and any product `components` list — never split into component SKUs even though the API exposes them.
- Each line: `product_code`, `article_number` (product.article_number), `quantity` (rfq), `unit_price` (the module's single tier price), `lead_time_days` (tier), `shelf_life_months` (product), `line_total` = `quantity * unit_price`.
- `grand_total` = sum of `line_total`.
- `offer_validity_days` = 30 (policy `POL-QUOTE-VALIDITY`).
- `who_documentation_required` = **true** when the RFQ is for IEHK-style emergency health kit modules (`product.family == "emergency_health_kit"`); otherwise false unless the prompt/records state otherwise.

### 3.6 Variant A/C quote_basis placement
- Variant A `quote_summary.quote_basis` = `"EXW"`.
- Variant C `client_warnings.policy_terms.quote_basis` = `"EXW_PLUS_FREIGHT_OPTIONS"`.
- Both also set `payment_terms` and `freight_reconfirmation_required` inside their respective policy blocks.

## 4. RECONCILIATION family — common data fetch

1. `GET /api/opportunities/<opportunity_id>` → `customer_id`, `contact`, `stage`, `won_amount_usd`, `outstanding_amount_usd`, `phases` (each with `phase_id`, `invoice_id`, `amount_usd`, `completion_date`).
2. `GET /api/customers/<customer_id>` → `name`, `segment`, `payment_profile`, `contacts`.
3. `GET /api/invoices?opportunity_id=<opp>` → per-milestone invoice (`status`, `amount_usd`, `paid_amount_usd`, `outstanding_amount_usd`, `due_date`, `phase_id`).
4. `GET /api/payments?opportunity_id=<opp>` → posted payments (cross-check paid amounts).
5. `GET /api/revenue-journals?opportunity_id=<opp>` → posted revenue journals keyed by `invoice_id`/`phase_id` (debit `Deferred Revenue`, credit `Implementation Services Revenue`).
6. `GET /api/events?opportunity_id=<opp>` and `GET /api/vouchers?opportunity_id=<opp>` (or `/api/search?q=<event_id|voucher_code>`) → linked event + voucher.

### 4.1 Milestone mapping
- Order phases by their natural order (P1, P2, P3 …) and label `MS1`, `MS2`, `MS3` … in ascending order. **Do not** output the API `phase_id` (e.g. `HEL-P2`) as the milestone id — emit the normalized `MS{n}`.
- `milestone.amount`/`invoice_total` = `invoice.amount_usd` (== `phase.amount_usd`; they agree).
- `phase_number` (R1) = 1-based index.
- `opportunity_matches_milestones` (R1) / `opportunity_matches_phase_total` (R2) = `true` iff `sum(phase.amount_usd) == opportunity.won_amount_usd`. `phase_total_amount` (R2) = that sum.

### 4.2 Invoice / payment state (per milestone)
- `paid_amount` / `amount_paid` = `invoice.paid_amount_usd`.
- `amount_unpaid` (R1) = `invoice.outstanding_amount_usd`.
- R1 `payment_status`: `PAID` if `paid_amount == amount`; `UNPAID` if `paid_amount == 0`; `PARTIAL` if `0 < paid_amount < amount`.
- R2 `invoice_state`: `paid`→`PAID`, `unpaid`→`OPEN`, `void`→`VOID`, anything else→`UNKNOWN`.
- R2 `payment_state`: same logic as R1 `payment_status` (`PAID`/`PARTIAL`/`UNPAID`), else `UNKNOWN`.

### 4.3 due_date rule
- **Paid milestone → `due_date: null`** (always, both variants).
- **Unpaid milestone → `due_date` = the invoice's `due_date`** (R2-confirmed: MS3 invoice due_date flows through verbatim).
- Collection follow-up `due_date` = the unpaid milestone's due_date (invoice due_date).
- R1 EVENT_INVITATION follow-up `due_date` = `as_of_date + 30 days` (the as_of/business date stated in or implied by the prompt).
- Known reference quirk: one R1 train case showed a `MS2` collection due of `2026-07-10` while its invoice due_date was `2026-06-27` — no clean derivation exists. For unseen tasks, **prefer the invoice due_date**; the only as_of-anchored reference (R2) confirms invoice due_date is authoritative.

### 4.4 Revenue recognition status
For each milestone, look for a posted revenue-journal whose `invoice_id`/`phase_id` matches:
- Paid milestone **with** a posted revenue journal → `RECOGNIZED` (R1) / `RECOGNIZED` (R2).
- Paid milestone **without** any revenue journal → `REQUIRED_MISSING` (R1) / `MISSING_REVENUE_JOURNAL` (R2). This is the trigger for a record-revenue accounting action.
- Unpaid milestone → `NOT_REQUIRED_UNPAID` (both variants). Unpaid milestones never need revenue recognition.
- R2 also allows `UNKNOWN` as a fallback when invoice state is unknown.

### 4.5 Aggregate revenue recognition (R1 `revenue_recognition` block)
- `recognition_status`: `COMPLETE_FOR_PAID_MILESTONES` if every **paid** milestone has a posted journal; `MISSING_FOR_PAID_MILESTONES` if any paid milestone lacks one; `NOT_REQUIRED` if there are no paid milestones.
- `recognized_milestones` = list of `MS{n}` that have a posted journal.
- `missing_required_milestones` = list of `MS{n}` that are paid but missing a journal.
- `recognized_amount` = sum of posted journal `amount_usd`.

### 4.6 Outstanding balance & paid totals
- `outstanding_balance` = `sum(invoice.outstanding_amount_usd for unpaid milestones)` == `opportunity.outstanding_amount_usd`. Cross-check both; they agree.
- `total_paid_amount` (R2) = `sum(paid milestone amounts)` == `sum(payments.amount_usd)` for posted payments.
- `won_amount` = `opportunity.won_amount_usd`.

### 4.7 Accounting action (R2 `invoice_actions.accounting_action`)
- `action` / `primary_accounting_action`:
  - `RECORD_REVENUE_MS2` when a paid milestone is missing its revenue journal — record revenue for **that** milestone (action string carries the milestone id).
  - `VERIFY_REVENUE_ONLY` when all paid milestones are already recognized (verify only).
  - `NO_ACCOUNTING_ACTION` when there are no paid milestones / nothing to record.
- `milestone_id` = the `MS{n}` needing recording (or `NONE`).
- `amount` = that milestone's amount.
- `debit_account` = `DEFERRED_REVENUE`; `credit_account` = `IMPLEMENTATION_SERVICES_REVENUE` (mirrors the standard posted journal: Deferred Revenue → Implementation Services Revenue). Use `NONE` only when action is `NO_ACCOUNTING_ACTION`.
- `owner_queue` = `ACCOUNTING`.

### 4.8 Collection action (R2 `invoice_actions.collection_task`) / R1 COLLECTION follow-up
- `action` / `collection_action`:
  - `MONITOR_UNPAID_NOT_DUE` when there is an unpaid milestone whose `due_date` is on/after the as_of date (not yet overdue) — monitor.
  - `SEND_COLLECTION_NOTICE` when an unpaid milestone is overdue (`due_date < as_of_date`).
  - `NO_COLLECTION_ACTION` when all milestones are paid.
- `milestone_id` = the unpaid milestone (or `NONE`).
- `amount` / `amount_due` = that milestone's amount.
- `due_date` = unpaid milestone's invoice due_date.
- `owner_queue`: `MONITOR_UNPAID_NOT_DUE` → `ACCOUNT_MANAGEMENT`; `SEND_COLLECTION_NOTICE` → `COLLECTIONS`; `NO_COLLECTION_ACTION` → `NONE`.
- `contact_name` = the opportunity/customer contact (see §4.10).
- R1 produces a `follow_up_tasks` entry with `task_type: COLLECTION`, `next_action: COLLECT_UNPAID_MILESTONE`, `task_title: "Milestone <n> collection - <customer_name>"`, and null `event_id`/`voucher_code` — only when an unpaid milestone exists.

### 4.9 Event & voucher linkage, invite action
From the linked event + voucher records:
- `event_id`, `event_date` = `event.event_date`.
- `event_status` (R2): `scheduled`→`SCHEDULED`, `active`→`ACTIVE`, `completed`→`COMPLETED`, `cancelled`→`CANCELLED`, else `UNKNOWN`. (R1 has no event_status field — only event_id/event_date/voucher fields.)
- `voucher_code` = `voucher.code` (== `event.voucher_code`).
- `voucher_status` (R2): `active`→`ACTIVE`, `draft`→`DRAFT`, `expired`→`EXPIRED`, `disabled`→`DISABLED`, else `UNKNOWN`.
- `voucher_discount` (R1) / `discount_amount` (R2) = `voucher.discount_percent` as a 2-decimal number (e.g. `100`→`100.00`, `50`→`50.00`). The API field is named `discount_percent` but the answer treats its numeric value as the discount amount.
- `voucher_max_uses` (R1) / `max_uses` (R2) = `voucher.max_redemptions`.
- `invite_action` (R2):
  - `SEND_BRIEFING_INVITE` when the event is `SCHEDULED` (or otherwise upcoming) and the invite has not been sent.
  - `VERIFY_INVITE_SENT` when the event is already `ACTIVE`/invitations should already be out.
  - `NO_INVITE_ACTION` when the event is `COMPLETED`/`CANCELLED` or no event exists.
- `invite_task.owner_queue` / event owner = map `event.follow_up_owner`: `"Account Management"`→`ACCOUNT_MANAGEMENT`, `"Events"`→`EVENTS`; else `NONE`.
- `invite_task` fields: `action`, `event_id`, `voucher_code`, `owner_queue`, `contact_name`, `customer_id`.
- R1 produces a `follow_up_tasks` entry `task_type: EVENT_INVITATION`, `next_action: SEND_EVENT_INVITATION`, `task_title: "Send <event-type> invite - <customer_name>"` (e.g. `"Send celebration invite - ..."`), `due_date` = as_of + 30, null `milestone_id`/`amount_due`, populated `event_id`/`voucher_code`.

### 4.10 Contact linkage
- Primary contact name = `opportunity.contact` (a name string). Verify it appears in `customer.contacts[].name`; use the `opportunity.contact` value as displayed.
- R1 `contact`: `{name, linked_customer_id, linked_opportunity_id}`.
- R2 `primary_contact`: `{contact_name, customer_id}`.
- All follow-up tasks carry the contact name + the customer/opportunity ids they belong to.

## 5. Controlled enum value maps (consolidated)

| Field | Allowed values | Derivation |
|---|---|---|
| quote_basis (A) | `EXW` | quote revision with freight |
| quote_basis (B) | `EXW_ONLY` | indicative module RFQ, no destination |
| policy_terms.quote_basis (C) | `EXW_PLUS_FREIGHT_OPTIONS` | quote revision with freight |
| mode | `AIR` / `SEA` / `ROAD` | freight.mode uppercased |
| risk_level (A) | `LOW` / `MEDIUM` / `HIGH` | route_risk uppercased |
| risk_flag (A) | `NONE` / `MEDIUM_BORDER_RISK` / `HIGH_BORDER_RISK` | low / medium-border / high |
| customs_border_risk (C) | `LOW` / `MEDIUM` / `HIGH` | customs/border exposure (see §3.2) |
| validity_status (C) | `VALID` / `STALE` | active+valid_until≥quote_date / else |
| payment_terms | `PREPAY_100` / `NET_30_AFTER_PO` | new-NGO → prepay; recurring → net30 |
| customer_policy (A) | `RECURRING_NGO` / `RECURRING_COMMERCIAL` / `NEW_NGO` … | segment uppercased |
| opportunity_stage / stage | `WON` / `OPEN` / `LOST` | `closed_won`→`WON`, `open`→`OPEN`, `closed_lost`→`LOST` |
| payment_status (R1) | `PAID` / `PARTIAL` / `UNPAID` | paid_amount vs amount |
| invoice_state (R2) | `PAID` / `OPEN` / `VOID` / `UNKNOWN` | invoice.status |
| payment_state (R2) | `PAID` / `PARTIAL` / `UNPAID` / `UNKNOWN` | paid_amount vs amount |
| revenue_recognition_status (R1) | `RECOGNIZED` / `REQUIRED_MISSING` / `NOT_REQUIRED_UNPAID` | paid+journal / paid no journal / unpaid |
| recognition_status (R2 milestone) | `RECOGNIZED` / `MISSING_REVENUE_JOURNAL` / `NOT_REQUIRED_UNPAID` / `UNKNOWN` | same logic, R2 enum names |
| recognition_status (R1 agg) | `COMPLETE_FOR_PAID_MILESTONES` / `MISSING_FOR_PAID_MILESTONES` / `NOT_REQUIRED` | all paid recognized / some missing / none paid |
| primary_accounting_action / accounting_action.action | `RECORD_REVENUE_MS2` / `VERIFY_REVENUE_ONLY` / `NO_ACCOUNTING_ACTION` | missing journal / all recognized / none |
| debit_account | `DEFERRED_REVENUE` / `ACCOUNTS_RECEIVABLE` / `CASH` / `NONE` | milestone rev-rec → DEFERRED_REVENUE |
| credit_account | `IMPLEMENTATION_SERVICES_REVENUE` / `DEFERRED_REVENUE` / `ACCOUNTS_RECEIVABLE` / `NONE` | milestone rev-rec → IMPLEMENTATION_SERVICES_REVENUE |
| accounting owner_queue | `ACCOUNTING` / `ACCOUNT_MANAGEMENT` / `NONE` | accounting action → ACCOUNTING |
| collection_action | `MONITOR_UNPAID_NOT_DUE` / `SEND_COLLECTION_NOTICE` / `NO_COLLECTION_ACTION` | unpaid not due / overdue / all paid |
| collection owner_queue | `ACCOUNT_MANAGEMENT` / `COLLECTIONS` / `NONE` | monitor / send / none |
| task_type (R1) | `COLLECTION` / `EVENT_INVITATION` | per follow-up |
| next_action (R1) | `COLLECT_UNPAID_MILESTONE` / `SEND_EVENT_INVITATION` | per follow-up |
| event_status | `SCHEDULED` / `ACTIVE` / `COMPLETED` / `CANCELLED` / `UNKNOWN` | event.status |
| voucher_status | `ACTIVE` / `DRAFT` / `EXPIRED` / `DISABLED` / `UNKNOWN` | voucher.status |
| invite_action | `SEND_BRIEFING_INVITE` / `VERIFY_INVITE_SENT` / `NO_INVITE_ACTION` | scheduled→send |
| invite owner_queue | `ACCOUNT_MANAGEMENT` / `EVENTS` / `NONE` | event.follow_up_owner mapped |

## 6. Misjudgments & exclusions to avoid

- **EXW excludes freight/insurance/duty/customs/last-mile** (`POL-EXW-SCOPE`). For Variant B (EXW_ONLY) set `freight_excluded: true` and emit **no** freight options / `grand_total` = EXW only. For Variants A/C the EXW line is shown **plus** freight options as separate grand totals — freight is never folded into the EXW unit price.
- **Module-level only** (`POL-MODULE-GRANULARITY`): never expand an IEHK module RFQ into its component lines, even though `product.components` and `rfq.component_composition_distractors` exist. One line item per requested module.
- **Paid milestones → `due_date: null`** (both R1 and R2), regardless of the invoice due_date.
- **Missing revenue journal for a PAID milestone ⇒ `REQUIRED_MISSING` (R1) / `MISSING_REVENUE_JOURNAL` (R2)** and drives a `RECORD_REVENUE_MS2`-style accounting action (do not mark it `RECOGNIZED`). Unpaid milestones are `NOT_REQUIRED_UNPAID` — never invent a journal for them.
- **New-client prepay**: a new-NGO / first-time account (`is_recurring=false`, `segment=new_ngo`, `payment_profile=NEW_CLIENT_REVIEW`) must get `PREPAY_100`, not net terms, even if the prompt sounds like a normal order.
- **WHO documentation flag**: `who_documentation_required=true` for IEHK / `emergency_health_kit` module RFQs; do not set it true for lab diagnostics or wound-care kits.
- **Distractor freight**: never include `FR-DIS-*` records or any whose `destination=="Distractor route"` — but DO include a genuine option that is merely stale (flag it `STALE`/`source_is_stale=true` and surface it in `freight_warning`).
- **Distractor invoice/phase data**: trust `opportunity.phases` + `invoices` filtered by `opportunity_id`; do not pull unrelated invoices by customer that belong to other events.
- **customer_name source**: echo the customer name **as stated in the task prompt** (the gold uses the prompt's name even when `customer.name` differs). Use the API for `customer_id`, `segment`, `payment_profile`, contacts — only the display name follows the prompt.
- **Do not output the API `phase_id`** (e.g. `HEL-P2`, `MER-P3`) as a milestone id — always normalize to `MS1/MS2/MS3`.
- **`freight_reconfirmation_required` is always true** — the reconfirmation policy is universal; do not set false even when all options are valid on the quote date.
- **Revenue journal accounts come from the journal record** (`Deferred Revenue` / `Implementation Services Revenue`); for a missing-journal record action use the same standard accounts, not AR/Cash.

## 7. Output discipline

- Emit **only** valid JSON — no markdown fences, no prose, no trailing commas. Match `answer_template.json` keys, nesting, and enum casing exactly.
- Money: number with 2 decimals (e.g. `42480.0` / `32185.00`). Dates: `YYYY-MM-DD` or `null` where allowed.
- Order arrays as the template implies: milestones ascending by `MS{n}`; freight options in AIR, SEA, ROAD order; follow_up_tasks COLLECTION before EVENT_INVITATION.
- Use stable record IDs verbatim (`Q-TR-WC-1187`, `FR-WC-AIR`, `CUST-HHA`, `OPP-TR-HELIOS`, `EVT-MERIDIAN-BRIEFING`, `MERIDIANBRIEF50`).
- When the prompt and API conflict on an ID or attribute, use the API; when they conflict on the customer display name, echo the prompt.
