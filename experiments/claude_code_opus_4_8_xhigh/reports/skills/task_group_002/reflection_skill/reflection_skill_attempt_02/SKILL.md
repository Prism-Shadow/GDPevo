---
name: medbridge-salesops-quote-recon
description: >-
  Produce account-ready JSON for MedBridge Sales Ops tasks built on the read-only CRM/quote/logistics/receivables
  HTTP API (catalog/EXW quotes, freight-mode comparison, indicative module quotes, milestone invoice reconciliation,
  revenue recognition, event/voucher invites). Use this whenever a prompt references the MedBridge Sales Ops API,
  a quote/RFQ/opportunity ID (Q-*, RFQ-*, OPP-*), freight options, catalog tiers, EXW pricing, milestone/phase
  invoices, revenue journals, payment/collection routing, or an event+voucher invite, AND asks you to "return only
  JSON matching answer_template.json". It encodes the API access pattern, the loose-filter distractor trap, the
  controlled enum/casing conventions, and the business-judgment rules needed to fill these templates correctly.
---

# MedBridge Sales Ops — Quote / Logistics / Receivables JSON

You are filling a fixed `answer_template.json` from a single read-only HTTP API. The template is the contract:
**emit exactly its keys, in its structure, with its controlled enum values — never invent or drop fields.**
Several mistakes below come from trusting raw API casing/values over the template's declared enums, or from
trusting a loose query filter that returns distractor rows.

## Golden rules (read first)

1. **The template is the source of truth for shape, field names, enums, and casing.** When a field declares
   `enum: A | B | C`, output one of those literal tokens — even if the raw API record stores a different
   wording or casing. The API supplies *facts*; the template dictates *vocabulary*.
2. **Recompute every derived number yourself** (line totals, EXW totals, grand totals, outstanding balances,
   recognized amounts). Cross-check internal consistency (e.g. grand_total should equal the sum of the line
   totals you listed). If a value you can independently compute disagrees with any single source, trust your
   recomputation from primitives — do not copy a number that contradicts the line items you emitted.
3. **Never trust a loose list filter blindly.** `?quote_id=...` (and any filter) matches a value *anywhere* in
   the record and returns extra/unrelated rows. Always re-filter precisely yourself and drop distractors.
4. **Money: 2-decimal USD. Dates: ISO `YYYY-MM-DD`.** Use cent precision. Copy dates verbatim from records.
5. Return ONLY the JSON. No markdown, no prose, no code fences.

## API access

Base URL: provided by the runner (e.g. `http://127.0.0.1:<PORT>`; commonly `http://127.0.0.1:8094`). Query with `curl -s`.

Collections: `customers, products, rfqs, quotes, freight-quotes, policies, opportunities, invoices, payments,
revenue-journals, events, vouchers`. List = `/api/<collection>`; detail = `/api/<collection>/<id>`.

**Finding records reliably:** prefer detail endpoints by the exact ID given in the prompt
(`/api/quotes/<id>`, `/api/opportunities/<id>`, `/api/products/<code>`). For child records (freight quotes,
invoices, payments, revenue journals, events, vouchers) fetch the **full collection** and filter in code by the
parent ID, because the query-param filter is loose. Example pattern:

```
curl -s "http://127.0.0.1:8094/api/invoices" \
  | python3 -c "import sys,json;[print(r) for r in json.load(sys.stdin)['records'] if r['opportunity_id']=='OPP-...']"
```

### The loose-filter / distractor trap (this WILL bite you)

`GET /api/freight-quotes?quote_id=Q-...` returns the 3 real options (air/sea/road) **plus distractor rows**.
Distractors are reliably identifiable by an **`FR-DIS-...` ID prefix** and often a `destination` like
`"Distractor route"` or a `risk_notes` like `"Wrong shipment size benchmark"`. Do NOT rely on `status` to spot
them — a distractor can be `active` with `low` risk (a real road option can be `stale`). **Rule: keep exactly one
freight row per mode whose ID does NOT start with `FR-DIS`.** The same caution applies to any collection: an
opportunity has exactly the phases listed on its own record; invoices/journals belong to it only when their
`opportunity_id` matches. Cross-check child IDs against the parent record.

## Field-derivation cheat sheet (raw API field -> template field)

