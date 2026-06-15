---
name: medbridge-sales-ops-packager
description: >-
  Build account-ready JSON decision packages from the MedBridge Sales Ops API
  (CRM / quotes / freight / receivables / milestone-engagement data at base
  http://127.0.0.1:<PORT>). Use this whenever a task asks you to verify
  customers, products, RFQs, quotes, freight quotes, opportunities, invoices,
  payments, revenue journals, events, or vouchers and return JSON that matches a
  provided answer_template.json. Covers four task families: (1) catalog quote +
  freight-mode decision, (2) module / RFQ EXW-only quote, (3) won-opportunity
  engagement reconciliation with accounting + collection routing, and (4)
  account reconciliation with milestone + event follow-up tasks. Trigger it for
  any "return only JSON matching input/payloads/answer_template.json", "decision
  package", "engagement reconciliation", "freight comparison", "recommended
  transport mode", "revenue recognition", or "milestone / collection follow-up"
  request in this domain, even if the user does not name the API explicitly.
---

# MedBridge Sales Ops — Account-Ready JSON Packager

You produce one JSON object that exactly matches a supplied
`input/payloads/answer_template.json`, populated from a read-only HTTP API. The
work is part data-lookup, part business-judgment. The grader rewards faithful
derivation from the API plus the exact controlled vocabulary and conventions the
template declares — so the two cardinal rules are:

1. **The answer_template.json is the contract.** Output every key it shows, in
   its shape, with values drawn ONLY from the enums/format it declares. Never
   invent fields and never drop fields. Enum spellings and number formats differ
   *between* templates — read each one fresh; do not reuse another task's casing.
2. **The API is the single source of truth for record values**, but the *prompt*
   can override identity/scope (which entity, which scope, "module level only",
   "EXW only", "as of <date>"). Read the prompt for scope, the API for values.

Work the task in this order: read the prompt → read the template → identify the
task family → pull records → derive values → emit JSON only (no markdown, no
prose).

## The API

Base URL is given by the runner (e.g. `http://127.0.0.1:8094`). Query with curl.

Useful endpoints (full list at `GET /api`):
`/api/customers/<id>`, `/api/products/<code>`, `/api/rfqs/<id>`,
`/api/quotes/<id>`, `/api/freight-quotes` (+`/<id>`), `/api/policies`,
`/api/opportunities/<id>`, `/api/invoices`, `/api/payments`,
`/api/revenue-journals`, `/api/events`, `/api/vouchers`,
`/api/search?q=<text>`. Money is USD; emit cent precision. Dates are ISO
`YYYY-MM-DD`.

### The loose-filter pitfall (this WILL bite you)

List filters like `?quote_id=Q-...` match the value *anywhere in the record,
nested-aware*, so they return distractor rows that merely mention the id, plus
genuinely unrelated rows. **Never trust a filtered list blindly.** Instead:

- Fetch the full collection and filter yourself on the exact field
  (`r["quote_id"] == "<id>"`, `r["opportunity_id"] == "<id>"`).
- For freight, the canonical rows follow `FR-<PRODUCT>-<MODE>` (e.g.
  `FR-WC-AIR/SEA/ROAD`). Rows named `FR-DIS-*` are decoys; rows with
  `status` not `active` (e.g. `stale`) or a different `quote_id` are decoys even
  if the loose filter surfaced them. Keep exactly the three canonical
  AIR/SEA/ROAD rows for the target quote.
- For invoices/payments/journals, key strictly on `opportunity_id` and on the
  matching `phase_id`/`invoice_id`. There are records for many other accounts.

## Catalog tier selection (the most common silent error)

Quote lines carry `prior_unit_price_usd` / `prior_quote_quantity`. **These are
distractors — ignore them.** Unit price, `lead_time_days`, and
`shelf_life_months` come from the product `price_tiers` row whose
`[min_qty, max_qty]` bracket contains the *confirmed* quantity (`max_qty: null`
means open-ended). Pick the tier by confirmed qty, then:

- `unit_price_usd` = that tier's `unit_price_usd`
- `lead_time_days` = that tier's `lead_time_days`
- `shelf_life_months` = the product's `shelf_life_months`
- `exw_total_usd` = confirmed_quantity × tier unit_price

A quote's `source_notes` often tells you the intended tier ("use active
900-1199 pack tier") — use it to sanity-check your bracket pick.

## Task families

Decide which family you're in by the template's top-level keys:

| Top-level keys in template | Family | Reference doc |
|---|---|---|
| `quote_summary`, `freight_options`, `policy_flags` | **A. Catalog quote + freight decision** | `references/quoting.md` |
| `pricing`, `transport_decisions`, `client_warnings` | **A′. Catalog quote + freight decision (richer)** | `references/quoting.md` |
| `quote_header`, `line_items`, `quote_controls` | **B. Module / RFQ EXW-only quote** | `references/quoting.md` |
| `engagement_reconciliation`, `invoice_actions`, `event_actions` | **C. Engagement reconciliation + action routing** | `references/reconciliation.md` |
| `account_status`, `milestones`, `revenue_recognition`, `follow_up_tasks` | **D. Account reconciliation + follow-up tasks** | `references/reconciliation.md` |

Read the matching reference file before answering — it has the field-by-field
derivation, the exact enum values, and the pitfalls I have actually hit. The
quoting families (A/A′/B) are in `references/quoting.md`; the receivables
families (C/D) are in `references/reconciliation.md`.

## Cross-cutting conventions (memorize these)

These caused real mistakes; apply them everywhere.

- **Enum casing follows the template, and risk/status enums are UPPERCASE in
  output even when the API stores them lowercase.** API `route_risk:"high"` →
  output `HIGH`; API `status:"scheduled"` → `SCHEDULED`; API voucher
  `status:"active"` → `ACTIVE`. But when the template *example* shows a value
  lowercased, follow the template. When unsure between two spellings, copy the
  literal token from the template's `enum:` annotation.
- **`customs_border_risk` ≠ `route_risk`.** `route_risk` is general (sea can be
  "medium" for shelf-life/transit reasons). `customs_border_risk` is specifically
  land-border/customs exposure: AIR and SEA are typically `LOW`; ROAD lanes
  carry the border risk (`MEDIUM`/`HIGH`). Read `risk_notes` to disambiguate —
  notes mentioning "customs"/"border" drive this field; notes about
  "shelf-life"/"transit" do not. Do not blindly uppercase `route_risk` into it.
- **Freight validity is by date, not just status.** A freight row is valid for
  the quote only if `valid_until >= quote_date` AND `status == active`. A row
  with `status:"stale"` or `valid_until < quote_date` is stale/expired and must
  not be recommended. The template's validity enum is usually `VALID` vs
  `STALE` (not "EXPIRED") and a parallel boolean `source_is_stale` — use the
  template's exact tokens.
- **`recommended_mode`** = the cheapest *valid* (in-date, active) option whose
  risk is acceptable (`LOW`). Compare by `grand_total_usd`. Sea is usually
  cheapest and low-risk → usually recommended; air wins only if the prompt
  demands speed/emergency. Never recommend a stale/expired or high-border-risk
  lane.
- **`quote_basis`** comes from the quote's `incoterm`, mapped to the template's
  enum. "EXW plus freight options" → use the template's freight-inclusive token
  (e.g. `EXW_PLUS_FREIGHT_OPTIONS`), NOT bare `EXW`. An indicative/no-destination
  RFQ → `EXW_ONLY` / freight excluded.
- **Payment terms** derive from the customer, mediated by policy:
  new/prospect NGO (segment `new_ngo`, profile `NEW_CLIENT_REVIEW`) →
  `PREPAY_100` (POL-NEW-CLIENT-PAYMENT). Recurring NGO/commercial →
  `NET_30_AFTER_PO` (POL-RECURRING-NGO-PAYMENT), unless restricted grant terms
  say otherwise.
- **A "customer_policy" / "policy" code field wants the policy CATEGORY code,
  not the policy record id.** e.g. output `RECURRING_NGO`, not
  `POL-RECURRING-NGO-PAYMENT`. (When a field is literally named `*_policy_id`,
  then it wants the id — read the field name.)
- **Paid milestone `due_date` is `null`; unpaid milestone `due_date` is the
  invoice `due_date`.** Once a milestone/invoice is settled it has no
  outstanding due date. Do not copy the invoice due date onto paid milestones.
- **Revenue recognition** (see reconciliation.md for the full state machine):
  paid + posted revenue journal → recognized; paid + NO journal → the template's
  "missing journal" token (which differs per template:
  `MISSING_REVENUE_JOURNAL` vs `REQUIRED_MISSING`); unpaid → `NOT_REQUIRED_UNPAID`.
- **Vouchers:** the API stores `discount_percent` and `max_redemptions`. Map
  `discount_percent`'s number straight into the template's `discount_amount` /
  `voucher_discount` (do NOT convert to a USD figure) and `max_redemptions` into
  `max_uses`/`voucher_max_uses`.
- **Totals are computed, at cent precision.** `grand_total` = Σ line_totals;
  `grand_total_usd` (freight) = `exw_total_usd` + that option's
  `freight_cost_usd`; `exw_total` = qty × unit_price. Recompute; never copy a
  stored total. If a stored/expected total disagrees with the line math, trust
  the line math and flag nothing — your computed sum is the defensible answer.
- **Source precedence for the same field:** for record *values* (amounts,
  dates, codes) the API wins. For *which entity and scope* (and occasionally the
  display name the package should carry), the prompt's explicit instruction
  wins. If the prompt names an `as_of`/current business date, use it for all
  "is it due yet?" comparisons rather than the real clock.

## Output discipline

- Emit only the JSON object. No code fences, no commentary, no trailing text.
- Include every template key; use `null` only where the template allows it.
- Money as numbers with cent precision (e.g. `42480.0` or `42480.00` — both are
  numerically equal; match the template's decimal style if it is consistent).
- Order array items the way the template says (e.g. milestones "ascending by
  milestone_id"; freight AIR then SEA then ROAD as the template lists them).
- Before returning, re-read the template once more and confirm each enum value
  you wrote is a literal member of that field's declared enum set.
