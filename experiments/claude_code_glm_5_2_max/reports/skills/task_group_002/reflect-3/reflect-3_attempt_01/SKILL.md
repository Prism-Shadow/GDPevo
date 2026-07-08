# MedBridge Sales Ops — CRM Reconciliation & Quote Decision Skill

Transferable workflow rules for solving MedBridge Sales Ops CRM tasks against the
remote business API. Covers the two task families: **QUOTE** (reconcile a customer
RFQ/quote into an account-ready quote decision package) and **RECONCILIATION**
(reconcile a won opportunity into a finance-ready engagement reconciliation).

These are reusable SOPs and pitfalls — not answers. Always derive every value from
the live API records for the task's specific quote/RFQ/opportunity.

---

## 0. Environment & API usage

- Business records live ONLY behind the remote HTTP JSON API (`API_BASE_URL`). Do
  not invent records; do not read any local `env/` source. Reconcile the task
  narrative against the API and **trust the API over narrative wording** when they
  conflict (e.g., a customer name in the prompt that differs from
  `customers[].name` — use the API value; use the API `customer_id` linked to the
  quote/RFQ/opportunity even if the prompt names the customer differently).
- Endpoints (all GET unless noted):
  - `GET /api` — service metadata (collections list).
  - `GET /api/<collection>` — list all records (`{collection, count, records}`).
  - `GET /api/<collection>?<key>=<value>` — filter (case-insensitive, matches
    nested keys; multiple filters AND). Use this for collections that have no
    detail-by-id.
  - `GET /api/<collection>/<id>` — single record by id. **Detail-by-id is only
    available for:** `customers`, `products`, `rfqs`, `quotes`, `freight-quotes`,
    `opportunities`. For `invoices`, `payments`, `revenue-journals`, `events`,
    `vouchers`, `policies` use the listing/filter endpoints.
  - `GET /api/search?q=<text>` — substring search across all collections.
- Collections: `customers`, `products`, `rfqs`, `quotes`, `freight-quotes`,
  `policies`, `opportunities`, `invoices`, `payments`, `revenue-journals`,
  `events`, `vouchers`.
- **Revenue-journals have NO `customer_id` and will not filter by customer_id —
  always filter revenue-journals by `opportunity_id`.** (Same safe pattern for
  invoices/payments/events/vouchers: filter by `opportunity_id`.)
- Money = USD with 2 decimals. Dates = ISO `YYYY-MM-DD`. Use stable record IDs
  exactly as they appear in the API.
- Output: return ONLY valid JSON matching the task's `answer_template.json`
  exactly — same field names, same nesting, the controlled enum values declared
  in the template, no markdown fences, no prose.

---

## 1. QUOTE tasks — quote decision package

Trigger: prompt references a quote id (`Q-...`) or RFQ id (`RFQ-...`) and asks
for revised EXW pricing, freight options/totals, route risk, recommended mode,
freight-validity/reconfirmation, and payment terms.

### 1.1 Record gathering
1. Fetch the quote (`/api/quotes/<id>`) or RFQ (`/api/rfqs/<id>`) — note
   `customer_id`, `quote_date`, `primary_product_code`/`requested_modules`,
   `confirmed_quantity`, `incoterm`, `quote_type`.
2. Fetch the customer (`/api/customers/<customer_id>`) — note `segment`,
   `customer_type`, `is_recurring`, `payment_profile`, `grant_terms`.
3. Fetch the product (`/api/products/<code>`) — note `price_tiers`,
   `shelf_life_months`, `article_number`, `cold_chain_required`.
4. Fetch freight quotes: `/api/freight-quotes?quote_id=<quote_id>`.
5. Fetch policies: `/api/policies` (payment_terms, quote_scope, freight,
   quote_validity, incoterms).

### 1.2 Catalog tier by quantity (EXW pricing)
- Pick the `price_tiers` entry where `min_qty <= confirmed_quantity` AND
  (`max_qty` is null OR `confirmed_quantity <= max_qty`). This single tier gives
  `unit_price_usd`, `lead_time_days`, `shelf_life_months`.
- `exw_total_usd` (or `line_total` / `grand_total` for EXW-only) =
  `confirmed_quantity × tier.unit_price_usd`.
- Do NOT use a "prior_unit_price_usd" from the quote line item — the catalog tier
  overrides it (revision quotes raise quantity into a cheaper tier).

### 1.3 Freight options
- **Distractor exclusion:** drop any freight quote whose `id` starts with
  `FR-DIS-` OR whose `destination` contains "Distractor". These are never part of
  the answer.