- Product tier: `products.price_tiers[]` row where `min_qty <= qty <= max_qty` (`max_qty: null` = open-ended).
  Take `unit_price_usd`, `lead_time_days`, `shelf_life_months` (shelf life is on the product, not the tier).
- `exw_total = qty * unit_price`. `line_total = qty * unit_price`. `grand_total = sum(line_totals)` (+ freight
  only when the template explicitly includes freight in the grand total).
- Freight cost field is **`cost_usd`** (template often calls it `freight_cost_usd`). Transit text is
  `transit_days_text` (e.g. `"4-6 days"` — copy whatever string form the template's sibling examples use).
  Route risk is `route_risk`. `grand_total_usd = exw_total + cost_usd`.
- Voucher discount value comes from **`discount_percent`** — output that number as-is even when the template
  labels the field `voucher_discount` / `discount_amount` or says "USD". Max uses comes from `max_redemptions`.
- Payment terms / customer policy: resolve via the `policies` collection (see Quote SOP), not the raw
  `customer.payment_profile` placeholder.
- Revenue journal accounts: API stores `"Deferred Revenue"` / `"Implementation Services Revenue"`; templates use
  the enum tokens `DEFERRED_REVENUE` / `IMPLEMENTATION_SERVICES_REVENUE`. Emit the enum token.

## Task family A — Catalog / EXW quote with freight comparison

Template shape: `quote_summary` (or `pricing`) + `freight_options[]` + `policy_flags`/`transport_decisions`/`client_warnings`.

SOP:
1. `GET /api/quotes/<id>` → confirm `customer_id`, `quote_date`, product code, `confirmed_quantity`. Also
   `GET /api/customers/<customer_id>` and `GET /api/products/<code>`.
2. Pick the price tier (see cheat sheet). Compute `exw_total = qty * unit_price`.
3. Freight: fetch all freight-quotes, keep the non-`FR-DIS` row per mode. For each: `grand_total = exw + cost_usd`.
4. **Validity / staleness** (two independent signals):
   - `valid_until` vs `quote_date`: valid if `valid_until >= quote_date`, else expired.
   - `status` field: `"stale"` marks a stale source.
   - For a `validity_status` enum field, prefer the source `status` wording the template/peers use
     (`VALID` / `STALE`); a row can be both stale and past-due. `source_is_stale = (status == "stale")`.
   - `all_freight_options_valid_on_quote_date` = true only if **every real option** has `valid_until >= quote_date`.
   - `freight_reconfirmation_required` is **always true** (policy `POL-FREIGHT-RECONFIRM` / `RECONFIRM_AT_ORDER`).
5. **`recommended_mode`**: among options that are valid (not expired, not stale, not distractor), pick the one
   with the **lowest `grand_total_usd`**. Cost is the tie-breaker basis when risks are acceptable; report risk
   per option but don't let a merely "medium/low" risk override a clearly cheaper valid option. Exclude any
   expired/stale option from candidacy. Output the mode in the casing the template's enum/peers use (the
   `freight_options[].mode` samples in the template show the expected casing — often UPPER `AIR|SEA|ROAD`).
6. **Casing for free-form-looking strings** (`mode`, `customs_border_risk`, `validity_status`): match the
   template's own example tokens. If the template pre-fills `"AIR"`, `"LOW"`, `"MEDIUM"` etc., normalize the
   lowercase API values (`air`, `low`) to that UPPER casing. Do not assume the API's lowercase is what's wanted.
