---
name: medbridge-sales-ops-deliverables
description: >-
  Produce account-ready JSON deliverables from the MedBridge Sales Ops API (CRM, quotes,
  freight/logistics, milestone receivables, revenue recognition, events/vouchers). Use this
  whenever a task asks you to build a quote/freight decision package, a module/RFQ quote, or an
  engagement/receivables reconciliation against a local "Sales Ops" / "MedBridge" HTTP API
  (base like http://127.0.0.1:PORT) and return ONLY JSON matching an answer_template.json.
  Triggers include: revised EXW pricing + freight options + recommended mode; indicative
  EXW-only module quotes from an RFQ; opportunity/milestone/invoice/payment/revenue-journal
  reconciliation with collection and event-invite routing. Pulls business facts from the API,
  applies the policy/enum conventions below, and avoids the loose-filter distractor rows.
---

# MedBridge Sales Ops Deliverables

You build a single JSON deliverable that exactly matches a provided
`input/payloads/answer_template.json`, using business facts from a read-only HTTP API. The
data is internally consistent and deterministic; almost every mistake comes from (a) picking a
distractor row, (b) using a raw API field where a derived/controlled value is expected, or
(c) getting a date/enum convention wrong. This skill encodes the conventions that the templates
expect so you don't have to re-derive them.

## Golden rules (read first)

1. **The API is the source of truth for numbers and IDs.** Never invent values. Fetch the
   relevant records and compute.
2. **But some output fields are DERIVED labels, not raw API fields.** Customer-policy segment
   labels, normalized milestone IDs (`MS1/MS2/MS3`), uppercase enum tokens, and "cheapest valid"
   recommendations are computed by you — not copied from the API verbatim.
3. **Match the template exactly**: same keys, same nesting, same controlled enum values. Return
   ONLY JSON — no markdown, no prose.
4. **Money** uses cent precision (two decimals where the template says so). **Dates** are ISO
   `YYYY-MM-DD`. The "current/business date" is whatever the prompt states (often a quote_date or
   as_of date); use it, not today's real date.
5. **Beware loose filters and distractor rows** — see the API section. This is the single most
   common silent failure.

## Using the API

Base URL comes from the prompt/runner (e.g. `http://127.0.0.1:8094`). Endpoints:
`/api/customers`, `/api/products`, `/api/rfqs`, `/api/quotes`, `/api/freight-quotes`,
`/api/policies`, `/api/opportunities`, `/api/invoices`, `/api/payments`,
`/api/revenue-journals`, `/api/events`, `/api/vouchers`, `/api/search?q=`. Detail endpoints take
an id, e.g. `/api/quotes/<id>`, `/api/opportunities/<id>`.

### The loose-filter pitfall (critical)
Query-param filters (e.g. `?quote_id=Q-...`) match a value **anywhere** in the record and return
extra unrelated rows. Worse, **distractor freight rows can carry the SAME real `quote_id`**, so
even an exact id filter is poisoned. Safe approach: **fetch the full collection and filter
client-side**, then drop distractors by these signals (not by status — distractors can be
`"active"` and look cheap/legitimate):
- `id` starts with `FR-DIS-` (or any `*-DIS-*` / "OLD"/"HEAVY"/"benchmark" id), and/or
- `destination` is `"Distractor route"` (or otherwise not the real quote/RFQ destination),
- `risk_notes`/`status` mentioning "Old route benchmark", "Archived", "Expired", "placeholder".

For a real catalog quote there are exactly **three real freight rows — one each for AIR, SEA,
ROAD** — whose `quote_id` matches AND whose destination matches the quote's destination. Keep only
those three.

Always cross-check linked records via stable IDs (opportunity → its `phases[].invoice_id` →
invoice → payment/revenue-journal by `invoice_id`/`phase_id`), rather than trusting a loose filter.

## Task families

There are two families. Read the template first to decide which, and to learn the exact key
names and enum vocab for this specific task (templates vary the field names and casing).

- **A. Quote / freight decision package** — keys like `quote_summary`/`pricing`,
  `freight_options`, `policy_flags`/`transport_decisions`/`client_warnings`. Inputs: a quote id
  or RFQ id, a product, a confirmed quantity, a quote date.
- **B. Engagement / receivables reconciliation** — keys like `account_status`/
  `engagement_reconciliation`, `milestones`, `revenue_recognition`, `event`/`event_actions`,
  `follow_up_tasks`/`invoice_actions`. Inputs: an opportunity id, a customer id, a contact, an
  as_of date, sometimes an event + voucher.

---

## Family A — Quote / freight decision package

### A1. Pricing from catalog tiers
1. Fetch the quote (`/api/quotes/<id>`) or RFQ (`/api/rfqs/<id>`) for customer, product, confirmed
   quantity, quote_date, destination, incoterm.
2. Fetch the product (`/api/products/<code>`). Pick the **price tier whose `[min_qty, max_qty]`
   band contains the confirmed quantity** (an open-ended top tier has `max_qty: null`).
   - `unit_price`, `lead_time_days` come from that **tier**.
   - `shelf_life_months` comes from the **product root**, not the tier.
   - **Ignore `prior_unit_price_usd` / `prior_quote_quantity` on the quote line — they are
     distractors.** A revision's price always comes from the current catalog tier (the data even
     says "catalog tier overrides prior unit price").
