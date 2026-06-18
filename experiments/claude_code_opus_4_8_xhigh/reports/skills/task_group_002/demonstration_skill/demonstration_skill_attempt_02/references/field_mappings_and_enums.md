# MedBridge field mappings, enums, and worked derivations

Reference for filling the answer templates precisely. Always bind to the template
you were handed; the names below are the variants seen across this domain. When a
template's example value differs from what is here, the template wins — copy its
spelling, casing, and format.

## Table of contents
1. API record shapes (the fields you actually read)
2. Controlled enum vocabularies
3. Field-by-field mapping per task family
4. Derivation walkthrough (method, not memorized answers)
5. Edge cases & precedence rules

---

## 1. API record shapes

**product** (`/api/products/<code>`): `code`, `article_number`, `name`,
`family`, `unit`, `cold_chain_required`, `shelf_life_months`, `weight_kg`, `cbm`,
`components[]`, and `price_tiers[]` of `{min_qty, max_qty (null=unbounded),
unit_price_usd, lead_time_days, lead_time_weeks}`.

**quote** (`/api/quotes/<id>`): `customer_id`, `quote_date`, `currency`,
`incoterm`, `quote_type`, `destination`, `confirmed_quantity`,
`primary_product_code`, `line_items[]` with `confirmed_quantity`,
`prior_quote_quantity`, `prior_unit_price_usd` (IGNORE the prior price),
`product_code`, `customer_note`. `source_notes` often hints the intended tier and
which freight row is stale — useful as a sanity check, not as the data source.

**rfq** (`/api/rfqs/<id>`): `customer_id`, `quote_date`, `received_date`,
`incoterm_requested`, `destination` (may be "pending"), `request_type`,
`requested_modules[]` (`product_code`, `quantity`), and
`component_composition_distractors[]` (review-only; never quote these).

**freight-quote** (`/api/freight-quotes`): `id`, `quote_id`, `mode`
(air/sea/road, lowercase), `cost_usd`, `currency`, `origin`, `destination`,
`forwarder`, `route_risk` (low/medium/high), `risk_notes`, `status`
(active/stale/mismatch), `valid_until`, `quote_date`, `transit_days_min/max`,
`transit_days_text` (e.g. "4-6 days"), `shipment_cbm`, `shipment_weight_kg`,
`cold_chain_support`.

**customer** (`/api/customers/<id>`): `name`, `customer_type`, `segment`
(new_ngo / recurring_ngo / recurring_commercial / ...), `is_recurring`,
`payment_profile` (NEW_CLIENT_REVIEW / NET_30_AFTER_PO / ...), `grant_terms`,
`status`, `contacts[]`, `region`, `country`.

**opportunity** (`/api/opportunities/<id>`): `stage` (closed_won / proposal /
negotiation / closed_lost), `won_amount_usd`, `won_date`, `outstanding_amount_usd`,
`contact`, `owner`, `phases[]` (`phase_id`, `name`, `amount_usd`,
`completion_date`, `invoice_id`).

**invoice** (`/api/invoices`): `id`, `invoice_number`, `customer_id`,
`opportunity_id`, `phase_id`, `phase_name`, `amount_usd`, `paid_amount_usd`,
`outstanding_amount_usd`, `status` (paid/unpaid/overdue/draft), `issue_date`,
`due_date`, `billing_type`.

**payment** (`/api/payments`): `id`, `invoice_id`, `opportunity_id`,
`customer_id`, `amount_usd`, `payment_date`, `method`, `status` (posted),
`reference`.

**revenue-journal** (`/api/revenue-journals`): `id`, `invoice_id`, `phase_id`,
`opportunity_id`, `amount_usd`, `debit_account` ("Deferred Revenue"),
`credit_account` ("Implementation Services Revenue"), `posted_date`, `status`,
`memo`. Presence of a row for a phase == that milestone's revenue is recognized.

**event** (`/api/events`): `id`, `customer_id`, `opportunity_id`, `name`,
`event_date`, `status` (scheduled/confirmed/live/completed/tentative/cancelled),
`primary_contact`, `voucher_code`, `follow_up_owner`.

**voucher** (`/api/vouchers`): `code`, `customer_id`, `opportunity_id`,
`event_id`, `description`, `discount_percent`, `max_redemptions`,
`redemptions_used`, `status` (active), `valid_until`.

---

## 2. Controlled enum vocabularies

These are the values the templates expect. Use the template's own list when it
declares one inline (the template is authoritative); these are the common forms.

- **quote_basis:** `EXW`, `EXW_ONLY`, `EXW_PLUS_FREIGHT_OPTIONS`.
- **payment_terms / terms_code:** `PREPAY_100`, `NET_30_AFTER_PO`.
- **customer_policy:** `NEW_CLIENT` / `NEW_NGO`, `RECURRING_NGO`,
  `RECURRING_COMMERCIAL` (use what the template/segment implies).