7. **Payment terms & customer policy**:
   - Map the customer to the right `policies` record by segment/situation, then read `terms_code` for
     `payment_terms` (e.g. recurring NGO/commercial → `NET_30_AFTER_PO`; new/prospect NGO → `PREPAY_100`).
     Use the policy's `terms_code`, NOT the customer's raw `payment_profile` (which can be a placeholder like
     `NEW_CLIENT_REVIEW`).
   - A field literally named **`customer_policy`** wants the policy record's stable **`id`**
     (e.g. `POL-RECURRING-NGO-PAYMENT`), not the segment label and not the policy name.
   - `quote_basis`: for catalog quotes with freight options use the template's token for that
     (e.g. `EXW` or `EXW_PLUS_FREIGHT_OPTIONS` — match the template's enum sample).

## Task family B — Indicative module / RFQ quote (EXW only, freight excluded)

Template shape: `quote_header` + `line_items[]` + `quote_controls`.

SOP:
1. `GET /api/rfqs/<id>` → `requested_modules[]` (product_code + quantity), `customer_id`, `quote_date`.
2. **Quote at the requested module level only.** Each module is a product with its own single-tier price.
   The RFQ may list `component_composition_distractors` / a composition table — **never split modules into
   component SKUs.** One `line_items` entry per requested module (policy `POL-MODULE-GRANULARITY`).
3. Per line: `unit_price` from the module's tier, `article_number`, `lead_time_days`, `shelf_life_months`,
   `line_total = quantity * unit_price`.
4. `grand_total = sum(line_total)`. Verify it equals the sum of the lines you emitted; if the only available
   source value disagrees by a small amount, trust your sum of the listed lines.
5. `quote_basis = EXW_ONLY`, `freight_excluded = true`, `currency = USD`. No freight rows (no destination →
   policy `POL-INDICATIVE-EXW`).
6. `payment_terms` from policy by segment (new/prospect NGO → `PREPAY_100`).
7. `offer_validity_days = 30` (policy `POL-QUOTE-VALIDITY` / `QUOTE_VALID_30_DAYS`) unless overridden.
8. `who_documentation_required`: keep the template's pre-filled default unless a record clearly contradicts it.

## Task family C — Milestone invoice reconciliation + revenue recognition + follow-ups

Template shape: `account_status` (or `engagement_reconciliation`) + `milestones[]` + `revenue_recognition` +
`event`/`event_actions` + `follow_up_tasks`/`invoice_actions`. Two template dialects exist — read the actual
template's enums each time; they differ (see below).

SOP:
1. `GET /api/opportunities/<id>` → `stage` (`closed_won` → enum `WON`), `won_amount_usd`, `phases[]`
   (each has `phase_id`, `amount_usd`, `completion_date`, `invoice_id`), `contact`, `customer_id`.
2. `won_amount` = `won_amount_usd`. `phase_total` = sum of phase amounts. `opportunity_matches...` = (won == phase total).
3. For each phase, pull its invoice from `/api/invoices` by `invoice_id`/`phase_id`:
   - `amount`/`invoice_total` = invoice `amount_usd`; `paid_amount` = `paid_amount_usd`; `amount_unpaid` =
     `outstanding_amount_usd`.
   - `payment_state`: paid (`outstanding == 0`) → `PAID`; partial → `PARTIAL`; else `UNPAID`.
   - `invoice_state` (when present): map invoice `status` → enum (`paid`→`PAID`, `unpaid`/`draft`→`OPEN`,
     etc.; use the template enum, e.g. `PAID | OPEN | VOID | UNKNOWN`).
   - **`due_date` = the invoice's `due_date`, copied verbatim — including for PAID milestones.** Do NOT null out
     a paid milestone's due date; only emit `null` when the invoice genuinely has no due date. (Common mistake:
     nulling paid milestones — the invoice still carries a due date.)
4. **Revenue recognition** (policy `POL-REVREC` / `RECOGNIZE_PAID_COMPLETE_MILESTONES`): a milestone needs
   recognition when it is **paid AND complete**. Check `/api/revenue-journals` for a row matching the phase/invoice.
   - paid + complete + journal exists → `RECOGNIZED`.
   - paid + complete + **no** journal → the "missing" state — use the template's exact token
     (`REQUIRED_MISSING` in one dialect, `MISSING_REVENUE_JOURNAL` in another). This is the actionable case.
   - unpaid → `NOT_REQUIRED_UNPAID` (recognition not required yet).
   - `recognition_status` (summary): `COMPLETE_FOR_PAID_MILESTONES` if every paid milestone has a journal,
     else `MISSING_FOR_PAID_MILESTONES`. `recognized_milestones` = paid+journaled; `missing_required_milestones`
     = paid-but-no-journal; `recognized_amount` = sum of recognized (posted journal) amounts.
5. **`outstanding_balance`** = sum of unpaid invoice `outstanding_amount_usd` (matches opportunity
   `outstanding_amount_usd`). `total_paid` = sum of `paid_amount_usd`.
