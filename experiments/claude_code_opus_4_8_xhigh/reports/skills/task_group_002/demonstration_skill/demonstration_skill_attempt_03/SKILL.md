---
name: medbridge-sales-ops
description: >-
  Produce account-ready JSON decision packages from the MedBridge Sales Ops API
  for CRM / quote / logistics / receivables tasks. Use this whenever a task asks
  you to build or verify a quote decision package, freight/transport comparison,
  EXW or module-level quote, catalog-tier pricing, route/border risk and freight
  validity flags, recommended transport mode, payment terms, or an
  opportunity/invoice/payment/revenue-recognition reconciliation with CRM
  follow-up routing — especially when the prompt references a MedBridge / "Sales
  Ops" API base URL (e.g. API_BASE_URL / BASE_URL / http://127.0.0.1:<PORT>),
  quote IDs (Q-...), RFQ IDs (RFQ-...), freight IDs (FR-...), opportunity IDs
  (OPP-...), invoices (INV-...), or asks to "return only JSON matching
  input/payloads/answer_template.json". Trigger even if the user only describes
  the business outcome (e.g. "reconcile this account", "compare freight options",
  "indicative module quote") without naming the API.
---

# MedBridge Sales Ops — Account-Ready JSON Packages

This skill turns MedBridge Sales Ops API records into the exact JSON an account
manager needs. The API is the **single source of truth** — never invent or
recall numbers; every value must trace back to a fetched record. Output is
**JSON only**, matching the task's `answer_template.json` exactly (no markdown,
no prose, no extra keys).

## Golden rules (apply to every task)

1. **Read the template first.** Open `input/payloads/answer_template.json`. It
   declares the exact keys, value types, controlled enums, and string
   conventions the grader expects. Mirror its structure 1:1 — same keys, same
   order is safe, no additions, no omissions. When the template embeds an enum
   list in a value (e.g. `"enum: WON | OPEN | LOST"`), you MUST output one of
   those literal tokens.
2. **The API source is authoritative; the prompt narrative is intent, not data.**
   Confirmed quantities, quote dates, and IDs are stated in the prompt but
   always reconcile them against the quote/RFQ record. If the prompt and a
   record disagree, prefer the record the prompt points you to, and let the
   record's own fields (tier, status, dates) drive computed values.
3. **Money at cent precision, dates ISO `YYYY-MM-DD`, IDs verbatim.** Use the
   stable record IDs exactly as returned (e.g. `FR-WC-SEA`, `INV-HELIOS-P1`).
4. **Beware the loose filter.** List endpoints (`?quote_id=...`,
   `?opportunity_id=...`) match a value *anywhere* in the record and return
   extra unrelated rows. Never trust a filtered list blindly. Fetch the full
   collection and filter precisely yourself on the field you care about, and
   drop any record whose `status` marks it as not-real (see exclusion rules).
5. **Compute, don't copy hopeful-looking fields.** Derive totals and statuses
   from primitive fields (quantity × tier price, valid_until vs quote_date,
   invoice/payment/journal cross-checks). Do not assume a convenient
   pre-aggregated field is correct.

## API quick reference

Base URL comes from the runner (env `API_BASE_URL` / `BASE_URL`, or
`http://127.0.0.1:<PORT>`). Reach it with `curl -s`.

| Need | Endpoint |
|---|---|
| Customer (payment profile, segment, contacts, recurring flag) | `/api/customers/<id>` |
| Product (price_tiers, shelf_life_months, article_number, cold_chain) | `/api/products/<code>` |
| RFQ (requested modules/quantities, incoterm, destination) | `/api/rfqs/<id>` |
| Quote (line_items, confirmed_quantity, quote_date, incoterm) | `/api/quotes/<id>` |
| Freight quotes (cost, mode, route_risk, valid_until, status) | `/api/freight-quotes` (fetch all, filter by `quote_id`) |
| Policies (payment terms, validity, freight reconfirm, revrec) | `/api/policies` |
| Opportunity (stage, won_amount, phases, contact) | `/api/opportunities/<id>` |
| Invoices / Payments / Revenue journals | `/api/invoices`, `/api/payments`, `/api/revenue-journals` |
| Events / Vouchers | `/api/events`, `/api/vouchers` |
| Last resort lookup | `/api/search?q=<text>` |