- Include every REAL freight quote for the quote_id, one per mode (typically
  AIR, SEA, ROAD). Include a stale/expired real option **with its stale flag
  set** — do NOT silently drop it (the stale flag and a client warning are how
  staleness is reported).
- Per-option fields:
  - `freight_id` = the freight quote `id`.
  - `mode` = UPPER(RI mode) (`AIR`/`SEA`/`ROAD`).
  - `freight_cost_usd` = `cost_usd`.
  - `transit_days` = the freight quote's `transit_days_text` string verbatim
    (e.g. `"4-6 days"`).
  - `valid_until` = freight quote `valid_until`.
  - `grand_total_usd` = `exw_total_usd + freight_cost_usd` (compute even for
    stale options).
  - Risk enums (derive from `route_risk`):
    - QUOTE-template `risk_level`: `low→LOW`, `medium→MEDIUM`, `high→HIGH`.
    - QUOTE-template `risk_flag`: `low→NONE`, `medium→MEDIUM_BORDER_RISK`
      (high-risk analog: `HIGH_BORDER_RISK`).
    - DECISION-template `customs_border_risk`: `LOW`/`MEDIUM`/`HIGH`.
  - DECISION-template staleness fields:
    - `source_is_stale` = (`freight quote status == "stale"`).
    - `validity_status` = `VALID` when `valid_until >= quote_date` and status
      active; `EXPIRED` when `valid_until < quote_date` (stale/expired).

### 1.4 Recommended transport mode (KEY RULE)
- **Recommended mode = the CHEAPEST VALID freight option by `grand_total_usd`,
  considering only VALID (active, non-stale, non-distractor) options.**
- Risk level does NOT determine the recommendation — cost among valid options
  does. A low-risk air option does NOT beat a cheaper valid sea option.
  Examples: cheapest valid = SEA when SEA is active and cheapest; AIR only when
  AIR is the sole valid (or cheapest valid) option.
- Stale and distractor options are never recommended.

### 1.5 Policy / control flags
- `freight_reconfirmation_required` = `true` always (policy: freight rates need
  reconfirmation at order; valid only through `valid_until`).
- `all_freight_options_valid_on_quote_date` (QUOTE template) = `true` only if
  every included real option has `valid_until >= quote_date` (i.e., none expired
  before the quote date). A stale/expired real option makes this `false`.
- `quote_basis`:
  - Freight-options quote (`incoterm` "EXW plus freight options") → `"EXW"`.
  - Indicative EXW-only quote (RFQ with no destination) → `"EXW_ONLY"`. Use the
    **template's controlled placeholder value**, NOT the policy `terms_code`
    (`EXW_ONLY_EXCLUDE_FREIGHT`).
- `payment_terms`:
  - New NGO client (`payment_profile` `NEW_CLIENT_REVIEW`, `is_recurring` false,
    `segment` `new_ngo`) → `PREPAY_100`.
  - Recurring NGO / commercial (`payment_profile` `NET_30_AFTER_PO`) →
    `NET_30_AFTER_PO`.
  - Map from the customer's `payment_profile` / the matching payment policy
    `terms_code`.
- `customer_policy` (where present) = customer `segment` (e.g. `recurring_ngo`).
- `offer_validity_days` = `30` (policy: catalog quote pricing valid 30 calendar
  days from quote date).
- `freight_excluded` = `true` for indicative quotes with no destination (EXW
  only); `false`/omit for freight-options quotes.
- `who_documentation_required` = `true` for IEHK-family / WHO-standardized
  emergency-health-kit modules (codes prefixed `IEHK-`); `false` for non-WHO
  products. (Note: products are "IEHK-style" but still trigger the WHO doc flag.)

### 1.6 Module-level quote discipline (RFQ module quotes)
- Output exactly ONE line item per entry in the RFQ `requested_modules`, at
  module granularity: `product_code`, `article_number`, `quantity`,
  `unit_price` (single-tier module price), `lead_time_days`,
  `shelf_life_months`, `line_total = quantity × unit_price`.
- Do NOT expand `components` into line items, and ignore
  `component_composition_distractors` — these are medical-review noise, not
  quoteable SKUs. The customer must explicitly request component-level pricing
  to split a module.
- EXW-only module quote: no freight options block; `quote_basis` `EXW_ONLY`,
  `freight_excluded` true.

---

## 2. RECONCILIATION tasks — engagement/finance reconciliation

Trigger: prompt references an opportunity id (`OPP-...`) and customer id
(`CUST-...`) and asks to reconcile won-amount, milestone invoices, payments,
revenue-recognition coverage, outstanding balance, and CRM/accounting/event
follow-ups. Use the prompt's stated current business date as `as_of_date` and for
due-date comparisons (default `2026-06-01`).

