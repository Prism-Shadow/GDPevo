# SKILL: MedBridge Sales Ops — B2B Quote + Engagement-Reconciliation Tasks

## Description & when this applies
Use this skill for "MedBridge Sales Ops" CRM/B2B task-group tasks. You get a free-text
prompt (an email-style request), a read-only JSON HTTP API, and an `answer_template.json`.
Your job: read real facts from the API and return ONLY a JSON object that fills the template
exactly. No markdown, no prose, no extra keys, no missing keys — just the JSON.

Two task families occur in this domain:

- **Family A — Quote / Freight decision package.** Prompt names a quote id (e.g. `Q-...`) or
  an RFQ id (e.g. `RFQ-...`), a product/module, a confirmed quantity, and a quote date. You
  return catalog-tier pricing, an EXW total, freight options with totals, route risk, a
  recommended transport mode, validity/reconfirmation flags, and payment terms.
- **Family B — Engagement / milestone reconciliation.** Prompt names an opportunity id
  (`OPP-...`) and customer id (`CUST-...`), a contact, often an event/voucher, and an "as-of"
  business date. You reconcile won amount vs milestone phases, invoice/payment/outstanding
  state, revenue-recognition coverage, and route the right accounting/collection/event tasks.

Match the family by the template shape: pricing/freight keys ⇒ A; milestones/revenue/
opportunity keys ⇒ B.

---

## The data API

Base URL is provided by the runner (env var like `API_BASE_URL` / `BASE_URL`, or
`http://127.0.0.1:<PORT>`). All endpoints are GET and return JSON.

Collections: `customers, products, rfqs, quotes, freight-quotes, policies, opportunities,
invoices, payments, revenue-journals, events, vouchers`.

Useful patterns:
- Single record: `GET /api/<collection>/<id>` (e.g. `/api/quotes/Q-...`, `/api/opportunities/OPP-...`,
  `/api/products/<CODE>`, `/api/customers/<CUST-...>`).
- List + filter: `GET /api/<collection>?field=value` (server flattens nested keys, matches
  case-insensitively, and numbers match their 2-decimal form). Returns
  `{collection, count, records:[...]}`.
- Full-text: `GET /api/search?q=<text>` searches every collection — great for resolving a
  customer by name (e.g. `?q=NovaAid`) or pulling everything tied to an account (`?q=HELIOS`
  returns the customer, opportunity, invoices, payments, journals, event, and voucher in one call).

### Resolving IDs from the prompt
- The prompt usually gives the key id directly (quote/rfq/opportunity/customer/event/voucher).
- If only a company NAME is given, use `/api/search?q=<name>` to get the `CUST-...` id.
- `/api/products/<CODE>` returns `price_tiers`, `article_number`, `shelf_life_months`, `unit`,
  `cold_chain_required`, `components`.

### API gotchas (hit during iteration)
- `revenue-journals` records have NO `customer_id` field — filtering `?customer_id=...` returns 0.
  Filter by `opportunity_id` or fetch the whole collection and match on `opportunity_id`/`phase_id`.
- Freight lists contain DISTRACTORS: records with id `FR-DIS-*` and/or `destination`
  "Distractor route" — never include these in the answer.
