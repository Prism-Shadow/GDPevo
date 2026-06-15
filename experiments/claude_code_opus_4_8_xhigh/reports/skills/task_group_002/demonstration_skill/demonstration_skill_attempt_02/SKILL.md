---
name: medbridge-sales-ops
description: >-
  Produce account-ready JSON answers for the MedBridge Sales Ops domain (CRM,
  quotes, freight/logistics decisions, and milestone receivables). Use this
  whenever a task asks you to verify or reconcile MedBridge records against the
  Sales Ops HTTP API and return JSON matching an answer_template.json — including
  catalog-tier quote pricing, EXW + freight decision packages, route/border risk
  and recommended transport mode, module-only RFQ quotes, payment-terms
  selection, or opportunity↔invoice↔payment↔revenue-journal reconciliation with
  collection/event follow-up routing. Trigger it even when the prompt only names
  a quote/opportunity/RFQ id (e.g. "Q-...", "OPP-...", "RFQ-...") and asks for a
  decision package or reconciliation, or mentions freight options, milestones,
  outstanding balance, revenue recognition, vouchers, or follow-up tasks.
---

# MedBridge Sales Ops — Account-Ready JSON

You are filling a fixed JSON answer template from a read-only business API. The
template is the contract: copy its key names, nesting, enum vocabulary, and
example values exactly, and only change the data. The single source of truth is
the MedBridge Sales Ops API. Never invent numbers, dates, or ids — derive every
value from a fetched record and reconcile cross-references before you trust them.

## 0. Always do this first

1. Read `environment_access.md` (or whatever the task calls it) for the base URL.
   It is typically `http://127.0.0.1:8094`, but the runner may inject it as
   `API_BASE_URL` / `BASE_URL` / a `${PORT}`. Confirm with `GET /health`.
2. Read the task prompt AND `input/payloads/answer_template.json`. The template
   tells you the task family and the exact output shape. Identify which family
   (see below) before fetching anything.
3. Fetch by id with detail endpoints (`/api/quotes/<id>`, `/api/opportunities/<id>`,
   etc.) whenever the prompt gives an id — that is the unambiguous record.
4. Output rule (every family): return ONLY the JSON, no markdown fences, no prose.
   Keep money at 2-decimal cent precision, dates as ISO `YYYY-MM-DD`, and preserve
   the template's field order and casing.

## The loose-filter pitfall (read before any list query)

List endpoints accept `?field=value`, but the filter matches the value ANYWHERE
in the (nested) record, so it returns **extra unrelated rows**, including planted
**distractors**. For example `GET /api/freight-quotes?quote_id=Q-...` can return
5 rows when only 3 belong to the quote.

Defensive rule: **fetch the full collection and filter precisely yourself.** Match
on the exact field you mean (e.g. `record["quote_id"] == quote_id`) and then drop
distractors using the cross-checks in each SOP. Distractor records typically have
ids containing `DIS`, `status` of `stale`/`mismatch`, a `valid_until` already
expired, or shipment/quantity dimensions that do not match the governing record.
`GET /api/search?q=<text>` is fine for *finding* an id, never for selecting the
authoritative row.

## Identifying the task family

| Signal in prompt / template | Family | SOP |
| --- | --- | --- |
| Quote id, "freight options", EXW + grand totals, route risk, recommended mode, payment/freight flags | **Freight decision package** | §A |
| RFQ id, "module level", "indicative", "EXW only / freight excluded", line items + grand_total | **Module-only EXW quote** | §B |
| Opportunity id, milestones/phases, invoices, payments, revenue recognition, outstanding balance, event/voucher, follow-up tasks | **Engagement / receivables reconciliation** | §C |

The freight-decision and reconciliation templates vary in field names across
tasks (e.g. `risk_level` vs `customs_border_risk`; `milestones[]` vs
`engagement_reconciliation.milestones[]`). Always bind to the template you were
given. The *logic* below is stable; the field names are whatever the template uses.

## Shared catalog-tier pricing rule (used by §A and §B)

Products carry `price_tiers[]`, each `{min_qty, max_qty, unit_price_usd,
lead_time_days, shelf_life_months?}`. Select the tier whose
`min_qty <= confirmed_quantity <= max_qty`, treating `max_qty == null` as
unbounded (open top tier). The catalog tier **overrides** any
`prior_unit_price_usd` on the quote line — a revision re-prices at the current
tier for the confirmed quantity. `lead_time_days` comes from the selected tier;
`shelf_life_months` is a product-level field. `exw_total = unit_price * quantity`
(then `line_total` / `grand_total` accordingly). Never use the prior price.

