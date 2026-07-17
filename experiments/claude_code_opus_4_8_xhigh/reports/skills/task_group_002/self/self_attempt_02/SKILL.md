# SKILL: MedBridge Sales Ops — Quote Decision Packages & Engagement Reconciliation

## What this is / when it applies
A future solver gets ONE new task in the MedBridge Sales Ops (CRM / B2B medical-supply) domain,
plus a read-only HTTP API and an `answer_template.json`. Tasks come in a few fixed families:

1. **EXW + freight decision package** — a revised catalog quote (`Q-...`) for a single product:
   pick the price tier by quantity, list the 3 current freight options, compute EXW + freight
   grand totals, flag route risk / staleness, recommend a mode, state payment + freight controls.
2. **Module / RFQ EXW-only quote** — an indicative RFQ (`RFQ-...`) with multiple module line items,
   EXW only, freight excluded (no destination).
3. **CRM milestone / engagement reconciliation** — an opportunity (`OPP-...`): reconcile won amount
   vs phase/milestone totals, invoice + payment state, outstanding balance, revenue-recognition
   coverage, the linked event + voucher, and route follow-up (collection / accounting / invite) tasks.

Identify the family from the answer_template top-level keys:
- `quote_summary` + `freight_options` + `policy_flags` → Family 1 (simple freight package).
- `pricing` + `transport_decisions` + `client_warnings` → Family 1 variant (adds validity/staleness fields).
- `quote_header` + `line_items` + `quote_controls` → Family 2 (module EXW-only).
- `account_status`/`engagement_reconciliation` + `milestones` + follow-up/action blocks → Family 3.

**ALWAYS return ONLY JSON matching the provided answer_template exactly — no markdown, no prose.**
Fill every field the template declares; keep the template's key order/structure.

---

## The remote API
- Base URL: given by the runner (e.g. `API_BASE_URL`, `BASE_URL`, or `http://127.0.0.1:<PORT>`).
  During offline reasoning the shared instance was `<remote-env-url>`. Use whatever
  base URL the prompt/runner provides.
- Read-only JSON over HTTP (`curl` or python urllib). No local data files exist.
- `GET /api` lists collections: customers, events, freight-quotes, invoices, opportunities,
  payments, policies, products, quotes, revenue-journals, rfqs, vouchers.

### Lookups by ID (preferred — IDs come straight from the prompt)
- `GET /api/quotes/<quote_id>`, `/api/rfqs/<rfq_id>`, `/api/products/<code>`,
  `/api/customers/<customer_id>`, `/api/opportunities/<opportunity_id>`.

### List + filter (`?field=value`, case-insensitive, server flattens nested keys)
- `GET /api/freight-quotes?quote_id=<quote_id>` → all freight rows for a quote.
- `GET /api/invoices?opportunity_id=<opp_id>` and `?customer_id=<cust_id>`.
- `GET /api/payments?opportunity_id=<opp_id>`.
- **`GET /api/revenue-journals?opportunity_id=<opp_id>`** — revenue-journal records have
  NO `customer_id` field, so filtering them by `customer_id` returns 0. Filter by `opportunity_id`
  (or fetch all and match on `opportunity_id`/`phase_id`/`invoice_id`). This is a real pitfall.
- `GET /api/events?id=<event_id>` (or `?opportunity_id=...`), `GET /api/vouchers?code=<code>`.
- `GET /api/search?q=<text>` — full-text across all collections; great for resolving a customer
  by name, or pulling every related record (opp + invoices + payments + journal + event + voucher)
  for one account in a single call.
- `GET /api/policies` — 8 business-rule records; read once and apply (see Business Rules).

### Resolving IDs from the prompt
Prompts hand you the IDs directly (quote_id, rfq_id, opportunity_id, customer_id, event_id,
voucher code). Use those. If only a name is given, use `/api/search?q=<name>`.
**Use API field values, not the prompt's prose** when they disagree — e.g. the customer `name`
from `/api/customers/<id>` overrides any name the email uses (a prompt called Helios
"Health Alliance" while the record name is "Helios Health Initiative").

---

## Output conventions (all families)
- Money: numbers with 2 decimals, USD. EXW/grand/amounts as numeric (e.g. `42480.00`).
- Dates: ISO `YYYY-MM-DD`. Use the record's own dates (valid_until, due_date, event_date, etc.).
- `transit_days`: a STRING — use the freight row's `transit_days_text` (e.g. `"4-6 days"`).
- Enums: use EXACTLY the controlled values the template lists (often UPPER_SNAKE_CASE).
  Map raw API strings to the template enum: API `stage:"closed_won"` → `WON`; `mode:"air"` → `AIR`;
  `route_risk:"medium"` → `MEDIUM`; invoice `status:"paid"/"unpaid"` → `PAID/UNPAID`/`OPEN`.