- **transport mode:** `AIR`, `SEA`, `ROAD` (UPPERCASE; API is lowercase).
- **risk_level / customs_border_risk:** `LOW`, `MEDIUM`, `HIGH`.
- **risk_flag:** `NONE` (low), `MEDIUM_BORDER_RISK`, `HIGH_BORDER_RISK`.
- **validity_status:** `VALID`, `STALE` (or `EXPIRED`).
- **opportunity stage:** `WON`, `OPEN`, `LOST`.
- **invoice_state:** `PAID`, `OPEN`, `VOID`, `UNKNOWN`.
- **payment_status / payment_state:** `PAID`, `PARTIAL`, `UNPAID`, `UNKNOWN`.
- **recognition_status (per milestone):** `RECOGNIZED`,
  `MISSING_REVENUE_JOURNAL` / `REQUIRED_MISSING`, `NOT_REQUIRED_UNPAID`,
  `UNKNOWN`.
- **recognition rollup:** `COMPLETE_FOR_PAID_MILESTONES`,
  `MISSING_FOR_PAID_MILESTONES`, `NOT_REQUIRED`.
- **primary_accounting_action / accounting action:** `RECORD_REVENUE_MS<n>`,
  `VERIFY_REVENUE_ONLY`, `NO_ACCOUNTING_ACTION`.
- **accounting debit_account:** `DEFERRED_REVENUE`, `ACCOUNTS_RECEIVABLE`,
  `CASH`, `NONE`. **credit_account:** `IMPLEMENTATION_SERVICES_REVENUE`,
  `DEFERRED_REVENUE`, `ACCOUNTS_RECEIVABLE`, `NONE`.
- **collection action / next_action:** `MONITOR_UNPAID_NOT_DUE`,
  `SEND_COLLECTION_NOTICE`, `COLLECT_UNPAID_MILESTONE`, `NO_COLLECTION_ACTION`.
- **event_status:** `SCHEDULED`, `ACTIVE`, `COMPLETED`, `CANCELLED`, `UNKNOWN`.
- **voucher_status:** `ACTIVE`, `DRAFT`, `EXPIRED`, `DISABLED`, `UNKNOWN`.
- **invite_action / next_action:** `SEND_EVENT_INVITATION`,
  `SEND_BRIEFING_INVITE`, `VERIFY_INVITE_SENT`, `NO_INVITE_ACTION`.
- **owner_queue:** `ACCOUNTING`, `ACCOUNT_MANAGEMENT`, `COLLECTIONS`, `EVENTS`,
  `NONE`.
- **task_type:** `COLLECTION`, `EVENT_INVITATION`.

---

## 3. Field-by-field mapping per family

### Freight decision package
| Template field (any variant) | API source / rule |
| --- | --- |
| quote_id / customer_id / quote_date / product_code / confirmed_quantity | quote record |
| unit_price_usd | selected catalog tier `unit_price_usd` |
| catalog_tier.{min,max}_quantity | selected tier `min_qty` / `max_qty` |
| lead_time_days | selected tier `lead_time_days` |
| shelf_life_months | product `shelf_life_months` |
| exw_total_usd | unit_price * confirmed_quantity |
| freight_id / mode | freight row `id` / UPPER(`mode`) |
| freight_cost_usd | freight `cost_usd` |
| transit_days | `transit_days_text` or `min-max` — copy template format |
| valid_until | freight `valid_until` |
| risk_level / customs_border_risk | UPPER(`route_risk`) |
| risk_flag | NONE if low; MEDIUM/HIGH_BORDER_RISK if border/customs risk noted |
| validity_status / source_is_stale | VALID vs STALE per status & valid_until ≥ quote_date |
| grand_total_usd | exw_total + freight_cost |
| recommended_mode | cheapest VALID, low-risk, cold-chain-OK mode |
| freight_reconfirmation_required | always true |
| all_freight_options_valid_on_quote_date | all 3 valid_until ≥ quote_date |
| road_quote_invalid_or_stale | ROAD option expired/stale |
| quote_basis | EXW_PLUS_FREIGHT_OPTIONS |
| payment_terms / customer_policy | §D |

### Module-only EXW quote
| Template field | API source / rule |
| --- | --- |
| rfq_id / customer_id / quote_date / currency | rfq record |
| quote_basis | EXW_ONLY |
| line product_code / article_number / shelf_life_months | product record |
| line quantity | requested module quantity |
| line unit_price | tier price for that quantity |
| line lead_time_days | selected tier |
| line_total | unit_price * quantity |
| grand_total | sum(line_total) |
| freight_excluded | true |
| payment_terms | §D (new NGO ⇒ PREPAY_100) |
| offer_validity_days | 30 |
| who_documentation_required | true |

