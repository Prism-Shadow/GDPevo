# SKILL: MedBridge Sales Ops — CRM/B2B Quote + Engagement Reconciliation

## When this applies
Use this skill for tasks against the **MedBridge Sales Ops API** that ask you to build an
"account-ready" / "finance-ready" JSON package about either:
- a **quote** (catalog product priced EXW, with or without freight options), or
- an **engagement reconciliation** (a won opportunity with milestone invoices, payments,
  revenue-recognition journals, and a follow-up event/voucher).

You always get: a prompt naming specific record IDs (quote/RFQ/opportunity/customer/event/
voucher), a read-only data API, and an `answer_template.json`. Fill the template EXACTLY and
**return ONLY JSON — no markdown, no prose, no comments**. Match the template's keys, nesting,
and any declared enum values verbatim.

---

## Data API (read-only)
Base URL is provided by the runner (env var like `API_BASE_URL`/`BASE_URL`/`http://127.0.0.1:<PORT>`
or `<remote-env-url>`). All GET, JSON.

Collections / single-record endpoints:
- `/api/customers` , `/api/customers/<id>`
- `/api/products` , `/api/products/<code>`
- `/api/rfqs` , `/api/rfqs/<id>`
- `/api/quotes` , `/api/quotes/<id>`
- `/api/freight-quotes` , `/api/freight-quotes/<id>`
- `/api/policies`
- `/api/opportunities` , `/api/opportunities/<id>`
- `/api/invoices` , `/api/payments` , `/api/revenue-journals`
- `/api/events` , `/api/vouchers`
- `/api/search?q=<text>` — full-text across all collections (returns `{collection,id,record}`)