Detail endpoints (`/api/<collection>/<id>`) return one record. Prefer them when
you know the ID. For freight/invoice/payment/journal work, pull the **whole
collection** and match precisely — the safest path.

## Choosing the task family

Read the prompt and template, then route to one SOP:

- **Quote + Freight decision package** — prompt gives a quote ID with a confirmed
  quantity and asks for revised EXW pricing, freight/transport options, route
  risk, recommended mode, validity/reconfirmation, payment terms. Template has
  `freight_options` / `transport_decisions`. → **SOP A**.
- **Indicative / module-level EXW quote** — prompt references an RFQ, asks to
  quote at module level only with freight excluded (often no destination, new
  client). Template has `quote_header` + `line_items` + `quote_controls`. → **SOP B**.
- **Engagement / receivables reconciliation** — prompt names an opportunity and
  customer, asks to reconcile milestones, invoices, payments, revenue
  recognition, and route follow-up tasks (collection + event invite). Template
  has `milestones`, `revenue_recognition`/`invoice_actions`, `event`/`event_actions`.
  → **SOP C**.

---

## SOP A — Quote + Freight decision package

Fetch: the quote, its customer, the primary product, all freight-quotes, and
policies.

### A1. Catalog tier & EXW pricing
- Confirmed quantity = the quote's `confirmed_quantity` (and/or line item). The
  catalog **tier override** replaces any prior/old unit price in the line — use
  the current catalog tier, never `prior_unit_price_usd`.
- Select the tier from `product.price_tiers` where
  `min_qty ≤ confirmed_quantity ≤ max_qty`. A `max_qty` of `null` means
  unbounded (open-ended top tier). Pick exactly one tier.
- `unit_price_usd` and `lead_time_days` come from that tier.
  `shelf_life_months` comes from the **product root** (not the tier).