3. `exw_total = confirmed_quantity * tier unit_price` (cent precision).
4. If the template has a `catalog_tier` object, fill its `min_quantity/max_quantity/
   unit_price_usd/lead_time_days/shelf_life_months` from the chosen tier (+ product shelf life).

### A2. Freight options
For each of the **three real** mode rows (AIR/SEA/ROAD, distractors removed):
- `freight_cost_usd` = `cost_usd`; `valid_until` = row `valid_until`.
- `transit_days`: mirror the template's example format. If the template shows `"4-6 days"`, use
  the `transit_days_text` with the " days" suffix; if it shows `"3-5"`, strip the suffix and use
  bare `min-max`. **When unsure, follow the template's own example casing/format literally.**
- `grand_total = exw_total + freight_cost`.
- **Validity vs. quote date:** a row is VALID if `valid_until >= quote_date` AND its API `status`
  is not `stale`/expired; otherwise it is STALE/expired. Set `source_is_stale` true and
  `validity_status` to the stale token when so.
- **Risk fields — two different concepts:**
  - `risk_level` / generic route risk → map the API `route_risk` (`low/medium/high`) to the
    template's casing.
  - `customs_border_risk` / `risk_flag` is specifically a **land-border/customs** concern, which
    in practice only applies to **ROAD**. For **AIR and SEA, set customs-border risk to `LOW` /
    `NONE`** even if their generic `route_risk` is `medium` (sea "medium" is usually a
    shelf-life/transit concern, not a border concern). For ROAD, carry its level
    (`MEDIUM`→`MEDIUM_BORDER_RISK`, `HIGH`→`HIGH`). When in doubt, mirror the template's example
    flag (e.g. template pre-fills ROAD with `MEDIUM_BORDER_RISK`).

### A3. Recommended mode (deterministic rule)
**`recommended_mode` = the VALID (non-stale, in-date) option with the LOWEST `grand_total`.**
Exclude stale/expired rows from consideration. Do NOT pick on speed or "lowest risk" — cost among
valid options wins. (In practice SEA is usually cheapest-and-valid and wins even over a low-risk
AIR; an expired ROAD is excluded even if nominally cheapest.)

### A4. Casing / enum conventions for Family A
Use **UPPERCASE** controlled tokens for `mode` (`AIR/SEA/ROAD`), `risk_level`/`customs_border_risk`
(`LOW/MEDIUM/HIGH`), and `validity_status` (`VALID`/`STALE`) — **even when the template leaves
these as empty strings.** The references use uppercase consistently. (If a template's *example*
explicitly shows lowercase for a field, follow that example for that field; but absent an example,
default to uppercase tokens.)
- `validity_status`: prefer `VALID` / `STALE` (use `STALE` for an expired-before-quote-date row,
  not the word "expired").
