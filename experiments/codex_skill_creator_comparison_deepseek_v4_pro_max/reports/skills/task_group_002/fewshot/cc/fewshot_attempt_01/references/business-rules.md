# Business Rules Reference

Detailed policy application, enum-mapping tables, decision logic, and edge-case
handling for MedBridge Sales Ops tasks.

## Policy Catalog

These eight policies are the complete set in the API. Every task should fetch
all policies and apply the ones relevant to the task type.

### Payment policies

**POL-RECURRING-NGO-PAYMENT** (`terms_code: NET_30_AFTER_PO`)
- Applies to: recurring NGO customers
- Rule: Recurring NGO customers can use NET_30_AFTER_PO unless restricted grant
  terms say otherwise.

**POL-NEW-CLIENT-PAYMENT** (`terms_code: PREPAY_100`)
- Applies to: new NGO clients without approved credit history
- Rule: New NGO clients require PREPAY_100 before production release.

**POL-RECURRING-COMMERCIAL-PAYMENT** (implied by policy data)
- Commercial recurring accounts use `NET_30_AFTER_PO` per their `payment_profile`.

### Quote scope policies

**POL-INDICATIVE-EXW** (`terms_code: EXW_ONLY_EXCLUDE_FREIGHT`)
- Applies to: indicative quotes without confirmed destination
- Rule: Indicative quotes without destination must be EXW only and exclude
  freight.

**POL-MODULE-GRANULARITY** (`terms_code: MODULE_LINES`)
- Applies to: module RFQs
- Rule: Module RFQs should be quoted at module line level unless the customer
  asks for component-level pricing.

**POL-EXW-SCOPE** (`terms_code: EXW_EXCLUSIONS`)
- Applies to: EXW quotes
- Rule: EXW excludes freight, insurance, import duty, customs clearance, and
  last-mile handling unless explicitly added as separate options.

**POL-QUOTE-VALIDITY** (`terms_code: QUOTE_VALID_30_DAYS`)
- Applies to: all catalog quotes unless overridden
- Rule: Catalog quote pricing is valid for 30 calendar days from quote date;
  freight validity may expire sooner.

### Freight policies

**POL-FREIGHT-RECONFIRM** (`terms_code: RECONFIRM_AT_ORDER`)
- Applies to: all freight quotes
- Rule: Freight rates need reconfirmation at final order and are valid only
  through the freight quote valid_until date.

### Revenue recognition policies

**POL-REVREC** (`terms_code: RECOGNIZE_PAID_COMPLETE_MILESTONES`)
- Applies to: implementation service milestones
- Rule: When a milestone is complete and paid, create or verify revenue
  recognition from deferred revenue to income; unpaid future milestones should
  remain outstanding and drive collection tasks when due or overdue.

---

## Payment Terms by Segment

| Segment | Default Payment Terms | Policy Source |
|---------|----------------------|---------------|
| `recurring_ngo` | `NET_30_AFTER_PO` | POL-RECURRING-NGO-PAYMENT |
| `new_ngo` | `PREPAY_100` | POL-NEW-CLIENT-PAYMENT |
| `recurring_commercial` | `NET_30_AFTER_PO` | payment_profile field |