### Reconciliation
| Template field | API source / rule |
| --- | --- |
| stage | map opportunity `stage` |
| won_amount | opportunity `won_amount_usd` |
| phase_total_amount | sum(phase `amount_usd`) |
| opportunity_matches_* | won_amount == phase_total |
| milestone amount/invoice_total | phase amount == invoice `amount_usd` |
| invoice_state | invoice `status` mapped |
| paid_amount | sum posted payments for that invoice |
| payment_state | PAID/PARTIAL/UNPAID by paid vs amount |
| due_date | invoice `due_date`, **null if milestone PAID** |
| recognition_status | revenue-journal presence + paid state |
| total_paid_amount | sum paid across milestones |
| outstanding_balance | sum(amount - paid); cross-check opp `outstanding_amount_usd` |
| primary_contact / contact | opportunity `contact` |
| accounting_action | see §C step 6 |
| collection_task | earliest unpaid milestone vs as-of date |
| event_id / event_status | event record |
| voucher_code / discount / max_uses | voucher `code` / `discount_percent` (as number) / `max_redemptions` |
| invite_action | SEND_* if upcoming & not sent |

---

## 4. Derivation walkthrough (method, not memorized answers)

These show the *procedure* on the structure of the data. Re-run the procedure on
whatever ids the new task gives you — do not reuse any number below.

**Tier pick:** product has tiers `[1-149], [150-299], [300-499], [500+]`. For a
confirmed qty of 360, `300 <= 360 <= 499` selects the third tier; take its
`unit_price_usd` and `lead_time_days`. `exw_total = price * 360`. The prior line
price is irrelevant.

**Freight set + recommendation:** pull all freight rows, keep `quote_id ==` the
quote and drop `FR-DIS-*`/stale/wrong-shipment-size rows, leaving one AIR, one
SEA, one ROAD. Compute each `grand_total = exw_total + cost_usd`. Mark each VALID
(active and `valid_until >= quote_date`) or STALE. Drop STALE and HIGH-risk from
recommendation candidates; among the rest recommend the lowest grand_total. A
cheaper ROAD that is stale/high-risk loses to a valid low-risk SEA even if SEA
costs more.

**Reconciliation:** for each phase, find its invoice (by `phase_id`/`invoice_id`),
its payments (by `invoice_id`, `status == posted`), and its revenue journal (by
`phase_id`/`invoice_id`). A phase that is invoiced+paid but has NO journal is the
"missing revenue" finding → recognition `MISSING_REVENUE_JOURNAL`, and the
primary accounting action is `RECORD_REVENUE_<that MS>` (debit DEFERRED_REVENUE,
credit IMPLEMENTATION_SERVICES_REVENUE, queue ACCOUNTING). Paid milestones get
`due_date = null`. The unpaid milestone keeps its invoice due_date; compare it to
the as-of date — future ⇒ MONITOR_UNPAID_NOT_DUE, today/past ⇒
SEND_COLLECTION_NOTICE. Outstanding balance = sum of unpaid invoice amounts and
should match the opportunity's `outstanding_amount_usd`.

**Event/voucher:** the event linked to the opportunity gives `event_id`,
`event_date`, status; its voucher gives `voucher_code`, `discount_percent` (output
as a number, e.g. 100 → 100.00), `max_redemptions` → `max_uses`. If the event is
upcoming, raise a SEND_*_INVITE task tied to the opportunity contact and customer.

---

## 5. Edge cases & precedence

- **Source/date precedence:** a record's own `status`/`valid_until` beats any
  narrative hint. A freight row marked `stale` or expired before the quote date is
  not usable regardless of cost. `source_notes` on a quote is a hint to confirm,
  not a data source.
- **Feasibility vs risk vs cost (recommendation ordering):** (1) drop infeasible/
  invalid (stale, expired, cold-chain-incapable for cold-chain product), (2) drop
  unacceptable risk (HIGH border/customs), (3) among survivors choose lowest cost.
  Report risk and validity honestly on every option even if it is not recommended.
- **Paid-milestone due-date nulling:** never carry a due_date once paid; due dates
  exist to drive collection, which a paid milestone does not need.
- **Revenue-recognition state:** recognition requires BOTH paid/complete AND a
  posted journal. Paid-without-journal ⇒ action to record it; unpaid ⇒ not
  required yet (it stays outstanding and drives collection when due/overdue).
- **Action priority:** an accounting gap (missing journal on a paid milestone) is
  the primary accounting action; collection handling is separate and keyed to the
  earliest unpaid milestone; event invites are a separate track keyed to the
  upcoming event. Keep the three tracks distinct in the output.
- **Number formatting:** money to 2 decimals; integers where the template uses
  integers (`max_uses`, `quantity`, `lead_time_days`). Voucher discount is the
  numeric percent value, not a string and not divided by 100.
- **Distractor tells:** ids containing `DIS`; `status` `stale`/`mismatch`;
  `valid_until` before quote_date; shipment cbm/weight that don't match the real
  shipment for the quote; an unrelated `quote_id`/`opportunity_id` surfaced only
  by a loose filter.
