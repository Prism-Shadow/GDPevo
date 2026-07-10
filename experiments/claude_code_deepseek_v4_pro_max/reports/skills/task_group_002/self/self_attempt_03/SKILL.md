# MedBridge Sales Ops API — Transferable SOP

## Environment

All API calls go to `{API_BASE_URL}/api/` where `API_BASE_URL` is provided by the
task runner. When task text mentions `localhost`, `127.0.0.1`, `BASE_URL`, or
`env/setup.sh`, substitute the remote base URL from the runner instead.

## API Endpoint Inventory

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api` | Collection index + endpoint listing |
| GET | `/api/customers` | All customers |
| GET | `/api/customers/<id>` | Single customer |
| GET | `/api/products` | All products |
| GET | `/api/products/<code>` | Single product by `code` |
| GET | `/api/rfqs` | All RFQs |
| GET | `/api/rfqs/<id>` | Single RFQ |
| GET | `/api/quotes` | All quotes |
| GET | `/api/quotes/<id>` | Single quote |
| GET | `/api/freight-quotes` | All freight quotes |
| GET | `/api/freight-quotes/<id>` | Single freight quote |
| GET | `/api/policies` | All business policies |
| GET | `/api/opportunities` | All opportunities |
| GET | `/api/opportunities/<id>` | Single opportunity |
| GET | `/api/invoices` | All invoices |
| GET | `/api/payments` | All payments |
| GET | `/api/revenue-journals` | All revenue recognition journals |
| GET | `/api/events` | All client events |
| GET | `/api/vouchers` | All event vouchers |
| GET | `/api/search?q=<text>` | Full-text search across collections |

**Pattern**: Sign-once, fetch-all. There are no write endpoints — the API is
read-only. Collection endpoints return `{"collection": "...", "count": N,
"records": [...]}`. Single-resource endpoints return the object directly.
Individual invoice fetches by ID are NOT supported — use the collection
`/api/invoices` and filter client-side.

## Task Dispatch: Quote vs. RFQ vs. Reconciliation

Use the top-level entity ID to decide the workflow:

- **`Q-TR-*`** (quote revision): Fetch the quote, its product, the customer,
  all freight records, and policies. Compute EXW total from catalog tiers,
  pair each freight mode, and evaluate validity/risk/reconfirmation.
- **`RFQ-TR-*`** (indicative request): Fetch the RFQ, its requested modules
  (products), the customer, and policies. Compute EXW-only line totals at
  module level — never split into components. Freight is always excluded.
- **`OPP-TR-*`** (opportunity reconciliation): Fetch the opportunity, its
  invoices, payments, revenue journals, customer, linked event, and voucher.
  Reconcile won amount → phase totals → invoice totals → payment totals →
  revenue recognition coverage. Generate accounting and collection follow-ups.

## Catalog Tier Selection (Quantity Brackets)

Every product has a `price_tiers` array. For a given quantity, select the
**single tier where `min_qty <= quantity <= max_qty`**. If `max_qty` is
`null`, the tier extends upward without bound.

```
Example: WC-KIT-A, 360 units
  Tier 1: 1–149   → unit_price 129.50  ✗ (above max)
  Tier 2: 150–299 → unit_price 124.00  ✗ (above max)
  Tier 3: 300–499 → unit_price 118.00  ✓ ← selected
  Tier 4: 500+    → unit_price 114.00  ✗ (below min)
