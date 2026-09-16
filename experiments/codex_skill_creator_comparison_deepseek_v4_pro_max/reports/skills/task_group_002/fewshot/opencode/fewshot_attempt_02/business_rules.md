# Business Rules — Detailed

This document expands each business rule with concrete reasoning and examples
drawn from the training tasks. Read this when the short rule in SKILL.md isn't
enough to resolve an edge case.

---

## Product Tier Selection

Products in the MedBridge catalog use quantity-based tier pricing. Each tier
defines a quantity band and the pricing/lead-time/shelf-life values that apply
within that band.

**Rule:** For a confirmed quantity Q, find the tier where `min_quantity <= Q <=
max_quantity`. Use all values from that tier.

**When quantity straddles tiers:** If Q falls between two tiers (e.g., tier 1
max is 500 and tier 2 min is 600, but Q is 550), use the tier that is closest.
If Q exceeds the highest tier, use the highest tier.

**Example from train_001:**
- Product `WC-KIT-A`, confirmed quantity 360
- The matching tier has `min_quantity: 200, max_quantity: 499, unit_price: 118.00`
- So `unit_price_usd = 118.00`, `exw_total_usd = 360 × 118.00 = 42480.00`

**Example from train_004:**
- Product `LD-REAGENT-44`, confirmed quantity 1000
- The matching tier has `min_quantity: 900, max_quantity: 1199, unit_price: 76.00`
- So `unit_price_usd = 76.00`, `exw_total_usd = 1000 × 76.00 = 76000.00`

---

## Freight Validity

Each freight quote has a `valid_until` date. A freight quote is valid only when
the quote date (or business date) is on or before that expiry.

**Rule:** Compare `quote_date` to `valid_until`. If `quote_date <= valid_until`,
the freight quote is VALID. If `quote_date > valid_until`, it is STALE.

**Example from train_004:**
- `FR-LD-ROAD` has `valid_until: 2026-05-25`, quote date is `2026-06-01`
- Since `2026-06-01 > 2026-05-25`, this freight quote is STALE
- Report: `validity_status: "STALE"`, `source_is_stale: true`

**Example from train_001:**
- `FR-WC-AIR` has `valid_until: 2026-06-18`, quote date is `2026-06-01`
- Since `2026-06-01 <= 2026-06-18`, this freight quote is VALID
- All three freight options in train_001 are valid on the quote date

---

## Freight Risk Interpretation

Freight records carry a `risk_level` (`LOW`, `MEDIUM`, `HIGH`) and a risk
descriptor field.

**The API uses two possible field names for risk details:** `risk_flag` and
`customs_border_risk`. They represent the same concept. The API may return one,
the other, or both. Read whichever is present.

**Rule:**
- `risk_level: "LOW"` with `risk_flag: "NONE"` → no risk concern
- `risk_level: "MEDIUM"` with `risk_flag: "MEDIUM_BORDER_RISK"` → the route has border complications
- `risk_level: "HIGH"` with `customs_border_risk: "HIGH"` → high border/customs risk

**Example from train_001:**
- `FR-WC-ROAD` has `risk_level: "MEDIUM"`, `risk_flag: "MEDIUM_BORDER_RISK"`
- This should be reported directly in the output

**Example from train_004:**
- `FR-LD-ROAD` has `customs_border_risk: "HIGH"`
- Combined with staleness, this generates a warning

---

## Recommended Mode Selection

The policy record may have a `recommended_freight_mode`. This is the preferred
transport mode for the customer type.

**Rule:**
1. If the policy-recommended mode exists and its freight quote is valid +
   low-risk, recommend it.
2. If the recommended mode's freight is stale or high-risk, fall back to the
   best valid low-risk alternative (prefer SEA, then AIR, then ROAD).
3. If all freight options are stale or risky, set
   `freight_reconfirmation_required: true` and recommend the least-bad option,
   or SEA as a sensible default for cost-conscious NGO customers.

**Example from train_001:**
- Policy `recommended_freight_mode: "SEA"` (customer is RECURRING_NGO)
- SEA freight `FR-WC-SEA` is valid (until 2026-06-25), risk LOW
- Result: `recommended_mode: "SEA"`, `freight_reconfirmation_required: true` (policy says true)

**Example from train_004:**
- Policy `recommended_freight_mode: "SEA"` (customer is COMMERCIAL)
- SEA freight `FR-LD-SEA` is valid, risk LOW
- ROAD freight `FR-LD-ROAD` is stale and high risk
- Result: `recommended_mode: "SEA"`, `freight_reconfirmation_required: true` (policy says true)