- `exw_total_usd = confirmed_quantity × tier.unit_price_usd` (cents).
- `quote_basis`: `EXW` when the template uses a bare basis field; use
  `EXW_PLUS_FREIGHT_OPTIONS` where the template's policy/basis field expects the
  freight-inclusive form (the quote's incoterm is "EXW plus freight options").

### A2. Selecting the right freight options
- From the full freight collection, keep only rows whose `quote_id` **exactly**
  equals this quote's ID.
- **Exclude distractors and non-real rows.** Drop any record whose `status` is
  `stale`, `mismatch`, or otherwise not `active` **for the purpose of being a
  recommendable, real option** — but you usually still must *report* all three
  canonical modes (air/sea/road) the template lists, including a stale road row,
  with its true flags. Always drop IDs that are explicitly distractors
  (`FR-DIS-*`, "Distractor route" destination, risk_notes like "benchmark",
  "Wrong shipment size", "Archived", "Unrelated"). The genuine options share the
  quote's real destination and shipment weight/CBM; distractors do not.
- Order the options as the template orders them (typically AIR, SEA, ROAD).

### A3. Per-option fields
- `mode`: uppercase (`AIR` / `SEA` / `ROAD`).
- `freight_cost_usd`: the row's `cost_usd`.
- `transit_days`: use the row's `transit_days_text` ("4-6 days") when the
  template shows a units suffix; use the bare range ("3-5") when the template's
  example omits "days". Match the template's example format.
- `valid_until`: the row's `valid_until`.
- `grand_total_usd = exw_total_usd + freight_cost_usd`.
- **Risk mapping** from `route_risk`:
  - `low`  → `risk_level: LOW`,    `risk_flag: NONE`,  `customs_border_risk: LOW`
  - `medium` → `risk_level: MEDIUM`, `risk_flag: MEDIUM_BORDER_RISK`, `customs_border_risk: MEDIUM`
  - `high` → `risk_level: HIGH`,   `risk_flag: HIGH_BORDER_RISK` (or template's high form), `customs_border_risk: HIGH`
- **Validity / staleness** (compute against the quote_date):
  - `validity_status`: `VALID` if `status == active` AND `valid_until ≥ quote_date`; else `STALE` (expired or status stale).
  - `source_is_stale`: true if `status == stale` OR `valid_until < quote_date`.
  - `road_quote_invalid_or_stale` / similar warning booleans: true when the road
    option is expired or stale.

### A4. Recommendation & control flags — feasibility vs. risk are separate
- `recommended_mode`: choose the **cheapest grand_total among ELIGIBLE options
  only**. An option is eligible only if it is **VALID (not stale/expired) AND
  not HIGH border risk**. This is the load-bearing judgment: a stale or
  high-risk road lane can have the lowest grand total and must STILL be rejected.
  In practice SEA (cheap, valid, low risk) usually wins over a cheaper but
  stale/high-risk road option. Do not recommend a mode you flagged as
  stale/invalid.
- `freight_reconfirmation_required`: `true` — policy `POL-FREIGHT-RECONFIRM`
  ("RECONFIRM_AT_ORDER") makes freight always reconfirm at final order.
- `all_freight_options_valid_on_quote_date`: true only if every reported option
  is valid on the quote date; false if any is expired/stale.
- `freight_warning`: a one-sentence client note when something is wrong —
  state that freight needs reconfirmation at final order, name the stale/expired
  freight ID, its expiry date, and its high customs/border risk, and that it
  must not be used without a fresh quote.

### A5. Payment terms & customer policy
- `payment_terms` = the customer's `payment_profile`, validated against policy:
  - Recurring NGO / recurring account → `NET_30_AFTER_PO` (policy
    `POL-RECURRING-NGO-PAYMENT`), unless restricted grant terms say otherwise.
  - New NGO / new client without approved credit → `PREPAY_100`
    (`POL-NEW-CLIENT-PAYMENT`).
- `customer_policy` (when the template asks for it): the segment label in the
  controlled form, e.g. `RECURRING_NGO`. Derive from the customer `segment`
  (`recurring_ngo` → `RECURRING_NGO`).

---

## SOP B — Indicative / module-level EXW quote

Fetch: the RFQ, its customer, each requested product, and policies.

- `quote_header`: `rfq_id`, `customer_id`, `quote_date` (from prompt/RFQ),
  `currency: "USD"`, `quote_basis: "EXW_ONLY"`.
- **Quote at module level only.** RFQs may include a "component composition" or
  composition table — that is for medical review only (policy
  `POL-MODULE-GRANULARITY`, "MODULE_LINES"). **Do NOT split modules into
  component SKUs.** One `line_item` per requested module, in the RFQ's order.
- Per line: `product_code`, `article_number` (product root), `quantity` (from
  the RFQ's requested module), `unit_price` (the matching price tier — most
  modules have a single open tier; otherwise select by quantity bracket),
  `lead_time_days` (tier), `shelf_life_months` (product root),
  `line_total = quantity × unit_price`.
- `quote_controls`:
  - `grand_total = Σ line_total` (cents).
  - `freight_excluded: true` — no destination ⇒ EXW only, freight excluded
    (`POL-INDICATIVE-EXW`).
  - `payment_terms`: from customer/policy. New NGO ⇒ `PREPAY_100`.
  - `offer_validity_days`: `30` (catalog quote validity, `POL-QUOTE-VALIDITY`,
    "QUOTE_VALID_30_DAYS") unless overridden.
  - `who_documentation_required`: `true` for WHO/IEHK-style emergency health kit
    modules.

---

## SOP C — Engagement / receivables reconciliation

Fetch: the opportunity, customer, and the full invoices, payments,
revenue-journals, events, and vouchers collections. Filter each precisely on
`opportunity_id` (and cross-check `customer_id`) — never trust loose filters.
Treat the prompt's "current business date" (often 2026-06-01) as `as_of_date`.

### C1. Account / opportunity status
- `stage`: map opportunity `stage` to the template enum (`closed_won` → `WON`).
- `won_amount` = opportunity `won_amount_usd`.
- `phase_total_amount` = Σ of the opportunity's phase `amount_usd`.
- `opportunity_matches_milestones` / `opportunity_matches_phase_total`:
  `won_amount == phase_total` (within cents).
- `outstanding_balance` = Σ unpaid invoice `outstanding_amount_usd` for this
  opportunity (equivalently won_amount − total paid). Cross-check against the
  opportunity's own `outstanding_amount_usd`.
- `total_paid_amount` = Σ posted payments for this opportunity.
- `contact` / `primary_contact`: the account contact named in the prompt (also
  on the opportunity/event). Tie every follow-up task to this contact and to
  `linked_customer_id` / `linked_opportunity_id`.

### C2. Per-milestone reconciliation (one phase = one milestone)
Order milestones ascending (MS1, MS2, MS3 / phase 1,2,3). Map each opportunity
phase → its invoice (by `phase_id`/`invoice_id`) → its payment(s) → its revenue
journal.
- `milestone_id`: stable label (`MS1`/`MS2`/... or the phase id). Match the
  template's enum form. `phase_number` is the ordinal.
- `invoice_total` / `amount` = invoice `amount_usd` (= phase amount).
- `invoice_state` (when asked): `paid`→`PAID`; `unpaid`/`overdue`/`draft`→`OPEN`
  (use template's enum, e.g. `OPEN`); follow the template's allowed tokens.
- `payment_status` / `payment_state`: `PAID` if paid_amount ≥ amount; `PARTIAL`
  if 0 < paid < amount; `UNPAID` if no posting.
- `amount_paid` / `paid_amount` = invoice `paid_amount_usd` (sum of posted
  payments). `amount_unpaid` = invoice `outstanding_amount_usd`.
- **`due_date` — paid-milestone nulling:** if the milestone is **fully PAID**,
  output `due_date: null` (a paid milestone has no live due date / no collection
  clock). Only **unpaid** milestones carry their invoice `due_date`. This is a
  deliberate convention; do not leak the original due date on a paid line.
- `revenue_recognition_status` / `recognition_status`:
  - **RECOGNIZED** — milestone is complete AND paid AND a posted revenue journal
    exists for it (debit Deferred Revenue → credit Implementation Services
    Revenue).
  - **MISSING (REQUIRED_MISSING / MISSING_REVENUE_JOURNAL)** — milestone is
    complete AND paid but **no** revenue journal exists. This requires action.
  - **NOT_REQUIRED_UNPAID** — milestone is unpaid; recognition is not yet due,
    it just stays outstanding and drives a collection task.
  Rule of thumb (policy `POL-REVREC`, "RECOGNIZE_PAID_COMPLETE_MILESTONES"):
  recognize **paid + complete** milestones; unpaid future milestones stay
  outstanding.

### C3. Rolled-up revenue recognition block (if template has one)
- `recognition_status`:
  `COMPLETE_FOR_PAID_MILESTONES` if every paid milestone already has a journal;
  `MISSING_FOR_PAID_MILESTONES` if any paid milestone lacks one;
  `NOT_REQUIRED` if nothing is paid yet.
- `recognized_milestones`: paid milestones with a journal.
- `missing_required_milestones`: paid milestones lacking a journal.
- `recognized_amount`: Σ amounts of journaled (recognized) milestones.

### C4. Accounting & collection actions (state-driven enums)
Pick the action that matches the account's actual state and the template's enum
vocabulary.
- **Accounting action**:
  - If a paid milestone is missing its journal → record it. e.g.
    `primary_accounting_action: RECORD_REVENUE_MS2`, `accounting_action.action:
    RECORD_REVENUE_MS2`, `milestone_id` = that milestone, `amount` = its value,
    `debit_account: DEFERRED_REVENUE`, `credit_account:
    IMPLEMENTATION_SERVICES_REVENUE`, `owner_queue: ACCOUNTING`.
  - If all paid milestones are already recognized → `VERIFY_REVENUE_ONLY`
    (or the template's "no missing" form), `NONE` accounts, no owner action.
  - If nothing paid → `NO_ACCOUNTING_ACTION`.
- **Collection action / task** (one per relevant unpaid milestone):
  - Unpaid but **not yet due** (due_date ≥ as_of_date) → `MONITOR_UNPAID_NOT_DUE`
    / `COLLECTION` with `next_action: COLLECT_UNPAID_MILESTONE`, owner
    `ACCOUNT_MANAGEMENT`.
  - Unpaid and **overdue** (due_date < as_of_date) → `SEND_COLLECTION_NOTICE`,
    owner `COLLECTIONS`.
  - Nothing unpaid → `NO_COLLECTION_ACTION`.
  - Include `milestone_id`, `amount`/`amount_due`, the unpaid invoice `due_date`,
    and the account `contact_name`.

### C5. Event / voucher block & invite routing
- Match the event and voucher to this opportunity/customer (exact link, not loose
  filter).
- `event_id`, `event_date`; `event_status` mapped to the template enum
  (`scheduled`→`SCHEDULED`, `confirmed`/`live`→`ACTIVE` per the template's tokens,
  `completed`→`COMPLETED`).
- Voucher facts: `voucher_code`; `voucher_discount`/`discount_amount` = the
  voucher's `discount_percent` value (output as the number the template shows,
  cent precision if it asks for USD-style two decimals); `voucher_max_uses`/
  `max_uses` = `max_redemptions`; `voucher_status` = `active`→`ACTIVE`.
- Invite action: if the event is upcoming/scheduled and the invite hasn't gone →
  `SEND_BRIEFING_INVITE` / `SEND_EVENT_INVITATION`, owner `ACCOUNT_MANAGEMENT`,
  with `contact_name`, `customer_id`, `event_id`, `voucher_code`.
- For an event-invitation follow-up task, the `due_date` is the invite-send
  date the template implies (typically ahead of the event_date — match the
  template; leave milestone/amount fields null on an invite task and event/
  voucher fields null on a collection task).

---

## Common misjudgments — do NOT do these

- **Do not use prior/old unit prices.** Quote line items carry
  `prior_unit_price_usd`/`prior_quote_quantity`; these are history. The current
  catalog tier overrides them.
- **Do not include distractor or stale freight as real options.** `FR-DIS-*`,
  "Distractor route", and benchmark/archived/mismatch rows are traps. Match on
  the exact `quote_id` plus real destination/shipment size, and honor `status`.
- **Do not recommend the cheapest option blindly.** Eligibility (valid +
  acceptable risk) gates the cheapest-grand-total choice. Feasibility/validity
  and risk are separate from price and override it.
- **Do not split RFQ modules into components.** Module RFQs are quoted at module
  line level unless the customer explicitly asks for component pricing.
- **Do not carry a due_date on a fully paid milestone.** Paid → `due_date: null`.
- **Do not mark a paid milestone RECOGNIZED unless a posted revenue journal
  actually exists** for it. Missing journal on a paid milestone = the action
  item (RECORD_REVENUE…), not a silent pass.
- **Do not add freight to an indicative no-destination quote.** EXW only,
  freight excluded.
- **Do not add explanatory prose, markdown fences, or extra keys.** Return only
  the JSON object the template defines.
- **Do not invent IDs, dates, or amounts.** If a value isn't in a fetched
  record, find the record — don't guess.

## Final checklist before returning

1. Output parses as JSON and matches the template's keys/structure exactly.
2. Every controlled-enum field uses a literal token from the template.
3. Money is cent-precise; dates are ISO; IDs are verbatim from records.
4. Totals recomputed from primitives (qty×price; EXW+freight; Σ phases; Σ paid).
5. Recommended mode is eligible (valid + acceptable risk), not just cheapest.
6. Paid milestones have null due_date; recognition status reflects real journals.
7. Follow-up tasks are tied to the correct contact, customer, and opportunity.
8. No prose outside the JSON.