```

The matching tier supplies: `unit_price_usd`, `lead_time_days`,
`shelf_life_months`. The prior quote unit price is **overridden** by the
current catalog tier — the quote's `source_notes` field confirms this rule.

## EXW Total Calculation

```
exw_total_usd = confirmed_quantity × selected_tier.unit_price_usd
grand_total_usd = exw_total_usd + freight.cost_usd   (for each freight mode)
```

All money values are USD with exactly 2 decimal places.

## Freight Record Filtering (Critical — Many Distractors)

The freight collection contains 22+ records. For a given quote, filter:

1. **Match `quote_id`** — only freight belonging to the target quote.
2. **Status must be `"active"`** — discard `"stale"`, `"mismatch"`, or
   anything that is not active.
3. **Verify shipment dimensions** — compare `shipment_cbm` and
   `shipment_weight_kg` across the three real options. Distractor freight
   often has wildly different cbm/weight (e.g., 8.0 cbm vs. 24.0 cbm) or
   belongs to an entirely different quote.
4. **Check `valid_until` against quote date** — a freight record whose
   `valid_until` is before the quote date is stale/invalid regardless of
   status. This is the most important validity gate.

There are typically exactly three valid active freight records per quote
(AIR, SEA, ROAD). Anything beyond that is a distractor.

## Freight Validity and Reconfirmation

- **`valid_until >= quote_date`** → freight is valid on quote date.
- **`valid_until < quote_date`** → freight is stale/expired (mark
  `source_is_stale: true`, flag in warnings).
- **POL-FREIGHT-RECONFIRM**: all freight rates require reconfirmation at
  final order. Set `freight_reconfirmation_required: true` unconditionally
  when freight is included.

## Risk Assessment

Map freight `route_risk` values:

| `route_risk` | risk_level | risk_flag | customs_border_risk |
|---|---|---|---|
| `"low"` | LOW | NONE | LOW |
| `"medium"` | MEDIUM | MEDIUM_BORDER_RISK | MEDIUM |
| `"high"` | HIGH | HIGH_CUSTOMS_RISK | HIGH |

The `risk_notes` field provides human-readable context but does not drive
the structured flags — use `route_risk` for that.

## Recommended Transport Mode

Select the recommended mode by this priority:
1. **Eliminate stale/expired** quotes first.
2. **Prefer lowest risk** (LOW > MEDIUM > HIGH).
3. **Break ties by shortest transit** (transit_days_min ascending).
4. **Consider cold-chain** — if the product requires cold chain and the
   freight supports it, that is a positive signal (but does not override
   risk).

If the road quote is stale with HIGH risk, the recommendation will
typically be AIR (fastest, safest), with SEA as a cheaper alternative.

## Payment Terms Assignment

Do NOT guess payment terms — derive them from policy + customer profile:

| Scenario | Policy | terms_code |
|---|---|---|
| New NGO, no credit history, `is_recurring: false`, `segment: new_ngo` | POL-NEW-CLIENT-PAYMENT | PREPAY_100 |
| Recurring NGO, `is_recurring: true`, `segment: recurring_ngo` | POL-RECURRING-NGO-PAYMENT | NET_30_AFTER_PO |
| Recurring commercial, `is_recurring: true`, `segment: recurring_commercial` | POL-RECURRING-NGO-PAYMENT (adapted) | NET_30_AFTER_PO |
| Implementation services, `payment_profile: MILESTONE_BILLING` | POL-REVREC | MILESTONE_BILLING |

The customer `payment_profile` field provides the fallback. The policy
`terms_code` gives the canonical short code for the template.

## Quote Scope (EXW vs. Freight-Included)

- **Destination present** on quote/RFQ → EXW + freight options (three modes).
- **No destination** (`"Destination pending..."` or similar) → EXW only,
  `freight_excluded: true`, no freight records returned. This is governed by
  POL-INDICATIVE-EXW.
- **Module RFQ granularity** (POL-MODULE-GRANULARITY): quote at module
  product-code level only. Do NOT split into the `components` array from the
  product record. Even if the API shows `component_composition_distractors`,
  those are medical-review metadata — ignore them for quoting.

## Offer Validity

- **POL-QUOTE-VALIDITY**: catalog quote pricing is valid for 30 calendar
  days from `quote_date`. Set `offer_validity_days: 30`.
- Freight validity may be shorter — always use the freight record's
  `valid_until` field, not the 30-day rule.

## Customer Name Resolution

- **Quote/RFQ tasks**: look up the customer by the `customer_id` on the
  quote/RFQ record, then use `customer.name`.
- The customer `id` (e.g., `CUST-HHA`) differs from the `name` (e.g.,
  `HealthHands Alliance`). Always output the human-readable `name`, not
  the ID, when the template asks for customer name.
- Some customer records match the handle in the prompt (`Health Horizon Aid`
  vs. API `HealthHands Alliance`) — trust the API name over the task prompt
  narrative if they differ.

## Opportunity Reconciliation Rules

### Stage Mapping
| API `stage` | Template enum |
|---|---|
| `"closed_won"` | WON |
| `"open"` | OPEN |
| anything else | LOST |

### Milestone Assignment
Each phase in `opportunity.phases` maps to a milestone. The milestone_id
follows the convention MS1, MS2, MS3 in ascending order by phase sequence
(first phase → MS1, second → MS2, third → MS3). Use the `phase_id` for
cross-referencing invoices and journals, but output the MSn form.

### Invoice State
Derive from invoice `status`:
- `"paid"` → PAID
- `"unpaid"` → OPEN
- `"overdue"` → OPEN (treat as open with urgency)
- `"draft"` → VOID (exclude from reconciliation)

### Payment State
Derive from invoice + payment data:
- `paid_amount_usd == amount_usd` → PAID
- `paid_amount_usd > 0 && paid_amount_usd < amount_usd` → PARTIAL
- `paid_amount_usd == 0` → UNPAID

Payments are matched to invoices by `invoice_id`. Sum all payments for the
same invoice if multiple exist (in practice, one payment per invoice).

### Revenue Recognition Status (per milestone)
- **Milestone paid AND revenue journal exists** → RECOGNIZED
- **Milestone paid AND NO revenue journal** → MISSING_REVENUE_JOURNAL (or
  REQUIRED_MISSING depending on template)
- **Milestone unpaid** → NOT_REQUIRED_UNPAID
- **Milestone completion_date is in the future**: still use the same logic;
  if an invoice has been issued and is unpaid, it is NOT_REQUIRED_UNPAID
  regardless of whether the milestone completion date has passed.

### Overall Revenue Recognition
- All paid milestones have journals → COMPLETE_FOR_PAID_MILESTONES
- Any paid milestone lacks a journal → MISSING_FOR_PAID_MILESTONES
- No paid milestones exist → NOT_REQUIRED

### Amount Reconciliation
- `won_amount` must equal the sum of all `phase.amount_usd` values.
- `phase_total_amount` is the sum of all phase amounts.
- `total_paid_amount` is the sum of all payments for this opportunity.
- `outstanding_balance` is the sum of `invoice.outstanding_amount_usd` for
  all invoices linked to this opportunity.

### Accounting Action
When a paid milestone lacks a revenue journal:
- **Action**: `RECORD_REVENUE_MSn` (n = milestone number)
- **Debit**: DEFERRED_REVENUE
- **Credit**: IMPLEMENTATION_SERVICES_REVENUE
- **Amount**: the milestone's `amount_usd`
- **Owner**: ACCOUNTING

When all paid milestones are recognized but unpaid milestones exist:
- **Action**: VERIFY_REVENUE_ONLY
- **Milestone**: NONE

When nothing needs attention:
- **Action**: NO_ACCOUNTING_ACTION

### Collection Action
- **Unpaid + due date is in the future** (relative to business/as-of date) →
  MONITOR_UNPAID_NOT_DUE, owner ACCOUNT_MANAGEMENT
- **Unpaid + due date has passed** → SEND_COLLECTION_NOTICE, owner COLLECTIONS
- **All paid** → NO_COLLECTION_ACTION
- The `amount` is the invoice `outstanding_amount_usd`.
- `contact_name` comes from the opportunity's `contact` field.

### Event and Voucher Handling
- Match event by `opportunity_id` and verify `event_id` matches the task
  prompt.
- Event status from API: `"scheduled"`, `"confirmed"`, `"live"`, `"completed"`,
  `"cancelled"`, `"tentative"`. Use as-is in the template.
- Voucher status from API: `"active"`, `"draft"`, `"expired"`, `"disabled"`.
  Use as-is.
- `voucher_discount` / `discount_amount`: the `discount_percent` from the
  voucher API record.
- `voucher_max_uses`: the `max_redemptions` from the voucher API record.

### Invite Action
- Event is `"scheduled"` and upcoming → SEND_BRIEFING_INVITE
- Event is `"confirmed"` → SEND_BRIEFING_INVITE (or SEND_EVENT_INVITATION
  depending on template enum)
- Event already `"completed"` or `"cancelled"` → NO_INVITE_ACTION
- Owner: ACCOUNT_MANAGEMENT (or EVENTS on some templates — use the template's
  enum values)
- Contact: from event's `primary_contact`

## Known Distractor Patterns

1. **Cross-quote freight**: freight records with a different `quote_id` than
   the target — filter strictly by quote_id.
2. **Stale freight**: `status: "stale"` or `valid_until` before quote date.
   These exist for the correct quote_id but are expired. Flag, don't use.
3. **Mismatch freight**: `status: "mismatch"` — wrong shipment dimensions,
   based on a prior order quantity. Discard.
4. **Wrong-size distractors**: freight with `shipment_cbm` or
   `shipment_weight_kg` that doesn't match the three real modes (look for
   the cluster of three with consistent dimensions).
5. **Component composition distractors**: RFQ records may list
   `component_composition_distractors` — these are medical review notes,
   not line items. Never split a module into components.
6. **Draft invoices**: invoices with `status: "draft"` belong to other
   opportunities — exclude from reconciliation.
7. **Name mismatches**: the task prompt narrative may use a slightly
   different customer name than the API record. Always use the API's
   `customer.name`.

## Date Conventions

- All dates in output: ISO `YYYY-MM-DD`.
- Quote date comes from the quote/RFQ/opportunity record's `quote_date`
  field.
- Business/as-of date: use 2026-06-01 unless the task explicitly sets
  another date.
- `due_date` for milestones: use the invoice `due_date`, or `null` if no
  invoice exists.

## Output Format

Return **only valid JSON** matching the provided `answer_template.json`.
No markdown fences, no explanatory text. Fill every field in the template
with real data — never leave placeholder strings like `"<quote_id>"` or
`"string"`. Use the exact enum values declared in the template comments.

## Quick Reference: Field Sources

| Template field | API source |
|---|---|
| quote_id / rfq_id | `.id` on quote or RFQ |
| customer_id | `.customer_id` on the primary record |
| customer_name | `customer.name` from customer lookup |
| quote_date | `.quote_date` on primary record |
| product_code | `.primary_product_code` or `requested_modules[].product_code` |
| confirmed_quantity | `.confirmed_quantity` or `requested_modules[].quantity` |
| unit_price_usd | matching `price_tiers[N].unit_price_usd` |
| lead_time_days | matching `price_tiers[N].lead_time_days` |
| shelf_life_months | product `shelf_life_months` or tier's `shelf_life_months` |
| article_number | product `.article_number` |
| freight_id | freight `.id` |
| freight_cost_usd | freight `.cost_usd` |
| transit_days | freight `.transit_days_text` |
| valid_until | freight `.valid_until` |
| risk_level | map from freight `.route_risk` |
| payment_terms | policy `terms_code` matching customer profile |
| won_amount | opportunity `.won_amount_usd` |
| stage | map opportunity `.stage` |
| milestone amount | phase `.amount_usd` |
| invoice_state | invoice `.status` mapped |
| payment_state | derived from invoice `paid_amount_usd` vs. `amount_usd` |
| recognition_status | derived from paid + journal existence |
| event_id | event `.id` |
| voucher_code | voucher `.code` |