### 2.1 Record gathering
1. Opportunity: `/api/opportunities/<opp_id>` — `stage`, `won_amount_usd`,
   `outstanding_amount_usd`, `contact`, `phases[]` (`phase_id`, `amount_usd`,
   `completion_date`, `invoice_id`).
2. Customer: `/api/customers/<customer_id>` — `name`, `segment`, `contacts`.
3. Invoices: `/api/invoices?opportunity_id=<opp_id>` — `amount_usd`, `status`,
   `paid_amount_usd`, `outstanding_amount_usd`, `due_date`, `phase_id`.
4. Payments: `/api/payments?opportunity_id=<opp_id>` — `amount_usd`, `invoice_id`,
   `status`.
5. Revenue journals: `/api/revenue-journals?opportunity_id=<opp_id>` (NOT by
   customer_id) — `invoice_id`, `phase_id`, `amount_usd`, `status`.
6. Event: `/api/events?opportunity_id=<opp_id>` — `event_date`, `status`,
   `voucher_code`, `primary_contact`, `follow_up_owner`.
7. Voucher: `/api/vouchers?opportunity_id=<opp_id>` — `discount_percent`,
   `max_redemptions`, `status`, `valid_until`.

### 2.2 Milestone identification & ordering
- Each opportunity phase = one milestone, ordered ascending by phase order.
- Where the template declares a milestone_id enum (`MS1 | MS2 | MS3`), use those
  enum values IN PHASE ORDER — NOT the API `phase_id` (`MER-P1`, etc.) and not
  the invoice id. Map phase 1→MS1, phase 2→MS2, phase 3→MS3.
- Where the template allows a freeform "stable phase or invoice milestone id",
  use the API `phase_id` (e.g. `HEL-P1`).
- Money per milestone: `amount`/`invoice_total` = invoice `amount_usd`;
  `paid_amount`/`amount_paid` = invoice `paid_amount_usd`;
  `amount_unpaid` = invoice `outstanding_amount_usd`.

### 2.3 Invoice / payment state enums
- `invoice_state`: invoice `status` `paid`→`PAID`, `unpaid`/`open`→`OPEN`,
  `void`→`VOID`, unknown→`UNKNOWN`.
- `payment_state`: fully paid→`PAID`, partially paid→`PARTIAL`, unpaid→`UNPAID`,
  unknown→`UNKNOWN`. A milestone is `PAID` only if `paid_amount_usd` equals
  `amount_usd` (and a posted payment exists).

### 2.4 due_date rule (KEY)
- **Paid milestone → `due_date: null`** (the obligation is settled; the invoice
  due date is no longer relevant).
- Unpaid milestone → `due_date` = the invoice's `due_date` (ISO string).

### 2.5 Revenue-recognition state mapping (KEY — missing-journal detection)
For each milestone, set `revenue_recognition_status` / `recognition_status`:
- **Paid AND a matching revenue-journal exists** (journal for that
  invoice_id/phase_id, status `posted`) → `RECOGNIZED`.
- **Paid AND NO matching revenue-journal** → `MISSING_REVENUE_JOURNAL`
  (decision template) / `REQUIRED_MISSING` (status template). This is the
  critical defect to detect: a milestone that is complete and paid but whose
  revenue was never recognized (deferred revenue not moved to income).
- **Unpaid** → `NOT_REQUIRED_UNPAID` (no revenue to recognize until paid).
- Unknown/inconsistent → `UNKNOWN` (decision template only).

Top-level `recognition_status` (status template):
- All paid milestones have journals → `COMPLETE_FOR_PAID_MILESTONES`.
- Any paid milestone lacks a journal → `MISSING_FOR_PAID_MILESTONES`.
- `recognized_milestones` = list of milestone ids with journals;
  `missing_required_milestones` = paid milestones lacking journals;
  `recognized_amount` = sum of recognized journal amounts.

### 2.6 Balance & match booleans
- `total_paid_amount` = sum of invoice `paid_amount_usd`.
- `outstanding_balance` = `won_amount − total_paid_amount` (= sum of invoice
  `outstanding_amount_usd`). Must agree with opportunity
  `outstanding_amount_usd`.
- `opportunity_matches_milestones` / `opportunity_matches_phase_total` =
  `(sum of phase amounts == won_amount_usd)`.

### 2.7 Follow-up routing (collection vs accounting vs event-invitation)

**Accounting action** — based on revenue-recognition need:
- A paid milestone MISSING its revenue journal → `RECORD_REVENUE_MSx`
  (`milestone_id` = that MS, `amount` = its invoice amount,
  `debit_account` = `DEFERRED_REVENUE`, `credit_account` =
  `IMPLEMENTATION_SERVICES_REVENUE`, `owner_queue` = `ACCOUNTING`). This is the
  `primary_accounting_action` when present.