6. **`milestone_id` representation is template-driven** — do not guess:
   - If the enum constrains it to `MS1 | MS2 | MS3`, emit `MS<phase_number>` (order ascending).
   - If the field says "stable phase or invoice milestone id" with no enum, emit the source `phase_id`
     (e.g. `HEL-P2`). Read the template field's declared enum/description and follow it exactly.
7. **Event + voucher**: from `/api/events` and `/api/vouchers` filtered to this customer/opportunity.
   - `event_status`: map free-form API status (`scheduled`/`confirmed`/`live`/`completed`/`tentative`) to the
     template enum (`SCHEDULED | ACTIVE | COMPLETED | CANCELLED | UNKNOWN`) — closest match, UPPER.
     `live`/`confirmed` → `ACTIVE` unless an exact token exists; `scheduled` → `SCHEDULED`.
   - `voucher_status`: API `active` → `ACTIVE`. Discount = `discount_percent`. Max uses = `max_redemptions`.
   - `event_date` = event's `event_date` (only if the template has the field).
8. **Follow-up / action routing**:
   - Each unpaid milestone → a collection task. If due date is in the future relative to the business date →
     `MONITOR_UNPAID_NOT_DUE` (owner `ACCOUNT_MANAGEMENT`); if due/overdue → `SEND_COLLECTION_NOTICE` /
     `COLLECT_UNPAID_MILESTONE` (collections owner). Use the as-of/current business date the prompt pins
     (it may differ from today — e.g. a task may say "treat 2026-06-01 as the current business date").
   - Each paid-but-unrecognized milestone → the accounting action (`RECORD_REVENUE_MS<n>`), with
     `debit_account = DEFERRED_REVENUE`, `credit_account = IMPLEMENTATION_SERVICES_REVENUE`, `owner_queue = ACCOUNTING`,
     `amount` = that milestone's amount.
   - Event present → an invite task (`SEND_EVENT_INVITATION` / `SEND_BRIEFING_INVITE`) carrying `event_id` +
     `voucher_code`, owner `ACCOUNT_MANAGEMENT` (or `EVENTS` if the enum offers it and that fits), tied to the
     prompt's named contact and customer.
   - Always set `contact_name`/`linked_*`/`customer_id` to the contact and IDs named in the prompt/opportunity.
   - For task `due_date`: collection tasks use the unpaid invoice's due date; event-invite tasks use the
     event date (or the template's convention shown by sibling fields).

## Common pitfalls -> rules (the mistakes to avoid)

- **Distractor freight rows.** Loose filter returns `FR-DIS-*` rows. Keep one non-`FR-DIS` row per mode.
- **Wrong policy representation.** `customer_policy` = policy record `id`; `payment_terms` = policy `terms_code`;
  neither is the customer's `segment` label or `payment_profile` placeholder.
- **Grand-total drift.** Always `grand_total = sum(line_totals)`; verify internal consistency rather than copying
  a single field that disagrees with the lines you listed.
- **Nulling paid milestones' due dates.** Copy the invoice `due_date` for paid milestones too.
- **Casing.** Normalize free-form API tokens (`air`, `low`, `closed_won`, `scheduled`, `active`,
  `Deferred Revenue`) to the template's enum casing/spelling (`AIR`, `LOW`, `WON`, `SCHEDULED`, `ACTIVE`,
  `DEFERRED_REVENUE`). Let the template's pre-filled samples and enum lists dictate casing.
- **Validity vs staleness conflation.** They are two signals; a `recommended_mode` must exclude expired/stale
  options, and `recommended_mode` is the cheapest valid grand total.
- **Splitting modules into components.** Module RFQs are quoted at module line level only; ignore composition
  distractors.
- **Enum-token drift across dialects.** The same concept has different tokens in different templates
  (`REQUIRED_MISSING` vs `MISSING_REVENUE_JOURNAL`; `MS1` vs `HEL-P1`). Read the actual template's enum each
  time; never carry a token over from memory of a prior task.
- **Business date.** Use the as-of date the prompt pins for due/overdue and monitor-vs-notice decisions, which
  may not be today's date.

## Final check before emitting

- Output validates against the template (same keys, same nesting, all required fields present).
- Every enum field holds a declared token; every money field has 2 decimals; every date is ISO.
- Numbers recomputed and internally consistent (line sums, grand total, outstanding, recognized amount).
- No `FR-DIS` rows, no component splits, no distractor invoices/journals from other opportunities.
- Output is raw JSON only.
