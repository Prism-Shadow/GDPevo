# Engagement Reconciliation & Action Generation Skill

## Purpose
Transform CRM opportunity data into a structured reconciliation report with derived accounting, collection, and event-action recommendations.

## Input Data Schema
Read the payload JSON. It contains these top-level keys (all may be absent—treat missing as empty/null):
- `current_date`: string "YYYY-MM-DD"
- `opportunity`: object with `opportunity_id`, `customer_id`, `customer_name`, `stage` (WON | OPEN | LOST), `amount` (won amount), `primary_contact`
- `milestones`: array of objects with `milestone_id` (MS1, MS2, MS3), `amount`, `invoice_state`, `payment_state`, `paid_amount`, `due_date`
- `payments`: array of objects with `payment_id`, `milestone_id`, `amount`
- `revenue_journals`: array of objects with `journal_id`, `milestone_id`, `amount`
- `event`: object with `event_id`, `status` (SCHEDULED | ACTIVE | COMPLETED | CANCELLED), `voucher` object (`voucher_code`, `status` (ACTIVE | DRAFT | EXPIRED | DISABLED), `discount_amount`, `max_uses`)

## Output Schema
Produce a JSON object matching `answer_template.json` with three top-level sections:
1. `engagement_reconciliation`
2. `invoice_actions`
3. `event_actions`

---

## Section 1: Engagement Reconciliation

### Top-Level Fields
| Field | Derivation Rule |
|-------|-----------------|
| `as_of_date` | `current_date` |
| `opportunity_id` | From `opportunity.opportunity_id` |
| `customer_id` | From `opportunity.customer_id` |
| `customer_name` | From `opportunity.customer_name` |
| `stage` | From `opportunity.stage` |
| `won_amount` | `opportunity.amount` as number with 2 decimals |
| `phase_total_amount` | Sum of all milestone `amount` values |
| `opportunity_matches_phase_total` | `won_amount == phase_total_amount` |
| `total_paid_amount` | Sum of all `payments.amount`. If `payments` array is absent, use `0.00`. |
| `outstanding_balance` | `won_amount - total_paid_amount` |
| `primary_contact.contact_name` | `opportunity.primary_contact` |
| `primary_contact.customer_id` | `opportunity.customer_id` |

### Milestone Array Rules
Milestones must be ordered ascending by `milestone_id` (MS1, MS2, MS3).

For each milestone, derive `invoice_state`, `payment_state`, and `paid_amount` using this **payments-override rule**:

1. **If the input contains a `payments` array (even if empty):**
   - `paid_amount` = sum of all `payments.amount` where `payment.milestone_id == milestone.milestone_id`
   - If `paid_amount > 0`: output `invoice_state` = `"PAID"`, `payment_state` = `"PAID"`
   - If `paid_amount == 0`: output `invoice_state` = `"OPEN"`, `payment_state` = `"UNPAID"`
   - `due_date` = input milestone `due_date` (preserve null if null)

2. **If the input does NOT contain a `payments` array:**
   - Preserve input `invoice_state`, `payment_state`, `paid_amount`, and `due_date` exactly as given.

### Milestone Recognition Status
Apply these rules **in order** for each milestone (use the *derived* `invoice_state` and `payment_state` from the payments-override rule):

1. **If derived `invoice_state` is `"VOID"`** -> `"NOT_REQUIRED_UNPAID"`
2. **If derived `invoice_state` is `"PAID"` AND derived `payment_state` is `"PAID"` AND there exists a `revenue_journal` with `journal.milestone_id == milestone.milestone_id` AND `journal.amount == milestone.amount`** -> `"RECOGNIZED"`
3. **If derived `invoice_state` is `"PAID"` AND derived `payment_state` is `"PAID"` AND either no matching `revenue_journal` exists OR the matching journal's amount differs** -> `"MISSING_REVENUE_JOURNAL"`
4. **If derived `invoice_state` is `"OPEN"` AND derived `payment_state` is `"UNPAID"` AND `due_date` is in the future (>`current_date`)** -> `"NOT_REQUIRED_UNPAID"`
5. **Otherwise** -> `"UNKNOWN"`

> **Important:** When `payments` array is present, any milestone with at least one payment is treated as PAID/PAID for recognition purposes, even if the payment sum is less than the milestone amount. When `payments` array is absent, the input invoice/payment states are preserved and evaluated directly.

---

## Section 2: Invoice Actions

### Primary Accounting Action
| Condition | Result |
|-----------|--------|
| `opportunity.stage == "LOST"` | `"NO_ACCOUNTING_ACTION"` |
| Any milestone has `"MISSING_REVENUE_JOURNAL"` | `"RECORD_REVENUE_MS2"` |
| Otherwise | `"NO_ACCOUNTING_ACTION"` |

> LOST opportunities never trigger revenue recording, even if a milestone is missing its journal.