- Trust the API record over the prompt for names: prompts paraphrase (e.g. prompt said "Helios
  Health Alliance" but the customer record name is "Helios Health Initiative"; use the record).
- `quotes` may carry `prior_quote_quantity`/`prior_unit_price_usd` — these are OLD values;
  always re-price from the product `price_tiers` using the CONFIRMED quantity.

---

## Output conventions (confirmed)
- Return ONLY the JSON object matching the template. No markdown fences, no commentary.
- Money: numbers with 2 decimals (e.g. `42480.00`). Totals must reconcile exactly.
- Dates: ISO `YYYY-MM-DD`.
- Enums: use the EXACT controlled values printed in the template (UPPERCASE). Map raw API
  strings to the template enum (e.g. API `closed_won` ⇒ template `WON`; API `scheduled` ⇒
  `SCHEDULED`; API `active` ⇒ `ACTIVE`).
- Fill every template key. Use `null` only where the template says "or null" and the value
  genuinely does not apply (see paid-milestone due_date rule below).
- Echo ids/dates exactly as the API spells them.

---

## Catalog tier & EXW math (Family A)
1. `GET /api/products/<CODE>`. Find the tier whose `[min_qty, max_qty]` contains the CONFIRMED
   quantity (`max_qty: null` means open-ended upper bound). Take that tier's `unit_price_usd`,
   `lead_time_days`, and the product's `shelf_life_months`.
2. `exw_total_usd = confirmed_quantity * tier.unit_price_usd` (2 decimals). Per line:
   `line_total = quantity * unit_price`; `grand_total = sum(line_totals)`.
3. `quote_basis` is `EXW` (single-product freight task) or `EXW_ONLY` (indicative no-destination task).
4. For module RFQs: quote at MODULE line level only — one line per requested module, using the
   module's own tier/article/shelf. IGNORE any `component_composition_distractors` / component
   breakdowns; do NOT expand modules into component SKUs.

## Freight options (Family A)
1. `GET /api/freight-quotes?quote_id=<Q-...>`. The real options are the per-mode records named
   `FR-<product>-AIR`, `FR-<product>-SEA`, `FR-<product>-ROAD`. EXCLUDE every `FR-DIS-*` /
   "Distractor route" / wrong-shipment-size record.
2. For each option: `freight_cost_usd = cost_usd`; `transit_days` = the `transit_days_text`
   (e.g. `"4-6 days"`); `valid_until` from the record; `grand_total_usd = exw_total + freight_cost`.
3. Risk mapping:
   - `route_risk` low ⇒ `risk_level` LOW; medium ⇒ MEDIUM; high ⇒ HIGH.
   - `risk_flag`: NONE for low risk; for a medium ROAD border lane use `MEDIUM_BORDER_RISK`
     (driven by the record's risk_notes/border language). High customs ROAD ⇒ high customs flag.
   - In the richer template: `customs_border_risk` mirrors the road/route risk (LOW/MEDIUM/HIGH);
     `source_is_stale = true` ONLY when the freight record `status == "stale"`;
     `validity_status` = VALID when `valid_until >= quote_date` and not stale, else EXPIRED/STALE.
4. Freight may be SHOWN even if stale/expired: when the template/prompt asks to flag a stale road
   quote, include all three AIR/SEA/ROAD options and mark the road one stale/expired/high-risk and
   set `road_quote_invalid_or_stale = true`. (Distractor `FR-DIS-*` records are always dropped.)

### recommended_mode — CONFIRMED RULE
`recommended_mode` = the **cheapest VALID option by `grand_total_usd`**, where "valid" means
NOT stale and NOT expired on the quote date. Exclude any stale/expired option from the choice.
It is COST-driven, not lowest-risk: if SEA is valid and cheaper than AIR, recommend SEA even
when SEA is MEDIUM risk and AIR is LOW.

### Validity / reconfirmation / payment (Family A)
- `freight_reconfirmation_required` = true (policy `POL-FREIGHT-RECONFIRM`: rates reconfirmed at
  order; valid only through each freight `valid_until`).
- `all_freight_options_valid_on_quote_date` = true only if EVERY shown real option has
  `valid_until >= quote_date`.
- Catalog pricing validity = 30 days (`POL-QUOTE-VALIDITY`) ⇒ `offer_validity_days = 30`.
- For indicative/no-destination RFQs: `quote_basis = EXW_ONLY`, `freight_excluded = true`
  (policy `POL-INDICATIVE-EXW`). Do not attach freight.
- WHO documentation: for IEHK / emergency-health-kit module quotes, `who_documentation_required = true`.

### Payment terms by account type (Family A & B)
- New NGO / no approved credit (`is_recurring=false`, segment `new_ngo`,
  payment_profile `NEW_CLIENT_REVIEW`) ⇒ `PREPAY_100` (`POL-NEW-CLIENT-PAYMENT`).
- Recurring NGO / recurring commercial with PO terms (payment_profile `NET_30_AFTER_PO`)
  ⇒ `NET_30_AFTER_PO` (`POL-RECURRING-NGO-PAYMENT`), unless restricted grant terms override.
- Prefer the customer's own `payment_profile` value when present; it matches the policy code.
- Where a `customer_policy` field is requested, the policy id (e.g. `POL-RECURRING-NGO-PAYMENT`)
  is the clean choice.

---

## Engagement / milestone reconciliation (Family B)

Gather: `GET /api/opportunities/<OPP-...>`, `GET /api/customers/<CUST-...>`,
`GET /api/invoices?opportunity_id=<OPP-...>`, `GET /api/payments?opportunity_id=<OPP-...>`,
revenue-journals (fetch all, match on `opportunity_id`/`phase_id`), and the named event/voucher.
Treat the prompt's "as-of"/current business date as `as_of_date`.

### Header / totals
- `stage`: `closed_won` ⇒ `WON` (else OPEN/LOST).
- `won_amount` from opportunity `won_amount_usd` (2 decimals).
- `phase_total_amount` = sum of phase `amount_usd`. `opportunity_matches_*` = (won == phase total).
- `total_paid_amount` = sum of `paid_amount_usd` across invoices (or posted payments).
- `outstanding_balance` = sum of invoice `outstanding_amount_usd` (= opportunity
  `outstanding_amount_usd`).
- `primary_contact` = the opportunity `contact` / matching customer contact named in the prompt.
- `customer_name` from the customer record.

### Milestones (one per phase, ascending)
- `milestone_id`: if the template enum is `MS1 | MS2 | MS3`, use POSITIONAL ids in phase order
  (MS1, MS2, MS3) — NOT the raw `MER-P1` phase ids. If the template instead says "stable phase or
  invoice id", use the phase id (`HEL-P1`) consistently.
- `amount` / `invoice_total` = phase/invoice `amount_usd`.
- `invoice_state`: paid invoice ⇒ `PAID`; unpaid invoice ⇒ `OPEN` (void ⇒ VOID).
- `payment_state`: `PAID` if fully paid, `UNPAID` if nothing paid, `PARTIAL` if some paid.
- `paid_amount` / `amount_paid` = invoice `paid_amount_usd`; `amount_unpaid` = `outstanding_amount_usd`.
- **due_date — CONFIRMED HARD RULE:** a PAID milestone's `due_date` MUST be `null`. Only an
  UNPAID/OPEN milestone carries its invoice `due_date`. (Setting a paid milestone's due_date to
  the invoice date is incorrect.)
- `recognition_status` / `revenue_recognition_status`:
  - `RECOGNIZED` — milestone paid AND a posted revenue-journal exists for it.
  - `MISSING_REVENUE_JOURNAL` (a.k.a. `REQUIRED_MISSING`) — milestone PAID but NO journal exists.
  - `NOT_REQUIRED_UNPAID` — milestone unpaid (recognition not yet required).

### Revenue-recognition summary
- Recognize revenue ONLY for PAID milestones. A paid-but-missing-journal milestone is the trigger
  for a RECORD_REVENUE action.
- `recognition_status` (summary): `COMPLETE_FOR_PAID_MILESTONES` if every paid milestone has a
  journal; `MISSING_FOR_PAID_MILESTONES` if any paid milestone lacks one; `NOT_REQUIRED` if none paid.
- `recognized_milestones` = paid milestones WITH a journal; `recognized_amount` = sum of their amounts.
- `missing_required_milestones` = paid milestones WITHOUT a journal.

### Accounting action routing — CONFIRMED
- If a paid milestone is missing its journal (e.g. MS2): `primary_accounting_action` /
  `accounting_action.action` = `RECORD_REVENUE_MS2`, `milestone_id` = that milestone,
  `amount` = its amount, `debit_account` = `DEFERRED_REVENUE`,
  `credit_account` = `IMPLEMENTATION_SERVICES_REVENUE`, `owner_queue` = `ACCOUNTING`.
  (debit/credit mirror the revenue-journal record's accounts.)
- If all paid milestones already recognized ⇒ `VERIFY_REVENUE_ONLY`; if nothing to do ⇒
  `NO_ACCOUNTING_ACTION` with milestone `NONE` and accounts `NONE`.

### Collection action routing — CONFIRMED
- Pick the unpaid milestone. Compare its due_date to `as_of_date`:
  - due_date in the FUTURE (not yet due) ⇒ `collection_action` = `MONITOR_UNPAID_NOT_DUE`,
    `owner_queue` = `ACCOUNT_MANAGEMENT` (NOT `COLLECTIONS`). Using COLLECTIONS here is incorrect
    while the milestone is not yet due.
  - due_date PAST (overdue) ⇒ `SEND_COLLECTION_NOTICE`, `owner_queue` = `COLLECTIONS`.
  - no unpaid milestone ⇒ `NO_COLLECTION_ACTION`, milestone `NONE`.
- `collection_task`: milestone_id, amount = outstanding, due_date = the unpaid invoice due_date
  (NOT null — it is unpaid), contact_name from the account contact.
- Accounting vs collection are SEPARATE routings: revenue gaps go to ACCOUNTING; unpaid balances
  go to ACCOUNT_MANAGEMENT/COLLECTIONS. Do not conflate them.

### Event / voucher actions
- `event_status` from event `status` mapped to the enum (`scheduled`⇒SCHEDULED, etc.).
- voucher: `voucher_status` from voucher `status` (`active`⇒ACTIVE); `discount_amount` =
  voucher `discount_percent`; `max_uses` = voucher `max_redemptions`.
- For a scheduled briefing/celebration: `invite_action` = `SEND_BRIEFING_INVITE` (or
  `SEND_EVENT_INVITATION` per template). `invite_task.owner_queue` = `ACCOUNT_MANAGEMENT`
  (matches event `follow_up_owner` "Account Management"); contact_name & customer_id from records.
- For simpler templates, follow_up_tasks is a list: one COLLECTION task for the unpaid milestone
  (next_action `COLLECT_UNPAID_MILESTONE`, with milestone_id/amount_due set, event/voucher null)
  and one EVENT_INVITATION task (next_action `SEND_EVENT_INVITATION`, with event_id/voucher_code
  set, milestone_id/amount_due null). The COLLECTION task due_date = the unpaid invoice due_date;
  the EVENT task due_date = the event_date.

---

## Common misjudgments / exclusion rules
- Do NOT include `FR-DIS-*` / "Distractor route" / wrong-shipment-size freight records.
- Do NOT price from `prior_unit_price_usd`; always re-tier from the product on the confirmed qty.
- Do NOT expand modules into components; quote module-level only and ignore component distractors.
- Do NOT give a PAID milestone a due_date — it must be `null`.
- Do NOT recommend the lowest-RISK mode; recommend the cheapest VALID (non-stale) mode.
- Do NOT route a not-yet-due unpaid balance to COLLECTIONS — that's ACCOUNT_MANAGEMENT/MONITOR.
- Do NOT recognize revenue for unpaid milestones; only paid ones (and flag paid-but-missing-journal).
- Do NOT filter revenue-journals by customer_id (field absent) — use opportunity_id.
- Do NOT invent enum values — copy the exact tokens from the template; map raw API strings to them.

## Final reminder
Return ONLY the JSON object that matches the provided `answer_template.json` — correct keys,
controlled enum values, 2-decimal money, ISO dates, and nulls only where required. No markdown.