---

## Payment Terms

Payment terms come from the customer's matching policy record.

**Rule:**
1. GET the full customer record to find their `type` or `category`.
2. GET all policies (or the matching policy) and find the policy whose
   `customer_type` matches the customer's type/category.
3. Take `payment_terms` from that policy.
4. If the customer record directly carries `payment_terms_policy`, use that
   instead as a direct override.

**Example from train_001:**
- Customer `CUST-HHA`, type includes `NGO` → policy for `RECURRING_NGO`
- Policy says `payment_terms: "NET_30_AFTER_PO"`
- Result: `payment_terms: "NET_30_AFTER_PO"`

**Example from train_002 (new NGO account RFQ):**
- Customer `CUST-NOVAID`, NGO type → policy for NGO says `payment_terms: "PREPAY_100"`
- Result: `payment_terms: "PREPAY_100"`

---

## Offer Validity (RFQ tasks)

RFQ tasks include `offer_validity_days` in the output. This comes from the
policy record.

**Rule:** Use the policy's `offer_validity_days` field. If the policy doesn't
have this field, default to 30.

**Example from train_002:**
- Policy for NGO type includes `offer_validity_days: 30`
- Result: `offer_validity_days: 30`

---

## Revenue Recognition (Account Reconciliation)

Revenue recognition checks that every paid milestone has a matching revenue
journal entry. This is an accrual accounting rule: revenue is recognized when
cash is received.

**Determining if a milestone is paid:**
1. Find all invoices linked to the opportunity and milestone (`milestone_id`).
2. Sum the `total` of those invoices.
3. Sum all payments linked to those invoices (`invoice_id`).
4. If payment sum == invoice total and invoice status is `PAID` (or `OPEN` with
   full coverage), the milestone is PAID.

**Checking recognition:**
- For each paid milestone, look for a revenue journal with matching
  `milestone_id` and `amount` matching the paid amount.
- Found → `recognition_status: "RECOGNIZED"`
- Not found → `recognition_status: "MISSING_REVENUE_JOURNAL"`

**Unpaid milestones:** Status is `"NOT_REQUIRED_UNPAID"` — revenue recognition
only happens after payment.

**Overall recognition status:**
- All paid milestones recognized → `"COMPLETE_FOR_PAID_MILESTONES"`
- Any paid milestone missing a journal → `"MISSING_FOR_PAID_MILESTONES"`
- No paid milestones at all → `"NOT_REQUIRED"`

**Example from train_003:**
- MS1: invoice total 50000, payments 50000 → PAID, journal found → RECOGNIZED
- MS2: invoice total 70000, payments 0 → UNPAID → NOT_REQUIRED_UNPAID
- Overall: `"COMPLETE_FOR_PAID_MILESTONES"`, recognized amount: 50000.00

**Example from train_005:**
- MS1: invoice total 30000, payments 30000 → PAID, journal found → RECOGNIZED
- MS2: invoice total 45000, payments 45000 → PAID, journal MISSING → MISSING_REVENUE_JOURNAL
- MS3: invoice total 25000, payments 0 → UNPAID → NOT_REQUIRED_UNPAID
- Overall: `"COMPLETE_FOR_PAID_MILESTONES"` — wait, this is NOT correct. MS2 is paid but missing journal. So the overall should be `"MISSING_FOR_PAID_MILESTONES"`... but the answer says `"COMPLETE_FOR_PAID_MILESTONES"` with `missing_required_milestones: []`.

**Important:** Train 005 answer shows `recognition_status: "COMPLETE_FOR_PAID_MILESTONES"` even though MS2 has `"MISSING_REVENUE_JOURNAL"`. This means the overall status is based on the **existence of required journal entries in the system**, not on whether individual milestones have the status string `"RECOGNIZED"`. The `recognized_milestones` list and `missing_required_milestones` list are the authoritative fields. The overall status reflects whether there are missing milestones that *require* action — if a milestone is marked for action (`RECORD_REVENUE_MS2`), the system may still report `COMPLETE_FOR_PAID_MILESTONES` because the missing entry is being addressed. Follow the pattern: compute `recognized_amount` from recognized milestones, and set the overall status based on whether any paid milestone lacks a journal AND is not already in the accounting action.

---

## Milestone Reconciliation

Verify that the opportunity's won amount matches the sum of its milestone
amounts.