---

## §A — Freight decision package (quote + EXW + freight)

Goal: revised EXW pricing for the confirmed quantity, the three current freight
options (one AIR, one SEA, one ROAD) with EXW-plus-freight grand totals, route/
border risk, recommended mode, freight validity/reconfirmation, and payment terms.

1. `GET /api/quotes/<id>` → `customer_id`, `quote_date`, primary product code,
   `confirmed_quantity`. Then fetch the customer and the product.
2. **Price** via the shared catalog-tier rule. `exw_total = unit_price * qty`.
3. **Select the 3 freight rows.** Fetch the full `/api/freight-quotes`
   collection. Keep rows where `quote_id == <this quote>`, then keep exactly the
   legitimate AIR/SEA/ROAD set and drop distractors:
   - Exclude ids containing `DIS` and any `status` of `stale`/`mismatch` **as the
     authoritative option for a mode**, unless the template explicitly wants you
     to *report* a stale option as one of the three (see step 5 — sometimes the
     genuine ROAD option is itself stale and must be shown with a STALE/`source_is_stale`
     flag). Distinguish: a genuine option matches the quote's shipment dimensions
     (same `shipment_cbm`/`shipment_weight_kg` family) and follows the quote's
     product token in its id (e.g. `FR-WC-*` for the WC quote); a distractor has
     mismatched dimensions or an unrelated id.
   - There should be exactly one row per mode after filtering. If two rows claim
     the same mode, the genuine one matches shipment size and is not a `DIS`/stale
     benchmark.
4. **Per-option fields** (map to whatever the template names them):
   - `freight_cost = cost_usd`; `grand_total = exw_total + freight_cost`.
   - `transit_days`: copy the template's format — some templates want the text
     `"4-6 days"` (use `transit_days_text`), others want `"4-6"` (strip " days")
     or `min-max`. Match the template's example exactly.
   - `valid_until = valid_until`.
   - Risk: `route_risk` is lowercase in the API. Map to the template's enum,
     usually UPPERCASE: `low→LOW`, `medium→MEDIUM`, `high→HIGH`. If the template
     has a separate `risk_flag`, use `NONE` for low risk and a border flag such as
     `MEDIUM_BORDER_RISK` / `HIGH_BORDER_RISK` when `risk_notes` mention border/
     customs risk at that level (mirror the example value in the template).
   - Validity status (if the template has one): `VALID` when
     `valid_until >= quote_date` and `status == active`; `STALE`/`EXPIRED` (and
     `source_is_stale = true`) when `status == stale` or `valid_until < quote_date`.
5. **Recommended mode** — feasibility/validity first, then cost, then risk:
   - Consider only options that are VALID on the quote date (not stale, not
     expired) AND carry acceptable risk (avoid HIGH border/customs risk).
   - Among the remaining options, recommend the **lowest grand_total**.
   - A cheaper option that is stale/expired or HIGH-risk does NOT win — exclude it
     first, then compare cost. (E.g. a stale, high-risk ROAD that happens to be a
     few dollars cheaper must not be recommended; the cheapest *valid low-risk*
     mode wins instead.)
   - Cold-chain note: if the product has `cold_chain_required: true`, a mode whose
     freight row lacks `cold_chain_support` is not a safe recommendation.