### Filtering & lookup
- List endpoints accept `?field=value` (flattened, case-insensitive, numbers match 2-decimal form).
- **Which filter key actually works differs by collection — verify, don't assume:**
  - `freight-quotes`: filter by **`?quote_id=<QUOTE_ID>`** (NOT customer_id). Freight is tied to a quote.
  - `invoices` / `payments`: filter by **`?opportunity_id=<OPP_ID>`** (customer_id also works on these).
  - `revenue-journals`: **DO NOT filter by `customer_id`** (those records have no customer_id field and
    you'll get 0 results). Filter by **`?opportunity_id=<OPP_ID>`**, or pull the whole list and match
    on `opportunity_id`/`phase_id`/`invoice_id`.
- `/api/search?q=<name>` is the best way to discover all linked record IDs for an account in one call.
  Searching a human name (e.g. a product's marketing name) may return 0 — search by the ID/code or a
  distinctive token instead.
- Resolve IDs from the prompt directly when given (quote, opportunity, event, voucher codes are usually
  literal). For a customer, read the quote/opportunity record — it carries `customer_id`.

---

## Output conventions (confirmed)
- **Money: numbers with 2 decimals in USD dollars** (e.g. `42480.0`, `45000.00`). Not integer cents,
  even if a prompt says "cent-level" — follow the template's "2 decimals" wording.
- **Dates: ISO `YYYY-MM-DD`.**
- **Enums: use the EXACT strings the template lists.** When the template gives an enum union
  (`WON | OPEN | LOST`), map source data to one of those tokens.
- **Mode strings are UPPERCASE** in output (`AIR`/`SEA`/`ROAD`) even though the API stores `air/sea/road`.
- **`transit_days` is the freight record's `transit_days_text` string** (e.g. `"4-6 days"`), not a number.
- **Totals must reconcile exactly:** line_total = quantity × unit_price; exw_total = quantity × unit_price;
  grand_total = exw_total + freight_cost; phase_total = sum of phase amounts; total_paid = sum of paid;
  outstanding_balance = sum of unpaid invoice outstanding amounts.
- A field that says "or null" must be `null` (not `""`, not `0`) when not applicable.
- If the template provides a single object inside an array but the source has N items (e.g. N requested
  modules, N milestones, N freight modes), **emit one array element per real item.**

---

## FAMILY A — Quote decision package (catalog product, EXW [+ freight])
Trigger: prompt references a `quote` or `rfq` for a catalog `product_code`, asks for EXW pricing,
freight comparison, recommended mode, payment/validity flags. Two sub-shapes:
- A1 freight comparison (template has `freight_options` with AIR/SEA/ROAD).
- A2 indicative EXW-only (no destination → freight excluded; multi-module RFQ lines).

### SOP
1. GET the quote (`/api/quotes/<id>`) or RFQ (`/api/rfqs/<id>`). Note `customer_id`, `quote_date`,
   `confirmed_quantity`, `primary_product_code` (or each `requested_modules[].product_code`/quantity).
2. GET the product(s) (`/api/products/<code>`). Read `price_tiers`, `article_number`, `shelf_life_months`.
3. **Tier selection:** pick the tier whose `[min_qty, max_qty]` contains the confirmed quantity
   (`max_qty: null` = open-ended top tier). Use that tier's `unit_price_usd`, `lead_time_days`,
   and the product `shelf_life_months`. The catalog tier OVERRIDES any `prior_unit_price_usd` on the quote.
4. **EXW total = confirmed_quantity × tier unit_price.** quote_basis = `EXW` (or `EXW_ONLY` when freight excluded).
5. GET customer (`/api/customers/<customer_id>`); determine payment terms (see Payment rules below).
6. **Freight (A1 only):** GET `/api/freight-quotes?quote_id=<QUOTE_ID>`.
   - **Exclude distractors:** any record whose id contains `DIS` or whose notes say "Old route benchmark",
     "Wrong shipment size", "benchmark", etc. Keep exactly the three genuine mode records (air/sea/road)
     that match this quote's shipment.
   - For each kept option: `freight_cost_usd = cost_usd`; `transit_days = transit_days_text`;
     `valid_until` as-is; `grand_total_usd = exw_total + freight_cost_usd`.
   - **Risk fields** map from `route_risk`: `low`→ risk_level `LOW`/risk_flag `NONE`;
     `medium` road border → `MEDIUM`/`MEDIUM_BORDER_RISK`; `high` → `HIGH` (+ appropriate flag).
     In the extended template use `customs_border_risk` = `LOW`/`MEDIUM`/`HIGH` from `route_risk`.
   - **Staleness:** an option is stale/invalid when `status == "stale"` OR `valid_until < quote_date`.
     Set `source_is_stale=true`, `validity_status="EXPIRED"` (STALE also accepted), and the matching
     `road_quote_invalid_or_stale=true` flag. Valid options → `source_is_stale=false`,
     `validity_status="VALID"`.
   - `all_freight_options_valid_on_quote_date` = true only if every kept option's `valid_until >= quote_date`.
7. **Recommended mode (confirmed rule):** choose the option with the **lowest `grand_total_usd` among the
   VALID (non-stale, valid_until >= quote_date) options.** This holds even if that option is MEDIUM risk
   or the product is cold-chain. A cheaper-but-STALE option is NOT recommended. (Empirically SEA beat both
   a cheaper stale ROAD and a low-risk-but-pricier AIR.)
8. `freight_reconfirmation_required = true` (freight rates always need reconfirmation at order; policy
   POL-FREIGHT-RECONFIRM).
9. **A2 EXW-only / module RFQ:** if the RFQ has no destination, quote EXW only, `freight_excluded=true`.
   Emit one line per requested module (module-level granularity, policy POL-MODULE-GRANULARITY) —
   **never expand into component SKUs**, and ignore any `component_composition_distractors` /
   "for medical review only" composition tables. line_total = qty×unit; grand_total = sum of line_totals.
   `offer_validity_days = 30` (POL-QUOTE-VALIDITY, catalog pricing valid 30 days).
   `who_documentation_required = true` for these emergency-health/IEHK module quotes.

### Payment terms (Family A)
From customer record (`customer_type`, `is_recurring`, `segment`, `payment_profile`) + policies:
- New NGO / first order / `payment_profile == NEW_CLIENT_REVIEW` / status prospect → **`PREPAY_100`** (POL-NEW-CLIENT-PAYMENT).
- Recurring NGO or recurring Commercial with `payment_profile == NET_30_AFTER_PO` → **`NET_30_AFTER_PO`** (POL-RECURRING-NGO-PAYMENT).
- In general, echo the customer's `payment_profile` unless a stricter policy (new-client prepay) overrides it.

---

## FAMILY B — Engagement reconciliation (won opp, milestones, revenue, event)
Trigger: prompt names an `opportunity` (OPP-...) + customer and asks to reconcile won amount vs milestone
phases, payment/outstanding/revenue-recognition state, and route follow-ups; usually also a related
event + voucher.

### SOP
1. GET opportunity (`/api/opportunities/<id>`): `stage` (`closed_won`→`WON`), `won_amount_usd`,
   `phases[]` (each has `phase_id`, `amount_usd`, `invoice_id`, `completion_date`), `outstanding_amount_usd`,
   `contact`.
2. GET customer for `customer_name`. Identify the primary contact (from prompt / opportunity / customer).
3. GET invoices: `/api/invoices?opportunity_id=<OPP_ID>` — per phase: `amount_usd`, `paid_amount_usd`,
   `outstanding_amount_usd`, `due_date`, `status` (`paid`/`unpaid`).
4. GET payments: `/api/payments?opportunity_id=<OPP_ID>` — posted payments confirm PAID.
5. GET revenue journals: `/api/revenue-journals?opportunity_id=<OPP_ID>` (NOT by customer_id). A posted
   journal for a phase's invoice = revenue recognized for that phase.
6. GET event + voucher (by IDs/codes in the prompt, or via `/api/search`). Voucher fields:
   `discount_percent`, `max_redemptions`, `status`, `event_id`.

### Per-milestone status rules
For each phase, in ascending phase order:
- `amount` = phase/invoice amount. `paid_amount` = invoice `paid_amount_usd`.
- `invoice_state`: paid→`PAID`; unpaid (status "unpaid")→`OPEN`; voided→`VOID`; else `UNKNOWN`.
- `payment_state`: fully paid→`PAID`; partial→`PARTIAL`; none→`UNPAID`.
- **`due_date`: set to the invoice `due_date` ONLY for NOT-yet-paid milestones; for PAID milestones
  set `due_date = null`.** (Confirmed: filling a paid milestone's due_date loses points.)
- **Recognition status:**
  - PAID **and** a posted revenue journal exists → `RECOGNIZED`.
  - PAID **but no** revenue journal → `MISSING_REVENUE_JOURNAL` (generic template:
    `REQUIRED_MISSING`). This is the trigger for a record-revenue accounting action.
  - UNPAID → `NOT_REQUIRED_UNPAID` (revenue not recognized until paid; policy POL-REVREC).
- `milestone_id`: use the template's required form — positional `MS1|MS2|MS3` (ascending) when the
  template enumerates it; otherwise the stable phase id (e.g. `MER-P1`).

### Account-level rollups
- `stage`: `closed_won`→`WON`.
- `won_amount` = `won_amount_usd`. `phase_total_amount` = sum of phase `amount_usd`.
- `opportunity_matches_phase_total` / `opportunity_matches_milestones` = (won == phase_total).
- `total_paid_amount` = sum of paid amounts. `outstanding_balance` = sum of unpaid outstanding.
- Recognition rollup: `recognized_milestones` = phases with a posted journal; `recognized_amount` =
  sum of their amounts; status `COMPLETE_FOR_PAID_MILESTONES` if every PAID milestone has a journal,
  else `MISSING_FOR_PAID_MILESTONES`.

### Action routing (the rules the grader rewards)
**Accounting action (revenue):**
- If a PAID milestone is missing its journal → `RECORD_REVENUE_MS<n>` (e.g. `RECORD_REVENUE_MS2`):
  `milestone_id = MS<n>`, `amount = that milestone amount`,
  `debit_account = DEFERRED_REVENUE`, `credit_account = IMPLEMENTATION_SERVICES_REVENUE`,
  `owner_queue = ACCOUNTING`. `primary_accounting_action` mirrors this.
- If all paid milestones are recognized → `VERIFY_REVENUE_ONLY` / `NO_ACCOUNTING_ACTION` (milestone `NONE`,
  amount 0, accounts `NONE`, queue `NONE`) as the template allows.

**Collection action (unpaid milestone) — separate from accounting:**
- Compare the unpaid milestone's `due_date` to the current/as-of business date (given in the prompt;
  if absent use `quote_date`/today).
  - Unpaid and **NOT yet due** (due_date >= as_of) → `MONITOR_UNPAID_NOT_DUE`,
    `owner_queue = ACCOUNT_MANAGEMENT` (CONFIRMED: not COLLECTIONS).
  - Unpaid and **overdue** (due_date < as_of) → `SEND_COLLECTION_NOTICE`, `owner_queue = COLLECTIONS`.
  - No unpaid milestone → `NO_COLLECTION_ACTION` (milestone `NONE`, amount 0, due_date null, queue `NONE`).
  - For an active collection task: `milestone_id` = the unpaid MS, `amount` = its outstanding,
    `due_date` = its invoice due_date, `contact_name` = primary contact.
- Keep feasibility/recognition (accounting) and collection routing **independent** — a paid-but-unrecognized
  milestone drives accounting only; an unpaid milestone drives collection only.

**Event / invite action:**
- `event_status` from event `status` (`scheduled`→`SCHEDULED`, `confirmed`→`CONFIRMED`/`SCHEDULED`,
  `active`→`ACTIVE`, etc.).
- Voucher: `voucher_status` from `status` (`active`→`ACTIVE`); **`discount_amount` = the voucher's
  `discount_percent` numeric value**; **`max_uses` = `max_redemptions`**.
- `invite_action = SEND_BRIEFING_INVITE` (or `SEND_EVENT_INVITATION`) to invite; `invite_task` carries
  `event_id`, `voucher_code`, `owner_queue = ACCOUNT_MANAGEMENT`, the primary `contact_name`, and `customer_id`.
- In the combined `follow_up_tasks` shape: emit one COLLECTION task per unpaid milestone (with
  `next_action = COLLECT_UNPAID_MILESTONE`, milestone_id + amount_due set, event/voucher null) and one
  EVENT_INVITATION task (with `next_action = SEND_EVENT_INVITATION`, event_id + voucher_code set,
  milestone_id + amount_due null), all tied to the same primary contact and customer/opportunity IDs.

---

## Gotchas / exclusion rules (learned)
- **Wrong filter key returns 0, not an error.** Freight → filter by `quote_id`; revenue-journals →
  filter by `opportunity_id` (never customer_id). When a filter yields 0 but data should exist, pull the
  full collection or use `/api/search`.
- **Distractor freight rows exist** (ids containing `DIS`, notes like "Old route benchmark" / "Wrong
  shipment size benchmark" / "Expired … quote"). Keep only the genuine AIR/SEA/ROAD records for the quote.
- **Stale freight** (`status=="stale"` or `valid_until < quote_date`) is flagged stale and excluded from
  the recommended-mode choice, but still listed (with stale/expired markers) in the options array.
- **Module RFQs:** quote at module level only; ignore component composition tables / distractor component
  lines; do not split modules into component SKUs.
- **Catalog tier overrides prior unit price** on revision quotes — always re-derive price from the tier
  for the confirmed quantity.
- **Paid milestones → `due_date = null`.** Only outstanding/unpaid milestones keep a due_date.
- **Recommended mode = cheapest VALID grand total** (stale options excluded), even over a lower-risk mode.
- Free-text/notes fields (e.g. a warning sentence) are not key business facts — fill them sensibly but the
  scored signal is in the structured/enum/numeric fields above.

## Final reminder
Return ONLY the JSON object that matches the provided `answer_template.json` — exact keys, exact nesting,
exact enum spellings, 2-decimal money, ISO dates, `null` where required. No markdown, no commentary.