Always read the customer's `grant_terms` and `notes` for possible overrides.
If a customer has restricted grant terms (e.g., "first order under restricted
donor review"), the tighter terms apply.

---

## Enum Mapping Tables

### Opportunity stage

| API Value | Task Output | Meaning |
|-----------|-------------|---------|
| `closed_won` | `WON` | Opportunity is won |
| `open` | `OPEN` | Opportunity is still open |
| `closed_lost` | `LOST` | Opportunity was lost |

### Invoice status

| API Value | Task Output |
|-----------|-------------|
| `paid` | `PAID` |
| `unpaid` | `OPEN` |

### Payment state (derived)

| Condition | Output |
|-----------|--------|
| Invoice paid + payment total >= invoice amount | `PAID` |
| Some payments but total < invoice amount | `PARTIAL` |
| No payments | `UNPAID` |

### Route risk

| API Value | Task Output |
|-----------|-------------|
| `low` | `LOW` |
| `medium` | `MEDIUM` |
| `high` | `HIGH` |

### Freight validity

| Condition | validity_status | source_is_stale |
|-----------|-----------------|-----------------|
| `valid_until >= quote_date` | `VALID` | `false` |
| `valid_until < quote_date` | `STALE` | `true` |

### Revenue recognition status (per milestone)

| Condition | Output |
|-----------|--------|
| Paid invoice + revenue journal exists for this invoice/phase | `RECOGNIZED` |
| Paid invoice + no revenue journal found | `MISSING_REVENUE_JOURNAL` |
| Unpaid invoice | `NOT_REQUIRED_UNPAID` |

### Global revenue recognition status

| Condition | Output |
|-----------|--------|
| Every paid milestone has a revenue journal | `COMPLETE_FOR_PAID_MILESTONES` |
| Any paid milestone is missing a revenue journal | `MISSING_FOR_PAID_MILESTONES` |
| No paid milestones exist (all unpaid) | `NOT_REQUIRED` |

### Event status

| API Value | Task Output |
|-----------|-------------|
| `scheduled` | `SCHEDULED` |
| `confirmed` | `ACTIVE` |
| `live` | `ACTIVE` |
| `completed` | `COMPLETED` |
| `cancelled` | `CANCELLED` |
| `tentative` | `SCHEDULED` (treat as scheduled for invite purposes) |

### Voucher status

Map to uppercase: `active` → `ACTIVE`, `draft` → `DRAFT`, `expired` → `EXPIRED`,
`disabled` → `DISABLED`.

---

## Freight Recommendation Logic

The recommended transport mode is chosen from the available freight quotes for
the quote. Apply these rules in order:

1. **Filter out STALE quotes** (`valid_until < quote_date`). Stale quotes are
   not considered for recommendation unless no valid quotes exist.
2. **Filter out HIGH-risk quotes** if alternatives exist.
3. **Preference order among remaining candidates**:

   | Priority | Mode | Rationale |
   |----------|------|-----------|
   | 1 | SEA | Lowest cost, low risk; default for non-urgent shipments |
   | 2 | AIR | Fastest; choose when timing is critical or SEA is unavailable/invalid |
   | 3 | ROAD | Medium-cost; only when SEA and AIR are both unavailable or stale |

4. **If no valid, low/medium-risk quote exists**: recommend the least-bad option
   and flag the situation clearly in warnings.

### Road-specific warnings

When the ROAD freight quote has:
- `route_risk` = `medium` or `high`: flag `MEDIUM_BORDER_RISK` or
  `HIGH_BORDER_RISK` as the risk flag.
- `valid_until < quote_date`: mark the road quote as invalid/stale.
- Even when VALID, road quotes with medium/high border risk should not be the
  primary recommendation if other valid modes exist.

---

## Revenue Recognition Decision Logic

For each milestone in the opportunity:

1. Find the invoice via `phase.invoice_id` matching `invoice.id`.
2. Determine if the invoice is paid: `invoice.status == "paid"`.
3. Find all payments for this invoice: filter payments on
   `payment.invoice_id == invoice.id`. Sum `amount_usd`.
4. Find the revenue journal: check `revenue-journals` for a record where
   `invoice_id == invoice.id` or `phase_id == phase.phase_id`.
5. Assign the per-milestone `recognition_status` using the table above.
6. Compute the global recognition status from all milestones.

### Accounting action derivation

- If any paid milestone is missing a revenue journal: the primary accounting
  action is `RECORD_REVENUE_MSx` where x is the lowest-numbered milestone with
  the gap. The journal entry debits `DEFERRED_REVENUE` and credits
  `IMPLEMENTATION_SERVICES_REVENUE` for the milestone amount. Owner:
  `ACCOUNTING`.
- If all paid milestones are recognized: `VERIFY_REVENUE_ONLY`. No journal entry
  is needed.
- If no paid milestones exist (all unpaid): `NO_ACCOUNTING_ACTION`.

---

## Collection Action Derivation

For each milestone with an unpaid invoice:

- **`due_date` is in the future** (relative to the business date):
  `MONITOR_UNPAID_NOT_DUE`. The invoice is not overdue yet; no collection notice
  is sent, but the account manager should track it.
- **`due_date` is in the past** (overdue): `SEND_COLLECTION_NOTICE`. The invoice
  is overdue; initiate collection follow-up.
- **No `due_date`**: treat as future (monitor).

The collection task is owned by `ACCOUNT_MANAGEMENT` (or `COLLECTIONS` if the
template uses that enum) and names the contact from the task prompt. Reference
the specific `milestone_id` and `amount_due`.

---

## Event and Invite Action Derivation

For tasks that include an event and voucher:

1. Fetch the event by ID and the voucher by code.
2. Map the event status using the table above.
3. Map the voucher status to uppercase.
4. Use `discount_percent` as the discount amount. Note: despite the field name,
   this may represent a percent or a flat USD amount; use it as-is from the API.
5. Use `max_redemptions` as `max_uses`.

**Invite action**: if the event status implies it is upcoming (`scheduled`,
`confirmed`, `live`, `tentative`), the invite action is `SEND_BRIEFING_INVITE`
(or the template's equivalent enum). The invite task is owned by
`ACCOUNT_MANAGEMENT`.

**No invite needed**: if the event is `completed` or `cancelled`, the invite
action is `NO_INVITE_ACTION` (or the template's equivalent).

---

## Edge Cases

### Quote tasks

- **RFQ with no destination**: do not fetch or include freight quotes.
  `freight_excluded` is `true`. Quote basis is `EXW_ONLY`.
- **Component composition distractors**: RFQ records may contain a
  `component_composition_distractors` field listing sub-components. Ignore it.
  Quote at the module level using `requested_modules` only.
- **Multiple modules in one RFQ**: compute a line item for each module, then sum
  line totals for the grand total. Each line uses its own product's tier pricing.
- **Tier boundary quantities**: a quantity that exactly matches `min_qty` or
  `max_qty` falls within the tier (inclusive bounds).
- **Null max_qty**: a tier with `max_qty: null` has no upper bound and applies
  to any quantity >= `min_qty`.
- **Cold-chain**: if the product has `cold_chain_required: true`, ensure the
  freight quote also has `cold_chain_support: true`. Note this in warnings if
  there is a mismatch.
- **Stale freight**: the template may ask for `source_is_stale` and
  `validity_status` per freight option. Compute these from `valid_until` vs
  `quote_date`.
- **Freight warn text**: when the road quote is stale or high-risk, include a
  prose warning like "Freight rates require reconfirmation at final order.
  FR-LD-ROAD expired on 2026-05-25 and has high customs or border risk, so it
  should not be used without a fresh quote."

### Reconciliation tasks

- **Milestone order**: sort milestones by phase number (MS1, MS2, MS3) not by
  API order.
- **Phase total vs won amount**: sum `phases[].amount_usd` and compare to
  `won_amount_usd`. Set `opportunity_matches_milestones` (or similar field)
  accordingly.
- **Multiple payments for one invoice**: sum all payment amounts for that
  invoice.
- **Revenue journal matching**: a revenue journal links by both `invoice_id` and
  `phase_id`. Check for a journal matching either the invoice or the phase.
- **Due date is null**: for paid milestones, the due date is typically null in
  the task output (the invoice was already settled). Do not fabricate a date.
- **Recognized amount**: sum the `amount_usd` of all revenue journals found for
  this opportunity.
- **Collection task when nothing is overdue**: if all unpaid milestones are
  not yet due, the collection action is `MONITOR_UNPAID_NOT_DUE` with no
  immediate follow-up needed.
- **Multiple accounting gaps**: if more than one paid milestone is missing a
  revenue journal, flag the first (lowest milestone number) as the primary
  accounting action. The template may or may not require all gaps to be listed;
  follow the template's structure.
- **Voucher discount**: use `discount_percent` directly. Do not apply a
  percentage calculation; the API field name may be misleading and its value
  is used as-is in task output.