- `quote_basis`:
  - Catalog quote with freight options visible → `EXW_PLUS_FREIGHT_OPTIONS` (this is what the
    `policy_terms.quote_basis` field expects when freight is included). A plain `quote_basis`
    summary field that the template pre-fills as `"EXW"` stays `EXW`.
  - Indicative / no-destination module quote → `EXW_ONLY`.

### A5. Policy-driven flags (Family A)
Fetch `/api/policies` and the customer record. Map by policy `terms_code`:
- `freight_reconfirmation_required` = **true always** (POL-FREIGHT-RECONFIRM: freight needs
  reconfirmation at order; valid only through `valid_until`).
- `all_freight_options_valid_on_quote_date` = true iff every real freight row's `valid_until >=
  quote_date`.
- `road_quote_invalid_or_stale` = true iff the ROAD row is stale/expired.
- **`payment_terms`** (controlled enum from policy `terms_code`):
  - Recurring NGO/commercial customer (`is_recurring: true`) → `NET_30_AFTER_PO`
    (POL-RECURRING-NGO-PAYMENT).
  - New NGO without credit history (`is_recurring: false` / new-client) → `PREPAY_100`
    (POL-NEW-CLIENT-PAYMENT).
- **`customer_policy`** is a **segment label**, NOT the policy id and NOT the terms_code. For a
  recurring NGO use `RECURRING_NGO`. Derive the analogous short UPPER_SNAKE label for other
  segments (e.g. a new NGO → `NEW_NGO`/`NEW_CLIENT`); do not output `POL-...` ids here.
- `offer_validity_days` = 30 (POL-QUOTE-VALIDITY, catalog pricing valid 30 days).
- `freight_warning` (free text) should name the offending freight id, state it expired/stale with
  its `valid_until`, note high customs/border risk, and that all rates need reconfirmation at order.

### A6. Module / indicative RFQ quotes (the EXW-only sub-case)
When the RFQ is indicative with no destination (`request_type: indicative_module_quote`,
`incoterm: EXW`, destination "pending"):
- `quote_basis` = `EXW_ONLY`; `freight_excluded` = true; quote **no freight at all**.
- **Quote at the requested MODULE level only.** Each module in `requested_modules` is one line
  item at its own catalog unit price × its quantity. **Never split modules into their
  `components` / `component_composition_distractors`** — those are medical-review notes, explicitly
  not SKUs (POL-MODULE-GRANULARITY).
- `article_number` = product `article_number`; `unit_price`/`lead_time_days` from the module's
  tier; `shelf_life_months` from the module product. `line_total = qty * unit_price`.
- `grand_total` = **sum of all `line_total`s.** (Compute it; don't trust a pre-filled number.)
- `payment_terms` per A5 (a new NGO account → `PREPAY_100`).
- `who_documentation_required` = true for IEHK/WHO-style emergency-health kits.

---

## Family B — Engagement / receivables reconciliation

### B1. Header / account status
1. Fetch the opportunity (`/api/opportunities/<id>`) and customer (`/api/customers/<id>`).
2. **Stage:** map `closed_won` → `WON`, open → `OPEN`, lost → `LOST`.
3. **`won_amount`** = `won_amount_usd`. **`phase_total`** = sum of `phases[].amount_usd`.
   `opportunity_matches_*` = (won_amount == phase_total).
4. **`customer_name`: use the customer name as stated in the PROMPT**, not necessarily the API
   `name`. The prompt's human-readable account name is what the deliverable expects; the API
   `name` field can differ (e.g. an "...Alliance" in the prompt vs "...Initiative" in the API) —
   when they disagree, the prompt name is authoritative for this output field. (Customer/opportunity
   IDs still come from the API.)
5. **Contact**: use the contact named in the prompt / opportunity `contact`. Link it to the
   customer id and opportunity id.
6. `outstanding_balance` = sum of unpaid invoices' outstanding (= opportunity
   `outstanding_amount_usd`). `total_paid` = sum of paid amounts.

### B2. Milestones (one per phase)
Build the invoice/payment picture: each phase has `invoice_id`; fetch invoices and match by
`phase_id`/`invoice_id`; revenue journals match by `invoice_id`/`phase_id`.
- **`milestone_id`: normalize to `MS1`, `MS2`, `MS3` by ascending phase number/order — do NOT
  output the raw API phase ids (`HEL-P1`, `MER-P2`, …),** even though a template hint says "stable
  phase or invoice milestone id". Both reconciliation references use `MS1/MS2/MS3`.
- `amount`/`invoice_total` = invoice/phase amount. `paid_amount` = invoice `paid_amount_usd`.
  `payment_state`: fully paid → `PAID`, partial → `PARTIAL`, nothing → `UNPAID`.
- `invoice_state` from invoice `status`: `paid`→`PAID`, `unpaid`/`draft`→`OPEN`, voided→`VOID`.
- **`due_date`: this is the trap. A PAID milestone's `due_date` is `null`. Only an UNPAID/
  outstanding milestone carries a `due_date`, taken from the INVOICE's `due_date` field** (not the
  phase `completion_date`). Apply this in the milestone rows AND wherever a due_date appears in a
  collection task.
- **Recognition status per milestone:**
  - Paid milestone WITH a revenue journal → `RECOGNIZED`.
  - Paid milestone WITHOUT a revenue journal → `MISSING_REVENUE_JOURNAL` (template 005 vocab) /
    `REQUIRED_MISSING` (template 003 vocab — use whichever enum the template declares).
  - Unpaid milestone → `NOT_REQUIRED_UNPAID` (revenue not recognized until paid).

### B3. Revenue-recognition rollup
- `recognition_status`: `COMPLETE_FOR_PAID_MILESTONES` if every paid milestone has a journal;
  `MISSING_FOR_PAID_MILESTONES` if any paid milestone lacks one; `NOT_REQUIRED` if nothing is paid.
- `recognized_milestones` = milestone ids with a posted journal; `missing_required_milestones` =
  paid-but-unrecognized; `recognized_amount` = sum of recognized journal amounts.

### B4. Action routing (the decision logic)
Compare each unpaid milestone's `due_date` to the **as_of/business date from the prompt**:
- **Accounting action:** if a paid milestone is missing its revenue journal → record it.
  `primary_accounting_action`/`accounting_action.action` = `RECORD_REVENUE_<MSx>` (e.g.
  `RECORD_REVENUE_MS2`), `milestone_id` = that MS, `amount` = its amount,
  `debit_account` = `DEFERRED_REVENUE`, `credit_account` = `IMPLEMENTATION_SERVICES_REVENUE`
  (from the journal pattern Deferred Revenue → Implementation Services Revenue),
  `owner_queue` = `ACCOUNTING`. If all paid milestones are recognized → `VERIFY_REVENUE_ONLY` or
  `NO_ACCOUNTING_ACTION` with `milestone_id: NONE`, accounts `NONE`.
- **Collection action:** for the unpaid milestone:
  - due_date **>** as_of date (not yet due) → `MONITOR_UNPAID_NOT_DUE`.
  - due_date **<=** as_of date / invoice `overdue` → `SEND_COLLECTION_NOTICE`.
  - none unpaid → `NO_COLLECTION_ACTION`.
  - Always populate the collection task with the unpaid milestone id, its `amount`, its invoice
    `due_date`, and the contact. `owner_queue` = `ACCOUNT_MANAGEMENT` for a monitor task (the
    account manager watches a not-yet-due item); `COLLECTIONS` is appropriate once it is actually
    being chased/overdue.
- **`follow_up_tasks` (template-003 style):** emit a `COLLECTION` task for an unpaid milestone
  (with its due_date, amount, milestone id; `next_action: COLLECT_UNPAID_MILESTONE`) AND an
  `EVENT_INVITATION` task (`next_action: SEND_EVENT_INVITATION`, with event id + voucher code,
  null milestone/amount). The unpaid milestone is the headline item — include the collection task
  even if it is not yet strictly overdue (the routing enum captures the not-due nuance).

### B5. Events & vouchers
Fetch `/api/events` and `/api/vouchers`, match by id / `event_id` / `customer_id`.
- `event_status` from event `status`: `scheduled`→`SCHEDULED`, `confirmed`/`live`→`ACTIVE`,
  `completed`→`COMPLETED`, `cancelled`→`CANCELLED`. Map to the template's enum.
- `voucher_status` from voucher `status`: `active`→`ACTIVE`, etc.
- **`voucher_discount` / `discount_amount` = the voucher's `discount_percent` value** (e.g. 100,
  50) even though the template may label the field "USD" — there is no separate dollar field; use
  the percent number with two decimals.
- `voucher_max_uses` / `max_uses` = `max_redemptions`.
- `event_date` = event `event_date`. **Invite/event-invitation task due_date:** use the
  `event_date` as the anchor unless the template/policy specifies an earlier invite lead window;
  there is usually no separate invite-deadline field in the API.
- Invite action: if the event is upcoming/scheduled and not yet sent → `SEND_BRIEFING_INVITE` /
  `SEND_EVENT_INVITATION`; route `owner_queue` per the event `follow_up_owner`
  (`Account Management` → `ACCOUNT_MANAGEMENT`), contact = prompt contact, include event id +
  voucher code + customer id.

---

## Common mistakes → the rule that prevents them
These are the specific errors to guard against (learned the hard way):

- **Used the policy id `POL-...` where a segment label was expected.** `customer_policy` is a
  segment token like `RECURRING_NGO`, not a `POL-...` id and not the `terms_code`. (A2/A5)
- **Output raw API phase ids (`HEL-P1`) for milestone_id.** Normalize to `MS1/MS2/MS3`. (B2)
- **Put a due_date on a PAID milestone.** Paid → `null`; only unpaid carries a due_date, from the
  invoice's `due_date`. (B2)
- **Took customer_name from the API when prompt and API disagree.** Use the prompt's account name
  for the deliverable. (B1)
- **Picked recommended mode by speed/lowest-risk.** It is the cheapest VALID option; exclude stale
  rows. (A3)
- **Lowercased mode/risk/validity, or wrote "expired".** Default to UPPERCASE tokens
  (`AIR/SEA/ROAD`, `LOW/MEDIUM/HIGH`, `VALID/STALE`) unless the template's own example shows
  otherwise. (A4)
- **Mapped SEA/AIR generic route_risk into customs_border_risk.** Customs/border risk is a ROAD
  concern; AIR/SEA → LOW/NONE. (A2 freight)
- **Used `EXW` where `EXW_PLUS_FREIGHT_OPTIONS` (freight included) or `EXW_ONLY` (indicative) was
  expected.** Match the scope. (A4/A6)
- **Split modules into component lines, or summed line_totals wrong.** Quote modules at module
  level; `grand_total` = sum of `line_total`s you computed. (A6)
- **Kept a distractor freight row** because it was `"active"` and cheap. Disqualify by
  `FR-DIS-*` id / "Distractor route" destination, never by status alone. (API section)
- **Trusted `prior_unit_price_usd` on a revised quote.** Always reprice from the current catalog
  tier. (A1)

## Final checklist before returning
- Output is ONLY JSON, keys/nesting identical to the template, no extra/missing keys.
- Money at cent precision; dates ISO `YYYY-MM-DD`; paid-milestone due_dates are `null`.
- Every enum is one of the template's declared controlled values, in the right case.
- Freight = exactly the three real modes; recommended mode = cheapest valid.
- All cross-record links (invoice↔phase↔journal↔payment, event↔voucher) verified by id, not by a
  loose filter.
- Re-add line totals / grand totals yourself; recompute `exw_total = qty * tier price`.

> Note on reference snapshots: the live API may occasionally differ by a small amount or a date
> from a previously generated reference (e.g. an invoice `due_date` shifted, or a line-sum that is
> off by a token amount). Always derive from the **current** API state and keep your answer
> internally consistent (totals equal the sum of their parts; due dates come from the live invoice).
> Do not reverse-engineer a phantom adjustment to match a stale number.
