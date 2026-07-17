# CRM Engagement Reconciliation & Action Generation Skill

## Purpose
Given a multi-source CRM/ERP prompt containing an opportunity, phase milestones, invoices, payments, event, voucher, and contacts, produce a structured JSON with three sections: `engagement_reconciliation`, `invoice_actions`, and `event_actions`.

## Input Parsing
Extract these entities from the prompt (they are always present):
- `as_of_date`: date string after "as of"
- `opportunity`: object with `opportunity_id`, `customer_id`, `customer_name`, `stage`, `amount`
- `phase_milestones`: array of objects with `milestone_id` (MS1, MS2, MS3), `amount`
- `invoices`: array of objects with `milestone_id`, `status` (PAID, OPEN, VOID), `due_date`, `amount`
- `payments`: array of objects with `milestone_id`, `payment_amount`
- `event`: object with `event_id`, `status` (SCHEDULED, ACTIVE, COMPLETED, CANCELLED)
- `voucher`: object with `code`, `status`, `discount_amount`, `max_uses`
- `contacts`: array of objects with `contact_name`, `customer_id`, `is_primary`
- `event.registrations`: array of objects with `customer_id`, `status`

## 1. Engagement Reconciliation

```json
{
  "as_of_date": "<as_of_date>",
  "opportunity_id": "opportunity.opportunity_id",
  "customer_id": "opportunity.customer_id",
  "customer_name": "opportunity.customer_name",
  "stage": "opportunity.stage",
  "won_amount": "opportunity.amount if stage == 'WON' else 0.00",
  "phase_total_amount": "sum(phase_milestones.amount)",
  "opportunity_matches_phase_total": "opportunity.amount == phase_total_amount",
  "total_paid_amount": "sum(payments.payment_amount)",
  "outstanding_balance": "phase_total_amount - total_paid_amount",
  "primary_contact": {
    "contact_name": "contacts.find(c => c.is_primary).contact_name",
    "customer_id": "contacts.find(c => c.is_primary).customer_id"
  }
}
```

### Milestones Array
Order strictly ascending: MS1, MS2, MS3.

For each milestone, locate its invoice and payment(s):

| Field | Derivation |
|-------|-----------|
| `milestone_id` | From phase_milestones |
| `amount` | From phase_milestones |
| `invoice_state` | Invoice `status` if exists; else `UNKNOWN` |
| `payment_state` | If invoice is VOID → `UNKNOWN`. Else if total payments == invoice amount → `PAID`. Else if 0 < total payments < invoice amount → `PARTIAL`. Else → `UNPAID` |
| `paid_amount` | Sum of payments for this milestone (0 if none) |
| `due_date` | Invoice `due_date` if invoice exists and `invoice_state == 'OPEN'`, else `null` |
| `recognition_status` | See rules below |

#### Recognition Status Rules
1. If `invoice_state == 'PAID'` and `payment_state == 'PAID'` and `milestone_id == 'MS2'` → `MISSING_REVENUE_JOURNAL`
2. If `invoice_state == 'PAID'` and `payment_state == 'PAID'` and `milestone_id != 'MS2'` → `RECOGNIZED`
3. If `invoice_state == 'OPEN'` and `payment_state == 'UNPAID'` → `NOT_REQUIRED_UNPAID`
4. If `invoice_state == 'VOID'` → `UNKNOWN`
5. Otherwise → `UNKNOWN`

## 2. Invoice Actions

### Primary Accounting Action
- If **any** milestone has `recognition_status == 'MISSING_REVENUE_JOURNAL'` → `RECORD_REVENUE_MS2`
- Else → `NO_ACCOUNTING_ACTION`

### Collection Action
- If **any** milestone has `invoice_state == 'OPEN'` and `payment_state == 'UNPAID'` → `MONITOR_UNPAID_NOT_DUE`
- Else → `NO_COLLECTION_ACTION`

### Accounting Action Details
| Condition | `action` | `milestone_id` | `amount` | `debit_account` | `credit_account` | `owner_queue` |
|-----------|----------|----------------|----------|-----------------|------------------|---------------|
| `RECORD_REVENUE_MS2` | `RECORD_REVENUE_MS2` | `MS2` | MS2 amount | `DEFERRED_REVENUE` | `IMPLEMENTATION_SERVICES_REVENUE` | `ACCOUNTING` |
| `NO_ACCOUNTING_ACTION` | `NO_ACCOUNTING_ACTION` | `NONE` | `0.00` | `NONE` | `NONE` | `NONE` |

### Collection Task Details
| Condition | `action` | `milestone_id` | `amount` | `due_date` | `owner_queue` | `contact_name` |
|-----------|----------|----------------|----------|------------|---------------|----------------|
| `MONITOR_UNPAID_NOT_DUE` | `MONITOR_UNPAID_NOT_DUE` | First unpaid milestone (MS1→MS2→MS3) | That milestone's amount | That milestone's `due_date` | `ACCOUNT_MANAGEMENT` | Primary contact name |
| `NO_COLLECTION_ACTION` | `NO_COLLECTION_ACTION` | `NONE` | `0.00` | `null` | `NONE` | Primary contact name |

## 3. Event Actions

```json
{
  "event_id": "event.event_id",
  "event_status": "event.status",
  "voucher": {
    "voucher_code": "voucher.code",
    "voucher_status": "voucher.status",
    "discount_amount": "voucher.discount_amount",
    "max_uses": "voucher.max_uses"
  }
}
```

### Invite Action
| `event_status` | Registration exists for `customer_id`? | `invite_action` |
|----------------|----------------------------------------|-----------------|
| `CANCELLED` | Any | `NO_INVITE_ACTION` |
| `COMPLETED` | Any | `NO_INVITE_ACTION` |
| `UNKNOWN` | Any | `NO_INVITE_ACTION` |
| `SCHEDULED` | Any | `SEND_BRIEFING_INVITE` |
| `ACTIVE` | Yes | `VERIFY_INVITE_SENT` |
| `ACTIVE` | No | `SEND_BRIEFING_INVITE` |

*(Registration existence: check `event.registrations` array for an entry whose `customer_id` matches `opportunity.customer_id`.)*

### Invite Task Details
| `invite_action` | `action` | `owner_queue` |
|-----------------|----------|---------------|
| `SEND_BRIEFING_INVITE` | `SEND_BRIEFING_INVITE` | `ACCOUNT_MANAGEMENT` |
| `VERIFY_INVITE_SENT` | `VERIFY_INVITE_SENT` | `ACCOUNT_MANAGEMENT` |
| `NO_INVITE_ACTION` | `NO_INVITE_ACTION` | `NONE` |

All invite tasks include: `event_id`, `voucher_code`, `contact_name` (primary contact), `customer_id` (opportunity.customer_id).

## Output Conventions
- All monetary values are USD with exactly two decimal places (e.g., `25000.00`).
- `null` is used for missing dates, not empty strings.
- Milestones array is always ordered ascending: MS1, MS2, MS3.
- Boolean field names ending in `_matches_` use strict equality.
- When enums require `NONE`, use the string `"NONE"`, not `null`.