6. **Flags / policy:**
   - `freight_reconfirmation_required = true` always (policy POL-FREIGHT-RECONFIRM:
     freight rates must be reconfirmed at final order).
   - `all_freight_options_valid_on_quote_date`: true only if all three reported
     options have `valid_until >= quote_date`.
   - `road_quote_invalid_or_stale` (if present): true when the ROAD option is
     expired/stale.
   - `quote_basis`: for these quotes it is EXW-plus-freight, e.g.
     `EXW_PLUS_FREIGHT_OPTIONS` (match the template's spelling/casing).
   - Payment terms and customer policy: see §D.
   - `freight_warning` (free-text, if present): state that rates need
     reconfirmation at final order, and name any expired/high-risk option with its
     expiry date and risk so it is not used without a fresh quote. Keep it factual.

---

## §B — Module-only EXW quote (RFQ)

Goal: indicative EXW quote at module/SKU line level, freight excluded.

1. `GET /api/rfqs/<id>` → `customer_id`, `quote_date`, and `requested_modules[]`
   (`product_code` + `quantity`). Fetch the customer and each requested product.
2. **Quote at the requested line level only.** RFQs include
   `component_composition_distractors` / "for medical review only" notes. Do NOT
   split modules into component SKUs and do NOT add component lines (policy
   POL-MODULE-GRANULARITY). One output line per requested module, in the requested
   order, using the requested quantity.
3. Per line: `unit_price` from the catalog tier for that module's quantity,
   `article_number` and `shelf_life_months` from the product, `lead_time_days`
   from the selected tier, `line_total = unit_price * quantity`.
4. `grand_total = sum(line_total)`. `freight_excluded = true`, `quote_basis =
   EXW_ONLY` (no destination ⇒ EXW only, policy POL-INDICATIVE-EXW).
5. Controls: `offer_validity_days = 30` (POL-QUOTE-VALIDITY, catalog pricing valid
   30 days). `who_documentation_required = true` for these humanitarian health
   kits unless the template/prompt says otherwise. Payment terms per §D (a new NGO
   ⇒ `PREPAY_100`).

---

## §C — Engagement / receivables reconciliation

Goal: confirm the won opportunity total agrees with its milestone phases;
summarize invoice/payment/outstanding/revenue-recognition state per milestone;
include the related event + voucher; and route the required follow-up tasks.

1. `GET /api/opportunities/<id>` → `stage`, `won_amount_usd`, `contact`,
   `outstanding_amount_usd`, and `phases[]` (each has `phase_id`, `amount_usd`,
   `invoice_id`, `completion_date`). Map `stage`: `closed_won → WON`, open/
   proposal/negotiation → `OPEN`, `closed_lost → LOST`.
2. **Match check:** `phase_total = sum(phase.amount_usd)`.
   `opportunity_matches_(milestones|phase_total) = (won_amount == phase_total)`.
3. **Per milestone** (one per phase, ordered ascending; if the template labels them
   `MS1/MS2/MS3`, assign by phase order). Cross-reference precisely (loose-filter
   pitfall): from the full `/api/invoices`, `/api/payments`, `/api/revenue-journals`
   collections, pick the rows whose `phase_id`/`invoice_id`/`opportunity_id`
   match THIS phase. Per milestone:
   - `amount / invoice_total = phase.amount_usd` (== matching invoice `amount_usd`).
   - `invoice_state` from the invoice `status` (`paid→PAID`, `unpaid/overdue/
     draft→OPEN`, etc. — map to the template's enum).
   - `paid_amount = sum(matching posted payments)` (or invoice `paid_amount_usd`).
   - `payment_state`: PAID if paid == amount, PARTIAL if 0 < paid < amount, UNPAID
     if paid == 0.
   - `due_date`: this is the load-bearing rule — **null out the due date for any
     PAID milestone**; only an unpaid/outstanding milestone keeps its invoice
     `due_date`. (Templates default paid due_date to null.)
   - `recognition_status` (revenue recognition; policy POL-REVREC):
     - `RECOGNIZED` — milestone is paid AND a revenue journal exists for it.
     - `MISSING_REVENUE_JOURNAL` / `REQUIRED_MISSING` — milestone is paid (and
       complete) but NO revenue journal exists. This is a finding that drives an
       accounting action.
     - `NOT_REQUIRED_UNPAID` — milestone is unpaid; recognition not yet required.
4. **Account totals:** `total_paid = sum(paid across milestones)`;
   `outstanding_balance = sum(amount - paid)` (should equal the opportunity's
   `outstanding_amount_usd`; if it disagrees, recompute from milestones and trust
   the reconciled figure). Carry the primary `contact` from the opportunity for
   all follow-up routing.
5. **Revenue-recognition rollup** (if the template has a block):
   - `COMPLETE_FOR_PAID_MILESTONES` — every paid milestone has a journal.
   - `MISSING_FOR_PAID_MILESTONES` — at least one paid milestone lacks a journal.
   - `recognized_milestones` = paid+journaled; `missing_required_milestones` =
     paid but unjournaled; `recognized_amount` = sum of journaled amounts.
6. **Follow-up / action routing** (use the template's exact enums):
   - **Accounting action:** if a paid milestone is missing its journal →
     `RECORD_REVENUE_<MSx>` for that milestone, `amount = milestone amount`,
     `debit_account = DEFERRED_REVENUE`, `credit_account =
     IMPLEMENTATION_SERVICES_REVENUE`, `owner_queue = ACCOUNTING`. If all paid
     milestones are already recognized → `VERIFY_REVENUE_ONLY`. If nothing is
     paid/recognizable → `NO_ACCOUNTING_ACTION` (accounts/owner `NONE`).
   - **Collection action** for the earliest unpaid milestone, compared to the
     business/as-of date (from the prompt; reconciliation tasks use the stated
     current date, e.g. `2026-06-01`):
     - unpaid and due_date in the future → `MONITOR_UNPAID_NOT_DUE`
       (`COLLECT_UNPAID_MILESTONE` as the next action where the template uses that
       enum), owner `ACCOUNT_MANAGEMENT`, due_date = invoice due_date.
     - unpaid and due_date today/past (overdue) → `SEND_COLLECTION_NOTICE`,
       owner `COLLECTIONS`.
     - no unpaid milestone → `NO_COLLECTION_ACTION`.
     The collection task is tied to the opportunity's contact and customer.
   - **Event / voucher invite:** include the linked event and voucher.
     - Event status maps from the event `status` (`scheduled→SCHEDULED`,
       `confirmed→SCHEDULED` or the template's "ready to invite" value,
       `live→ACTIVE`, `completed→COMPLETED`, `cancelled→CANCELLED`). Read the
       template enum and pick the matching value.
     - Voucher: `voucher_code` = code; `discount`/`discount_amount` = the numeric
       `discount_percent` value rendered as a number (e.g. 100 → 100.00, 50 →
       50.00); `max_uses` = `max_redemptions`; `voucher_status` from voucher
       `status` (`active→ACTIVE`).
     - Invite action: if the event is upcoming/active and the invite has not been
       sent → `SEND_EVENT_INVITATION` / `SEND_BRIEFING_INVITE`, owner
       `ACCOUNT_MANAGEMENT`, carrying event_id, voucher_code, contact, customer.
   - **Follow-up due dates:** a collection task is due on the unpaid milestone's
     due_date. An event-invitation task is due shortly *before* the event date
     (lead time) — match the template's convention; do not invent a date the
     records cannot support.

For the precise field-name→API-field mapping, enum vocabularies, and worked
derivations for each template variant, read
`references/field_mappings_and_enums.md`.

---

## §D — Payment terms & customer policy (all quote families)

Derive from the customer record + policies, not from guesswork:
- New NGO / first order / no approved credit (`segment: new_ngo`,
  `is_recurring: false`, `payment_profile: NEW_CLIENT_REVIEW`) → `PREPAY_100`
  (POL-NEW-CLIENT-PAYMENT) and customer policy `NEW_CLIENT` / `NEW_NGO`.
- Recurring NGO or recurring commercial with net-after-PO grant terms
  (`is_recurring: true`, `payment_profile: NET_30_AFTER_PO`) → `NET_30_AFTER_PO`
  (POL-RECURRING-NGO-PAYMENT) and customer policy `RECURRING_NGO` (or the
  segment-appropriate value). Restricted grant terms can override to stricter.
- When in doubt, the customer's `payment_profile` field is the authoritative
  terms code; confirm it against the matching policy `terms_code`.

Use the controlled strings exactly as the template/policies spell them
(`PREPAY_100`, `NET_30_AFTER_PO`, `EXW_ONLY`, `EXW_PLUS_FREIGHT_OPTIONS`, etc.).

---

## Common misjudgments — do NOT do these

- Do NOT trust loose list filters; they include distractors (`FR-DIS-*`, stale,
  mismatched shipment size). Always cross-check the governing id and dimensions.
- Do NOT use the quote line's `prior_unit_price_usd`. Re-price at the current
  catalog tier for the confirmed quantity.
- Do NOT split module RFQ lines into components, and do NOT add component lines —
  the `component_composition_distractors` are review-only.
- Do NOT recommend a freight mode just because it is cheapest. Exclude stale/
  expired/HIGH-risk (and cold-chain-incapable for cold-chain products) options
  first; recommend the cheapest *valid, low-risk* mode. Keep feasibility/validity
  separate from cost.
- Do NOT keep a `due_date` on a PAID milestone — null it. Only unpaid/outstanding
  milestones carry a due date.
- Do NOT mark a paid milestone `RECOGNIZED` unless an actual revenue journal row
  exists for it; a paid-but-unjournaled milestone is `MISSING_REVENUE_JOURNAL`
  and drives a `RECORD_REVENUE` accounting action.
- Do NOT add freight, insurance, or duty to an EXW-only / indicative quote.
- Do NOT emit markdown, comments, or prose around the JSON, and do NOT rename,
  reorder, or drop template keys. Match enum casing exactly.
- Do NOT compute risk text or border flags from the mode name; derive from the
  freight row's `route_risk` and `risk_notes`.