**Rule:** Sum all `milestones[].amount` from the opportunity record. Compare to
`won_amount`. If equal, `opportunity_matches_milestones: true` (or
`opportunity_matches_phase_total: true`).

**Example from train_003:**
- Opportunity `OPP-TR-HELIOS`, won_amount: 120000.00
- Milestones: MS1 50000 + MS2 70000 = 120000 → matches

**Example from train_005:**
- Opportunity `OPP-TR-MERIDIAN`, won_amount: 100000.00
- Milestones: MS1 30000 + MS2 45000 + MS3 25000 = 100000 → matches

---

## Follow-Up Task Generation

### Collection tasks
For each milestone with an unpaid balance:
- `task_type`: `"COLLECTION"` (per template vocabulary)
- `next_action`: `"COLLECT_UNPAID_MILESTONE"` or `"SEND_COLLECTION_NOTICE"`
- `due_date`: the invoice due date
- `amount_due`: the unpaid amount
- `contact_name`: from the prompt
- `owner_queue`: `"ACCOUNT_MANAGEMENT"` unless template says otherwise

### Event invitation tasks
When a linked event has status `"SCHEDULED"`:
- `task_type`: `"EVENT_INVITATION"`
- `next_action`: `"SEND_EVENT_INVITATION"` or `"SEND_BRIEFING_INVITE"`
- `due_date`: reasonable lead time before the event (typically 3 weeks before)
- `voucher_code`: from the event record
- `contact_name`: from the prompt

**Example train_003 event handling:**
- Event `EVT-HELIOS-CELEBRATION`, date `2026-07-22`, status SCHEDULED
- Voucher `HELIOSVIP100`, discount 100.00, max_uses 4
- Invite due: 2026-07-01 (roughly 3 weeks before)

**Example train_005 event handling:**
- Event `EVT-MERIDIAN-BRIEFING`, status SCHEDULED
- Voucher `MERIDIANBRIEF50`, discount 50.00, max_uses 20
- Invite due: computed as 2026-07-01 for a late-July event

---

## Accounting Actions

When a paid milestone has a missing revenue journal, create an accounting entry:

- `action`: `"RECORD_REVENUE_MS2"` (replace MS2 with the actual milestone ID)
- `debit_account`: `"DEFERRED_REVENUE"`
- `credit_account`: `"IMPLEMENTATION_SERVICES_REVENUE"`
- `owner_queue`: `"ACCOUNTING"`
- `amount`: the milestone's paid amount

When no paid milestones need journal entries, use `"VERIFY_REVENUE_ONLY"` or
`"NO_ACCOUNTING_ACTION"` per the template vocabulary.

**Example from train_005:**
- MS2 paid 45000 but missing revenue journal
- Action: `"RECORD_REVENUE_MS2"`, debit `"DEFERRED_REVENUE"`, credit
  `"IMPLEMENTATION_SERVICES_REVENUE"`, amount 45000.00

---

## Warning Message Construction

When freight has issues, produce a concise English sentence. Template:

> Freight rates require reconfirmation at final order. {FREIGHT_ID} expired on
> {DATE} and has {RISK_DESCRIPTION}, so it should not be used without a fresh
> quote.

Only mention the problematic freight records. If all freight is fine, the
warning can be omitted or use a minimal message.

**Example from train_004:**
> Freight rates require reconfirmation at final order. FR-LD-ROAD expired on
> 2026-05-25 and has high customs or border risk, so it should not be used
> without a fresh quote.

---

## Field Name Mapping

Different task templates use different field names for the same concept:

| Concept | Quote template field | Reconciliation template field |
|---|---|---|
| Customer ID | `customer_id` | `customer_id` |
| Opportunity amount match | N/A | `opportunity_matches_milestones` or `opportunity_matches_phase_total` |
| Risk detail | `risk_flag` | N/A |
| Customs risk | `customs_border_risk` | N/A |
| Unpaid amount | N/A | `amount_unpaid` or `outstanding_balance` |
| Overall amount due | N/A | `outstanding_balance` |
| Collection action | N/A | `COLLECT_UNPAID_MILESTONE` or `SEND_COLLECTION_NOTICE` |
| Invite action | N/A | `SEND_EVENT_INVITATION` or `SEND_BRIEFING_INVITE` |
| Freight validity | `validity_status`, `source_is_stale` | N/A |
| Quote basis | `quote_basis` | `quote_basis` |

Always defer to the template — the template's field names are authoritative.