- Null: only where the template explicitly allows it (e.g. `milestone_id`/`amount_due`/`event_id`
  null on an action that doesn't apply; `due_date` null when not applicable).
- Totals MUST reconcile: line totals sum to grand_total; EXW + freight = grand_total;
  phase amounts sum to won_amount when they match; paid + unpaid = invoice amount.

---

## FAMILY 1 — EXW + freight decision package (`quote_summary`/`pricing` templates)

SOP:
1. `GET /api/quotes/<quote_id>` → customer_id, primary_product_code, confirmed_quantity, quote_date,
   destination. (Prior unit price / prior quantity in the quote are HISTORY — ignore them; the
   catalog tier overrides the prior price.)
2. `GET /api/products/<code>` → walk `price_tiers`; pick the tier where
   `min_qty <= confirmed_quantity <= max_qty` (a `null` `max_qty` means "no upper bound").
   Take that tier's `unit_price_usd`, `lead_time_days`, and the product's `shelf_life_months`.
3. **EXW total = unit_price_usd × confirmed_quantity** (2 decimals).
4. `GET /api/freight-quotes?quote_id=<quote_id>` → there are usually 5 rows but only 3 are real
   (one AIR, one SEA, one ROAD). **EXCLUDE distractors**: any row whose `id` contains `FR-DIS-`,
   whose `destination` is `"Distractor route"`, or that is the wrong shipment size / a benchmark.
   Keep exactly the one canonical AIR / SEA / ROAD row (ids like `FR-WC-AIR`, `FR-LD-SEA`, ...).
5. For each kept option:
   - `freight_cost_usd` = row `cost_usd`; `transit_days` = `transit_days_text`;
     `valid_until` = row `valid_until`; `mode` = uppercased row `mode`.
   - **grand_total_usd = EXW total + freight_cost_usd**.
   - `risk_level` = uppercased `route_risk` (LOW/MEDIUM/HIGH).
   - `risk_flag` (simple template): `NONE` for low/clean; for road border risk use the value the
     template seeds, e.g. `MEDIUM_BORDER_RISK` when risk_notes mention border risk.
   - Validity-rich template (Family 1 variant): set `validity_status` (`valid` vs `expired`/`stale`),
     `source_is_stale` = (`status=="stale"` OR `valid_until` < quote_date), and
     `customs_border_risk` from route_risk / risk_notes.
6. **Stale / expired road**: if the ROAD row has `status:"stale"` or `valid_until` < quote_date,
   set `road_quote_invalid_or_stale = true` and write a `freight_warning` saying the road quote is
   expired/stale and must be re-sourced before use.
7. `all_freight_options_valid_on_quote_date`: true only if EVERY kept option's `valid_until`
   >= quote_date.
8. `freight_reconfirmation_required`: **true** (policy `POL-FREIGHT-RECONFIRM`: rates need
   reconfirmation at final order; valid only through valid_until).
9. **recommended_mode**: from the VALID options only (drop any stale/expired/high-risk-invalid road).
   Prefer the lowest `route_risk`; break ties by lowest grand_total and fitness for the goods
   (cold-chain support, urgency/transit for emergency stock). Concretely: if road is stale, choose
   between AIR (fast, low-risk, cold-chain-capable) and SEA (cheapest but long transit / shelf-life
   review) — pick AIR when cold-chain reliability or speed matters, SEA when cost dominates and
   transit is acceptable. State a single mode (AIR/SEA/ROAD).
10. `payment_terms` / `customer_policy`: from customer + policies (see Business Rules).
11. `quote_basis` = `EXW`.

Money sanity (worked examples that match the data):
EXW = tier_price × qty; grand_total = EXW + each freight cost. Always re-add; never carry the
prior_unit_price from the quote line.

---

## FAMILY 2 — Module / RFQ EXW-only quote (`quote_header`/`line_items`/`quote_controls`)

SOP:
1. `GET /api/rfqs/<rfq_id>` → customer_id, quote_date, `requested_modules` (each `product_code` +
   `quantity`), destination (usually "pending"/none).
2. **Keep MODULE-level lines only.** Do NOT expand into component SKUs even if products/RFQ show a
   `components` list or a `component_composition_distractors` field — those are medical-review noise
   (policy `POL-MODULE-GRANULARITY`: quote at module line level unless the customer asks for
   component pricing).
3. For each requested module: `GET /api/products/<code>` → `article_number`, the single price tier's
   `unit_price` (`unit_price_usd`), `lead_time_days`, `shelf_life_months`.
   - `line_total = unit_price × quantity`.
4. `grand_total` = sum of all `line_total`.
5. `quote_basis` = `EXW_ONLY`; `freight_excluded` = true (no destination → policy `POL-INDICATIVE-EXW`
   `EXW_ONLY_EXCLUDE_FREIGHT`).
6. `offer_validity_days` = 30 (policy `POL-QUOTE-VALIDITY` — catalog pricing valid 30 days).
7. `payment_terms`: new NGO / new-client (segment `new_ngo`, `is_recurring:false`,
   payment_profile `NEW_CLIENT_REVIEW`) → `PREPAY_100` (policy `POL-NEW-CLIENT-PAYMENT`).
8. `who_documentation_required` = true for emergency/NGO health-kit modules (keep template default
   unless data clearly says otherwise).
9. `currency` = `USD`.

---

## FAMILY 3 — CRM milestone / engagement reconciliation

SOP:
1. `GET /api/opportunities/<opp_id>` → stage, won_amount_usd, phases[] (each `phase_id`, `amount_usd`,
   `invoice_id`, `completion_date`, name), contact, outstanding_amount_usd.
   `GET /api/customers/<customer_id>` → customer name (authoritative).
2. `stage`: `closed_won` → `WON` (map to template enum WON/OPEN/LOST).
3. `won_amount` = won_amount_usd. `phase_total` = sum of phase `amount_usd`.
   `opportunity_matches_(milestones|phase_total)` = (won_amount == phase_total).
4. `GET /api/invoices?opportunity_id=<opp>` — per phase: `amount_usd`, `paid_amount_usd`,
   `outstanding_amount_usd`, `due_date`, `status`. Map invoice `status`: paid→`PAID`,
   unpaid→`UNPAID`/`OPEN` (use the template's enum spelling — Family-3a uses PAID/PARTIAL/UNPAID,
   Family-3b invoice_state uses PAID/OPEN/VOID/UNKNOWN).
5. `GET /api/payments?opportunity_id=<opp>` — confirm posted payments per invoice. payment_state:
   fully paid→`PAID`, part→`PARTIAL`, none→`UNPAID`.
6. `GET /api/revenue-journals?opportunity_id=<opp>` (NOT by customer_id). A milestone is
   **RECOGNIZED** iff a posted revenue-journal exists for its phase/invoice. recognition per
   milestone:
   - paid milestone WITH a journal → `RECOGNIZED`.
   - **paid milestone WITHOUT a journal → `MISSING_REVENUE_JOURNAL` / `REQUIRED_MISSING`** (this is
     the actionable gap — drives an accounting action).
   - unpaid milestone → `NOT_REQUIRED_UNPAID` (do NOT recognize revenue on unpaid milestones;
     policy `POL-REVREC`: recognize only completed & paid milestones).
7. `outstanding_balance` / `outstanding_amount` = sum of unpaid invoice `outstanding_amount_usd`
   (equals opportunity `outstanding_amount_usd`). `total_paid_amount` = sum of paid amounts.
8. Milestone IDs: use the template's convention. If the template enumerates `MS1|MS2|MS3`, map phases
   in ascending phase order (P1→MS1, P2→MS2, P3→MS3). If it asks for a "stable phase/invoice id",
   use the `phase_id` (e.g. `HEL-P1`). Order ascending.
9. `due_date`: use the invoice `due_date`. (For a recognized/paid milestone some templates still
   want the invoice due_date; only null it where the template explicitly allows null.)
10. Revenue-recognition summary block:
    - `recognized_milestones` = paid milestones that have a journal; `recognized_amount` = their sum.
    - `missing_required_milestones` = paid milestones lacking a journal.
    - status: all paid have journals → `COMPLETE_FOR_PAID_MILESTONES`; some paid lack journals →
      `MISSING_FOR_PAID_MILESTONES`; no paid milestones → `NOT_REQUIRED` (use template's enum names).
11. Event + voucher: `GET /api/events?id=<event_id>` and `GET /api/vouchers?code=<code>` (or pull from
    `/api/search`). Event `status` map: `confirmed`/`scheduled` → SCHEDULED (use template enum),
    `event_date`, `voucher_code`. Voucher: `status` (active→ACTIVE), `max_uses` = `max_redemptions`.
    `voucher_discount`/`discount_amount` = the voucher's `discount_percent` value (vouchers carry a
    percent, not a dollar amount; put that numeric value in the discount field).
12. **Follow-up / action routing**:
    - **Accounting action**: if a PAID milestone is missing its revenue journal → record it.
      action `RECORD_REVENUE_<MS>` (e.g. `RECORD_REVENUE_MS2`), that milestone, its amount,
      `debit_account = DEFERRED_REVENUE`, `credit_account = IMPLEMENTATION_SERVICES_REVENUE`
      (matches the journal pattern: debit Deferred Revenue, credit Implementation Services Revenue),
      `owner_queue = ACCOUNTING`. If all paid milestones already recognized → `VERIFY_REVENUE_ONLY`
      / `NO_ACCOUNTING_ACTION` with `NONE` accounts and `0.00`.
    - **Collection action**: for an UNPAID milestone, compare its invoice `due_date` to the as-of /
      current business date. Not yet due → `MONITOR_UNPAID_NOT_DUE`, owner `ACCOUNT_MANAGEMENT`.
      Overdue → `SEND_COLLECTION_NOTICE`, owner `COLLECTIONS`. Carry milestone id, amount_due (the
      outstanding amount), due_date, contact name. If nothing unpaid → `NO_COLLECTION_ACTION`/`NONE`.
    - **Event invite action**: a scheduled/confirmed event that still needs invitations →
      `SEND_BRIEFING_INVITE` / `SEND_EVENT_INVITATION`, with event_id, voucher_code,
      `owner_queue` from the event's `follow_up_owner` (e.g. "Account Management" → ACCOUNT_MANAGEMENT),
      contact, customer_id. If already sent → `VERIFY_INVITE_SENT`/`NO_INVITE_ACTION`.
    - The simpler Family-3a `follow_up_tasks[]` array: emit one COLLECTION task per unpaid milestone
      (`next_action: COLLECT_UNPAID_MILESTONE`, due_date = invoice due_date, amount_due = outstanding,
      milestone_id set, event_id/voucher_code null) and one EVENT_INVITATION task
      (`next_action: SEND_EVENT_INVITATION`, event_id + voucher_code set, milestone_id/amount_due null,
      due_date = event_date). Contact = the account contact named in the prompt / opportunity.

---

## Business rules reference (from `/api/policies`)
- **Tier selection** (`min_qty <= qty <= max_qty`, null max = unbounded); tier price overrides any
  prior/historical unit price on the quote line.
- **Freight cost & grand total**: grand_total = EXW(unit×qty) + freight cost, per option.
- **Risk level vs risk flag**: risk_level mirrors `route_risk` (LOW/MEDIUM/HIGH); risk_flag/
  customs_border_risk encodes the specific concern (NONE, MEDIUM_BORDER_RISK, etc.) from risk_notes.
- **Feasibility vs risk**: a stale/expired freight row is INVALID (exclude from recommendation and
  flag it) — separate from merely "risky but valid". `source_is_stale` = status stale OR
  valid_until < quote_date.
- **Validity / reconfirmation**: catalog pricing valid 30 days (`QUOTE_VALID_30_DAYS`); freight valid
  only through its `valid_until`; freight always needs reconfirmation at order
  (`freight_reconfirmation_required = true`).
- **Payment terms by account type**:
  - New NGO / new-client (no approved credit, `NEW_CLIENT_REVIEW`) → `PREPAY_100`.
  - Recurring NGO → `NET_30_AFTER_PO` (unless restricted grant terms say otherwise).
  - Recurring Commercial / framework accounts → `NET_30_AFTER_PO`.
  Prefer the customer's own `payment_profile` when present and consistent with policy.
- **Module granularity**: keep module lines; never expand to component SKUs (`MODULE_LINES`).
- **Indicative EXW**: no destination → EXW only, freight excluded (`EXW_ONLY_EXCLUDE_FREIGHT`).
- **Revenue recognition**: recognize (debit Deferred Revenue → credit Implementation Services Revenue)
  ONLY for completed & paid milestones; unpaid future milestones stay outstanding and drive
  collection tasks when due/overdue (`RECOGNIZE_PAID_COMPLETE_MILESTONES`).

---

## Common misjudgments / exclusion rules
- Don't include `FR-DIS-*` / "Distractor route" / wrong-shipment-size freight rows. Keep exactly one
  AIR, one SEA, one ROAD canonical row.
- Don't use the quote line's `prior_unit_price_usd` / `prior_quote_quantity` — recompute from the
  catalog tier.
- Don't filter `revenue-journals` by `customer_id` (no such field) — filter by `opportunity_id`.
- Don't expand modules into components, even when `components` / `component_composition_distractors`
  are present.
- Don't recognize revenue on unpaid milestones; do flag a PAID milestone that lacks a journal.
- Don't escalate a not-yet-due unpaid milestone to COLLECTIONS — that's MONITOR (ACCOUNT_MANAGEMENT)
  until the due_date passes.
- Don't include freight when there's no destination (Family 2).
- Use the customer `name` and other field values from the API, not the prompt's wording, when they
  differ.
- Map every raw value to the exact template enum spelling and casing.

---

## Final reminder
Output ONLY the JSON object matching the provided `answer_template.json` — same keys, same nesting,
controlled enum values, 2-decimal money, ISO dates, nulls only where allowed. No markdown, no
explanation.