- Paid milestone already recognized → `VERIFY_REVENUE_ONLY` (no new posting;
  owner `ACCOUNTING`).
- Unpaid milestones → `NO_ACCOUNTING_ACTION` (`owner_queue` `NONE`).

**Collection action** — based on the unpaid milestone vs current business date:
- Unpaid milestone with `due_date` <= current business date (due/overdue) →
  `SEND_COLLECTION_NOTICE` (`owner_queue` = `COLLECTIONS`,
  `due_date` = invoice due date, `amount` = outstanding).
- Unpaid milestone with `due_date` > current business date (not yet due) →
  `MONITOR_UNPAID_NOT_DUE` (`owner_queue` = `ACCOUNT_MANAGEMENT`,
  `due_date` = invoice due date, `amount` = outstanding).
- No unpaid milestone → `NO_COLLECTION_ACTION` (`owner_queue` `NONE`).

**Event-invitation action** — based on the linked event:
- Event `status` `scheduled`/`confirmed` and upcoming (event_date >= current
  date) with invitation not yet sent → `SEND_BRIEFING_INVITE`
  (`owner_queue` = the event's `follow_up_owner`, typically
  `ACCOUNT_MANAGEMENT`; `event_id`, `voucher_code`, `contact_name`,
  `customer_id` populated).
- Invitation already sent / event active → `VERIFY_INVITE_SENT`.
- No event → `NO_INVITE_ACTION`.
- Event status enum: `scheduled`→`SCHEDULED`, `confirmed`→`ACTIVE`/`CONFIRMED`
  per template, `completed`→`COMPLETED`, `cancelled`→`CANCELLED`.
- Voucher: `voucher_status` from voucher `status` (`active`→`ACTIVE`, `draft`→
  `DRAFT`, `expired`→`EXPIRED`, `disabled`→`DISABLED`);
  `discount_amount` = voucher `discount_percent` value;
  `max_uses` = voucher `max_redemptions`.

### 2.8 Contact linkage
- `primary_contact`/`contact` = the opportunity's `contact` name; link to the
  customer via `customer_id` (and `opportunity_id` where the template field
  exists). Tie every follow-up task to this contact name and the
  customer/opportunity ids.

---

## 3. Cross-cutting pitfalls (from reflect feedback)

1. **Recommended mode is cheapest-VALID, not lowest-risk.** Picking the
   low-risk air option over a cheaper valid sea option is wrong. (Cost among
   active/non-stale/non-distractor options decides.)
2. **Stale real freight options stay in the array, flagged — do not drop them.**
   Only distractors (`FR-DIS-*` / "Distractor" destination) are removed.
3. **Paid milestones get `due_date: null`.** Leaving the invoice due date on a
   paid milestone is wrong.
4. **Detect missing revenue journals explicitly.** A paid milestone with no
   matching revenue-journal is `MISSING_REVENUE_JOURNAL` and drives a
   `RECORD_REVENUE` accounting action — this is the single most important
   reconciliation finding.
5. **Collection routing depends on due date vs current business date.** A
   not-yet-due unpaid milestone is `MONITOR_UNPAID_NOT_DUE` (account
   management), not a collection notice.
6. **Filter revenue-journals (and other finance records) by `opportunity_id`,
   not `customer_id`.** Revenue journals carry no customer_id.
7. **`quote_basis` uses the template's controlled value**, not the policy
   `terms_code` (e.g. `EXW_ONLY`, not `EXW_ONLY_EXCLUDE_FREIGHT`).
8. **`who_documentation_required` is true for IEHK-family modules** even though
   the catalog calls them "IEHK-style".
9. **Module RFQs stay at module line level** — never expand `components` or
   honor `component_composition_distractors`.
10. **Catalog tier overrides prior unit price** on revision quotes; recompute
    EXW total from the tier that matches the confirmed quantity.
11. **Trust API values over prompt narrative** for customer name, ids, amounts,
    and statuses; reconcile which entity the prompt asks about, then read facts
    from that API record.
12. **Use detail-by-id only for the six id-keyed collections**; otherwise list
    + filter. Use stable API ids verbatim.
13. **Freeform string fields (warning messages, task titles) are not reliably
    matchable** — prioritize getting every structured id, amount, date, and enum
    exactly right; for freeform warning text, state the concrete finding
    concisely (which freight id is stale/expired, its valid_until vs quote date,
    the recommendation, the reconfirmation requirement).
14. **Output ordering:** milestones ascending by milestone_id (MS1, MS2, MS3);
    freight options in AIR, SEA, ROAD order unless the template implies
    otherwise.