### Accounting Action Detail Object
| Field | When `RECORD_REVENUE_MS2` | When `NO_ACCOUNTING_ACTION` |
|-------|---------------------------|----------------------------|
| `action` | `"RECORD_REVENUE_MS2"` | `"NO_ACCOUNTING_ACTION"` |
| `milestone_id` | `"MS2"` | `"NONE"` |
| `amount` | `milestones[MS2].amount` | `0.00` |
| `debit_account` | `"DEFERRED_REVENUE"` | `"NONE"` |
| `credit_account` | `"IMPLEMENTATION_SERVICES_REVENUE"` | `"NONE"` |
| `owner_queue` | `"ACCOUNTING"` | `"NONE"` |

### Collection Action
Identify "unpaid" milestones: those with derived `invoice_state != "PAID"` (or derived `payment_state != "PAID"`) after applying the payments-override rule.

| Condition | Result |
|-----------|--------|
| `opportunity.stage == "LOST"` AND at least one unpaid milestone exists | `"SEND_COLLECTION_NOTICE"` |
| `opportunity.stage == "WON"` AND at least one unpaid milestone has `due_date < current_date` (past due) | `"SEND_COLLECTION_NOTICE"` |
| `opportunity.stage == "WON"` AND at least one unpaid milestone exists but none are past due | `"MONITOR_UNPAID_NOT_DUE"` |
| Otherwise | `"NO_COLLECTION_ACTION"` |

### Collection Task Detail Object
- `action` = same as `collection_action`
- `milestone_id`:
  - For `SEND_COLLECTION_NOTICE`:
    - If stage is LOST: first unpaid milestone by milestone_id order (MS1, then MS2, then MS3)
    - If stage is WON: first past-due unpaid milestone by milestone_id order
  - For `MONITOR_UNPAID_NOT_DUE`: first future-due unpaid milestone by milestone_id order
  - For `NO_COLLECTION_ACTION`: `"NONE"`
- `amount` = the selected milestone's `amount`
- `due_date` = the selected milestone's `due_date` (null if null)
- `owner_queue`: `"COLLECTIONS"` for `SEND_COLLECTION_NOTICE`, `"ACCOUNT_MANAGEMENT"` for `MONITOR_UNPAID_NOT_DUE`, `"NONE"` for `NO_COLLECTION_ACTION`
- `contact_name` = `opportunity.primary_contact`

---

## Section 3: Event Actions

### Event Fields
| Field | Derivation |
|-------|------------|
| `event_id` | `event.event_id` if event exists, else `null` |
| `event_status` | `event.status` if event exists, else `"UNKNOWN"` |
| `voucher` | If event exists: copy `event.voucher` object fields (`voucher_code`, `status` as `voucher_status`, `discount_amount`, `max_uses`). If no event: `null`. |

### Invite Action
| Condition | Result |
|-----------|--------|
| `event.status == "SCHEDULED"` AND `event.voucher.status == "ACTIVE"` | `"SEND_BRIEFING_INVITE"` |
| `event.status == "ACTIVE"` AND `event.voucher.status == "ACTIVE"` | `"VERIFY_INVITE_SENT"` |
| Otherwise (no event, COMPLETED/CANCELLED status, or non-ACTIVE voucher) | `"NO_INVITE_ACTION"` |

### Invite Task Detail Object
| Field | When `SEND_BRIEFING_INVITE` | When `VERIFY_INVITE_SENT` | When `NO_INVITE_ACTION` |
|-------|------------------------------|---------------------------|------------------------|
| `action` | `"SEND_BRIEFING_INVITE"` | `"VERIFY_INVITE_SENT"` | `"NO_INVITE_ACTION"` |
| `event_id` | `event.event_id` | `event.event_id` | `null` |
| `voucher_code` | `event.voucher.voucher_code` | `event.voucher.voucher_code` | `null` |
| `owner_queue` | `"ACCOUNT_MANAGEMENT"` | `"EVENTS"` | `"NONE"` |
| `contact_name` | `opportunity.primary_contact` | `opportunity.primary_contact` | `opportunity.primary_contact` |
| `customer_id` | `opportunity.customer_id` | `opportunity.customer_id` | `opportunity.customer_id` |

---

## Key Pitfalls
1. **Payments array presence changes behavior.** When `payments` exists, always derive milestone states from payments (presence = PAID/PAID, absence = OPEN/UNPAID). When `payments` is absent, preserve input states exactly.
2. **LOST stage blocks accounting.** A LOST opportunity always gets `NO_ACCOUNTING_ACTION` for the accounting action, even if MS2 has `MISSING_REVENUE_JOURNAL`.
3. **Collection on LOST is immediate.** LOST stage with any unpaid milestone triggers `SEND_COLLECTION_NOTICE` regardless of due date.
4. **Revenue journal amount must match milestone amount.** For `RECOGNIZED` status, the journal amount must equal the milestone amount exactly.
5. **Milestone order.** Always output milestones sorted MS1, MS2, MS3. Collection and action targets pick the first qualifying milestone in this order.
6. **Numbers.** All monetary values must be numbers with exactly 2 decimal places.
