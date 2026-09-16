# Reconciliation Decision Tables

Cross-reference tables for merging opportunity, invoice, payment, and revenue
journal records into a single coherent engagement view.

## Milestone state determination

For each milestone phase in an opportunity, follow this chain:

1. Find the invoice whose `id` matches the phase's `invoice_id`.
2. From the invoice, check `status`: `paid`, `unpaid`, `overdue`, `void`.
3. Cross-check with payments: sum `amount_usd` across all payments whose
   `invoice_id` matches. If the sum equals the invoice `amount_usd`, it is paid
   in full. If partial, it's PARTIAL.
4. Find revenue journal entries whose `phase_id` matches the phase.

```
Phase → invoice (by invoice_id)
     → payments (by invoice_id, sum amount_usd)
     → revenue journals (by phase_id, check status=posted)
```

### Revenue recognition per milestone

| Invoice paid in full? | Revenue journal posted? | recognition_status |
|---|---|---|
| Yes | Yes | `RECOGNIZED` |
| Yes | No | `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING` |
| No (unpaid or partial) | N/A | `NOT_REQUIRED_UNPAID` |

Note: the exact enum value depends on the output template. Template enums
include `RECOGNIZED`, `MISSING_REVENUE_JOURNAL`, `REQUIRED_MISSING`,
`NOT_REQUIRED_UNPAID`, and `UNKNOWN`. Use the exact string from the
template's declared enum set.

### Recognition strategy

For engagement reconciliations, the standard accounting journal for
recognizing revenue follows this pattern every time:

- Debit: `DEFERRED_REVENUE`
- Credit: `IMPLEMENTATION_SERVICES_REVENUE`
- Amount: the milestone's total amount_usd
- Owner: `ACCOUNTING`

This matches policy `POL-REVREC` ("recognize completed paid milestone
revenue from deferred revenue to income") and is consistent across all
examples.

## Overall engagement status

| Condition | Status |
|---|---|
| All paid milestones have posted revenue journals | `COMPLETE_FOR_PAID_MILESTONES` |
| At least one paid milestone lacks a journal | `MISSING_FOR_PAID_MILESTONES` |
| No milestones are paid | `NOT_REQUIRED` |

## Collection task routing

| Invoice state | Due date vs as-of date | Action | Owner |
|---|---|---|---|
| Unpaid, overdue | due_date <= as_of_date | `COLLECT_UNPAID_MILESTONE` or `SEND_COLLECTION_NOTICE` | `COLLECTIONS` or `ACCOUNT_MANAGEMENT` |
| Unpaid, not due | due_date > as_of_date | `MONITOR_UNPAID_NOT_DUE` | `ACCOUNT_MANAGEMENT` |
| Paid or no unpaid | N/A | `NO_COLLECTION_ACTION` | `NONE` |

## Event invitation routing

| Event status | Voucher status | Action |
|---|---|---|
| `scheduled` or `confirmed` | `active` | `SEND_BRIEFING_INVITE` or `SEND_EVENT_INVITATION` |
| `live` | `active` | `VERIFY_INVITE_SENT` or `SEND_EVENT_INVITATION` |
| `completed` or `cancelled` | any | `NO_INVITE_ACTION` |
| `tentative` | any | `VERIFY_INVITE_SENT` (don't send until confirmed) |

## Opportunity-to-phase matching

Sum all phase `amount_usd` values. Compare to `won_amount_usd`.

- Equal → `opportunity_matches_milestones` or `opportunity_matches_phase_total` = true
- Not equal → false (flag the discrepancy)

## Voucher interpretation

The API voucher record's `discount_percent` is the discount value. Map it
to the output template's `voucher_discount` or `discount_amount` field
directly. The `max_redemptions` field maps to `max_uses` or `voucher_max_uses`.

## Freight staleness check

For a freight quote with `valid_until` date F and a quote date Q:

- F < Q → freight is STALE, `source_is_stale` = true, `validity_status` = `"STALE"`
- F >= Q → freight is VALID, `source_is_stale` = false, `validity_status` = `"VALID"`

A stale freight quote should still be listed in freight options (the
template expects it), but with its staleness clearly flagged so the
account manager knows to reconfirm.
