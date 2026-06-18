---
name: medbridge-sales-ops
description: >-
  Produce account-ready JSON decision packages from the MedBridge Sales Ops API
  (CRM, quotes, freight/logistics, milestone receivables). Use this skill WHENEVER a
  task asks you to verify customer/quote/RFQ/opportunity records against a MedBridge
  Sales Ops API (base like http://127.0.0.1:<PORT>) and emit JSON matching an
  answer_template.json — including: catalog-tier quote pricing and EXW totals;
  EXW-plus-freight transport comparisons with route/border risk, freight validity
  and reconfirmation, and a recommended mode; module-only (IEHK / kit) indicative
  quotes; and opportunity-to-invoice-to-payment-to-revenue-journal reconciliation
  with outstanding balance, revenue recognition state, and CRM follow-up routing
  (collection, event/voucher invitation). Trigger even when the user only says
  "quote decision package", "freight comparison", "engagement / account
  reconciliation", "revenue recognition check", or names a MedBridge quote/RFQ/
  opportunity ID (Q-*, RFQ-*, OPP-*), and never freelance the business rules below.
---

# MedBridge Sales Ops — account-ready JSON packages

You verify records against one read-only JSON API and return JSON that exactly
matches a provided `answer_template.json`. The data is small, internally
consistent, and seeded — every required value is **derivable from the API**, never
invented. Your job is to find the *right* records (the API loosely over-returns)
and apply the business conventions the templates encode.

## 0. Universal rules (apply to every task family)

1. **The template is the contract.** Read `input/payloads/answer_template.json`
   first. Reproduce its exact key names, nesting, ordering, and especially its
   **controlled enum values** (e.g. `EXW`, `NET_30_AFTER_PO`, `RECORD_REVENUE_MS2`).
   Templates list allowed enums inline as `"enum: A | B | C"` — pick one of those
   literally. Output **only** JSON, no markdown, no prose, no trailing commentary.
2. **API only.** Never read local business files. Reach the API with `curl`. The
   base URL is given in the prompt (env var like `API_BASE_URL` / `BASE_URL` or
   `http://127.0.0.1:<PORT>`). Confirm reachability with `GET /health`.
3. **Fetch full collections, then filter yourself.** List filters
   (`?quote_id=...`, `?customer_id=...`) match a value **anywhere/nested** in the
   record, so they return extra unrelated rows. Pull the whole collection and
   match precisely on the exact field. See the distractor rules in each family.
4. **Money:** USD, cent-level. Render template-required decimals (e.g. `2420.00`).
   **Dates:** ISO `YYYY-MM-DD`. **IDs:** copy the API's stable IDs verbatim.
5. **The "business date" matters.** The prompt states a quote date / as-of date
   (commonly `2026-06-01`). Use it for all validity / due / staleness comparisons,
   not today's real date.
6. **Catalog tier overrides prior pricing.** Quotes carry a `prior_unit_price_usd`
   / `prior_quote_quantity`. These are history — never quote them. Always reprice
   from the current product `price_tiers` at the confirmed quantity.

Identify the task family from the template/prompt, then follow its SOP:
- **A. Freight / transport decision package** — template has `freight_options`,
  `grand_total`, `recommended_mode`, risk/validity fields. (Q-* quotes with freight.)
- **B. Module-only indicative quote** — template has `line_items`, `EXW_ONLY`,
  `who_documentation_required`. (RFQ-* module requests, no destination.)
- **C. Engagement / receivables reconciliation** — template has `milestones`,
  `outstanding_balance`, `revenue_recognition`, follow-up/`event` actions. (OPP-*.)

---

## A. Freight / transport decision package

Inputs: a quote ID (`Q-...`), confirmed quantity, quote date. Output: catalog
pricing + EXW total, 3 freight options (AIR/SEA/ROAD) with EXW-plus-freight grand
totals, risk + validity flags, a recommended mode, and policy/payment flags.

### A1. Pricing
1. `GET /api/quotes/<id>` → read `customer_id`, `primary_product_code`,
   `confirmed_quantity`, `quote_date`. Cross-check the prompt's quantity/date.
2. `GET /api/products/<product_code>` → choose the **catalog tier** whose band
   contains the confirmed quantity: `min_qty <= qty <= max_qty`. A `max_qty` of
   `null` means open-ended (no upper bound). Take `unit_price_usd`,
   `lead_time_days`, `shelf_life_months` from that tier/product.
3. `exw_total_usd = confirmed_quantity * tier.unit_price_usd`.
4. `quote_basis` is EXW with freight shown as separate options. Use the exact
   string the template wants (`"EXW"`, or `"EXW_PLUS_FREIGHT_OPTIONS"` for the
   `policy_terms.quote_basis` field).

### A2. Selecting the REAL freight options (loose-filter trap)
`GET /api/freight-quotes`, then keep only rows where `quote_id` **exactly** equals
the quote and that are the genuine lane set. **Exclude distractors:**
- Any `id` starting with `FR-DIS-` — these are benchmark/archived/wrong-size rows.
- Rows whose `status` is `stale`/`mismatch` AND that duplicate a mode you already
  have a clean active row for, or whose `shipment_cbm`/`shipment_weight_kg` differ
  from the consistent real shipment dimensions of the genuine set.
The genuine set is exactly three rows — one `mode` each of `air`, `sea`, `road` —
sharing one consistent `shipment_cbm`/`shipment_weight_kg`. Output `mode` uppercased
(`AIR`/`SEA`/`ROAD`). Note: a *real* lane can still be `status: "stale"` / expired
(e.g. a road quote that genuinely lapsed) — that one stays in the output and gets
flagged stale; it is NOT a `FR-DIS-` distractor. Distinguish "real but expired"
from "fake distractor."

### A3. Per-option fields
- `freight_cost_usd` = `cost_usd`; `transit_days` = `transit_days_text` (copy the
  template's format — some want `"4-6 days"`, some want `"3-5"`; mirror the example
  value style in the template).
- `valid_until` = freight `valid_until`.
- `grand_total_usd = exw_total_usd + freight_cost_usd`.
- **Risk** from `route_risk`: uppercase it for `risk_level`/`customs_border_risk`
  (`low→LOW`, `medium→MEDIUM`, `high→HIGH`). For `risk_flag`:
  `low→NONE`, `medium→MEDIUM_BORDER_RISK`, `high→HIGH_BORDER_RISK`.
- **Validity** vs the quote date: `validity_status = VALID` if
  `valid_until >= quote_date`, else `STALE`. `source_is_stale` is `true` if the
  freight `status` is `stale` **or** it is expired on the quote date, else `false`.

### A4. Recommended mode (decision basis — order matters)
Pick the mode to recommend by filtering, then optimizing:
1. **Eligibility filter (feasibility/safety):** drop options that are STALE/expired
   on the quote date, and drop HIGH border-risk options. (MEDIUM risk is allowed but
   disfavored vs LOW.)
2. **Among the eligible, prefer LOW route risk over MEDIUM.**
3. **Tie-break by lowest `grand_total_usd`** (cheapest landed cost).
This typically yields **SEA** when AIR and SEA are both LOW/valid (SEA is cheaper)
and ROAD is medium/high or stale. Recommend by transport mode string (`"SEA"` etc).
Keep *risk/validity* separate from *recommendation*: you still list every real
option with its true flags even though only one is recommended.

### A5. Policy / payment flags
- `freight_reconfirmation_required` = **true** always (policy
  `POL-FREIGHT-RECONFIRM`: freight rates reconfirm at final order).
- `all_freight_options_valid_on_quote_date` = true only if **all three** real
  options are VALID on the quote date (false if any is stale/expired).
- `payment_terms` from the customer + payment policies (see Payment terms table).
- `customer_policy` / segment label: map the customer `segment` to the controlled
  value the template shows (e.g. recurring NGO → `RECURRING_NGO`).
- `road_quote_invalid_or_stale` = true if the ROAD option is stale/expired.
- `freight_warning`: when something is stale or high-risk, write a short factual
  sentence: rates require reconfirmation at final order; name the stale freight ID,
  its expiry date, and its risk, and say it should not be used without a fresh
  quote. Keep it specific and grounded in the records.

---

## B. Module-only indicative quote (RFQ, EXW only)

Inputs: an RFQ (`RFQ-...`) listing `requested_modules`, no confirmed destination.
Output: one EXW-only quote with one line **per requested module**.

### B1. SOP
1. `GET /api/rfqs/<id>` → `customer_id`, `quote_date`, `requested_modules`
   (each `{product_code, quantity}`), `incoterm_requested`.
2. For **each requested module**, `GET /api/products/<code>`:
   - `article_number`, `unit_price` from the product price tier at the requested
     quantity (module products usually have a single open tier), `lead_time_days`,
     `shelf_life_months` from that tier/product.
   - `line_total = quantity * unit_price`.
   - Emit one line item per module, **in the RFQ's module order**.
3. `grand_total = sum(line_total)`.
4. `freight_excluded = true`, `quote_basis = "EXW_ONLY"` (policy `POL-INDICATIVE-EXW`
   + `POL-EXW-SCOPE`: no destination ⇒ EXW only, exclude freight).
5. `offer_validity_days = 30` (policy `POL-QUOTE-VALIDITY`).
6. `who_documentation_required = true` for these emergency-health-kit/WHO module RFQs.
7. `payment_terms`: new NGO ⇒ `PREPAY_100` (see Payment terms table).

### B2. Critical exclusion — module lines ONLY
RFQs and products carry `component_composition_distractors` /
`components` (e.g. "Paracetamol tabs", "gauze and splints", "RDT buffer packs").
These are **medical-review context, not quote lines.** Never split a module into
component SKUs, never add component lines, never re-price by component. One line per
requested module, period (policy `POL-MODULE-GRANULARITY`). Quantities come straight
from the RFQ — do not infer extra units from composition tables.

---

## C. Engagement / receivables reconciliation (opportunity → cash → revenue)

Inputs: an opportunity (`OPP-...`), its customer, a named contact, an as-of date,
and (usually) a linked event + voucher. Output: account status, per-milestone
state, revenue-recognition status, and routed follow-up tasks.

### C1. Gather and link
1. `GET /api/opportunities/<id>` → `stage`, `won_amount_usd`, `phases[]`
   (`phase_id`, `amount_usd`, `invoice_id`, `completion_date`), `contact`,
   `outstanding_amount_usd`.
2. `GET /api/invoices`, `GET /api/payments`, `GET /api/revenue-journals`; filter
   each to this `opportunity_id` precisely (the collections contain many other
   accounts — match exactly). Link by `invoice_id` / `phase_id`.
3. Number milestones in phase order. Output milestone IDs in the convention the
   template uses — some templates label them `MS1/MS2/MS3` (ascending), others use
   the API `phase_id`. Match the template's enum/example exactly.

### C2. Per-milestone derivation
- `invoice_total` / `amount` = invoice (or phase) `amount_usd`.
- **Payment state** from the matched payment(s) and invoice paid/outstanding:
  fully paid ⇒ `PAID`; partially paid ⇒ `PARTIAL`; none ⇒ `UNPAID`. `paid_amount`
  = sum of posted payments (or invoice `paid_amount_usd`); `amount_unpaid` =
  invoice `outstanding_amount_usd`.
- **`invoice_state`** (when the template asks): mirror the invoice `status`
  mapped to the template enum (paid⇒`PAID`, unpaid/overdue⇒`OPEN`, etc.).
- **Due-date nulling:** for a **PAID** milestone set `due_date` to `null` (it is
  settled — no due date is actionable). For an unpaid milestone use the invoice
  `due_date`.
- **Revenue recognition status** (policy `POL-REVREC` — recognize paid+complete
  milestones; unpaid stay outstanding):
  - PAID **and** a matching revenue journal exists ⇒ `RECOGNIZED`.
  - PAID **but no** revenue journal ⇒ recognition is *required but missing*
    (`REQUIRED_MISSING` or `MISSING_REVENUE_JOURNAL`, per template enum).
  - UNPAID ⇒ recognition not yet required ⇒ `NOT_REQUIRED_UNPAID`.

### C3. Account-level rollups
- `opportunity_matches_milestones` / `opportunity_matches_phase_total` = true iff
  `won_amount == sum(phase amounts)`.
- `outstanding_balance` = sum of unpaid invoice outstanding amounts (= opportunity
  `outstanding_amount_usd`; verify they agree).
- `total_paid_amount` = sum of posted payments / paid invoice amounts.
- Contact: use the named contact; link it to this customer_id and opportunity_id.

### C4. Revenue-recognition rollup block
- `recognized_milestones` = paid milestones that have a journal.
- `missing_required_milestones` = paid milestones lacking a journal.
- `recognized_amount` = sum of recognized milestone amounts.
- `recognition_status`: `COMPLETE_FOR_PAID_MILESTONES` if every paid milestone is
  recognized; `MISSING_FOR_PAID_MILESTONES` if any paid milestone lacks a journal;
  `NOT_REQUIRED` if nothing is paid yet. (Watch for the classic seeded case: a
  milestone that is **paid but has no journal** ⇒ flag missing, and the primary
  accounting action becomes "record revenue for that milestone".)

### C5. Action routing (the decision layer)
Templates differ; produce the actions their enums demand. General logic:

**Accounting / revenue action** — driven by the paid-but-unrecognized milestone:
- If a paid milestone lacks a journal ⇒ action `RECORD_REVENUE_MS<n>`, on that
  milestone, `amount` = its value, `debit_account = DEFERRED_REVENUE`,
  `credit_account = IMPLEMENTATION_SERVICES_REVENUE`, `owner_queue = ACCOUNTING`.
- If all paid milestones are already recognized ⇒ `VERIFY_REVENUE_ONLY`/
  `NO_ACCOUNTING_ACTION` per template (nothing to post).

**Collection action** — driven by the unpaid milestone vs the as-of date:
- Unpaid and **not yet due** (`due_date > as_of_date`) ⇒ `MONITOR_UNPAID_NOT_DUE`
  / `COLLECT_UNPAID_MILESTONE` task but not overdue; owner `ACCOUNT_MANAGEMENT`.
- Unpaid and **due/overdue** (`due_date <= as_of_date`) ⇒ `SEND_COLLECTION_NOTICE`;
  owner `COLLECTIONS`.
- No unpaid milestone ⇒ `NO_COLLECTION_ACTION`.
- The collection task carries the unpaid milestone ID, its amount, and its due date.

**Event / voucher invitation action** — from the linked event + voucher:
- `GET /api/events` and `GET /api/vouchers`; match the event by `opportunity_id`
  (or the ID named in the prompt) and the voucher by `event_id`/`code`.
- Map event `status` to the template enum (`scheduled→SCHEDULED`,
  `confirmed`/`live`→`ACTIVE`, `completed→COMPLETED`, etc.). Map voucher `status`
  (`active→ACTIVE`). `discount_amount` = voucher `discount_percent` value;
  `max_uses` = `max_redemptions`.
- If the event is upcoming/scheduled ⇒ invite action `SEND_EVENT_INVITATION` /
  `SEND_BRIEFING_INVITE`; owner `ACCOUNT_MANAGEMENT` (or `EVENTS`); attach
  `event_id`, `voucher_code`, contact, customer_id.
- Task titles: short, human, name the customer (e.g.
  `"Milestone 2 collection - <Customer Name>"`,
  `"Send celebration invite - <Customer Name>"`).
- Task `due_date`: collection tasks use the unpaid invoice due date; invitation
  tasks use a sensible pre-event date when the template expects one — prefer a date
  the records justify (e.g. shortly before the event); never invent far-future dates.

**Customer name caveat:** use the customer `name` from the API record. The prompt's
friendly name may differ slightly (e.g. "Helios Health Alliance" in the prompt vs a
different stored name) — follow the convention the template/answer expects, which is
usually the human-readable account name the prompt uses for *titles* and the API
`name` for the canonical `customer_name` field. When in doubt, match the API record.

---

## Payment terms — controlled values

Derive from customer `payment_profile` / `segment` and the payment policies:

| Situation | Customer signal | `payment_terms` value | Policy |
|---|---|---|---|
| New NGO, no approved credit / first order | `segment: new_ngo`, `payment_profile: NEW_CLIENT_REVIEW`, `is_recurring:false` | `PREPAY_100` | POL-NEW-CLIENT-PAYMENT |
| Recurring NGO | `segment: recurring_ngo`, `is_recurring:true` | `NET_30_AFTER_PO` | POL-RECURRING-NGO-PAYMENT |
| Recurring commercial | `payment_profile: NET_30_AFTER_PO` | `NET_30_AFTER_PO` | (account terms) |
| Milestone implementation | `payment_profile: MILESTONE_BILLING` | milestone billing per phases | POL-REVREC |

If grant terms restrict net terms, honor the restriction over the default.

## Common misjudgments — do NOT do these

- **Do not** quote `prior_unit_price_usd` or `prior_quote_quantity`; reprice from
  the current catalog tier at the confirmed quantity.
- **Do not** include `FR-DIS-*` freight rows or wrong-shipment-size rows just
  because the loose filter returned them. There are exactly three real lanes.
- **Do not** confuse "real but expired/stale" lanes (keep + flag) with fake
  `FR-DIS-` distractors (drop entirely).
- **Do not** split modules into component SKUs or add component lines — module
  line level only; composition tables are medical context.
- **Do not** put a `due_date` on a PAID milestone — null it.
- **Do not** mark a paid milestone `RECOGNIZED` if no revenue journal exists —
  that is the "missing journal" case that drives the record-revenue action.
- **Do not** recommend a stale/expired or HIGH-risk lane even if it is cheapest;
  eligibility (validity + risk) gates the cheapest-cost tie-break.
- **Do not** compare validity/staleness against today's real date — use the
  prompt's stated quote/as-of date.
- **Do not** invent IDs, amounts, dates, or enum values not present in the API or
  template; every value must trace to a record or a stated convention.
- **Do not** emit markdown, code fences, or explanation — only the JSON object that
  matches the template's structure exactly.

## Quick verification before returning
- Every template key present, correct nesting/order, enums are literal allowed values.
- All money at required decimal precision; `grand_total = EXW + freight` and line
  sums reconcile; `outstanding = won - paid` and matches the opportunity.
- Exactly three real freight lanes; recommended mode is eligible (valid + not high
  risk) and lowest landed cost among eligibles.
- Paid milestones with journals = RECOGNIZED; paid without = missing → action set;
  unpaid = NOT_REQUIRED_UNPAID with due date carried into the collection task.
