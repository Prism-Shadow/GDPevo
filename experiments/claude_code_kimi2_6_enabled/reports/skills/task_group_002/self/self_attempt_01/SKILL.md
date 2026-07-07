# MedBridge Sales Ops — Engagement Reconciliation Skill

## Purpose
Reconcile a won opportunity against its milestone phases, invoices, payments, and revenue-recognition state, then produce a single JSON response that also includes event/voucher follow-ups for briefing invites.

## Environment
- Base URL is provided by the runner (e.g. `http://34.46.77.124:8002`).
- Override any local/localhost references with the runner-provided base URL.

## API Surface

### Endpoints
All collections are under `/api/<collection>`.

| Collection | Path | Description |
|------------|------|-------------|
| opportunities | `GET /api/opportunities/<id>` | Single opportunity with `phases[]`, `stage`, `won_amount_usd`, `outstanding_amount_usd`, `contact`, `notes` |
| customers | `GET /api/customers/<id>` | Customer record with `name`, `contacts[]` |
| invoices | `GET /api/invoices?opportunity_id=<id>` | Invoices for an opportunity; each has `status`, `amount_usd`, `paid_amount_usd`, `outstanding_amount_usd`, `due_date`, `phase_id` |
| payments | `GET /api/payments?opportunity_id=<id>` | Payments for an opportunity; each has `amount_usd`, `invoice_id`, `status` |
| events | `GET /api/events?opportunity_id=<id>` | Events tied to an opportunity; each has `status`, `event_date`, `voucher_code`, `primary_contact` |
| vouchers | `GET /api/vouchers?opportunity_id=<id>` or `?code=<code>` | Voucher record with `status`, `discount_percent`, `max_redemptions`, `valid_until` |

Query parameters such as `?opportunity_id=...` and `?code=...` are supported on list endpoints.

### Key Data Relationships
- An **opportunity** has one or more **phases** (`phases[]`). Each phase has `phase_id`, `amount_usd`, and `invoice_id`.
- An **invoice** belongs to exactly one phase (`phase_id`).
- A **payment** references an `invoice_id`.
- An **event** belongs to an opportunity and references a `voucher_code`.
- A **voucher** belongs to an opportunity and event.

## Output Schema
Return a single JSON object matching the `answer_template.json` structure with these top-level keys:
- `engagement_reconciliation`
- `invoice_actions`
- `event_actions`

### engagement_reconciliation
| Field | How to compute |
|-------|---------------|
| `as_of_date` | Use the current business date given in the prompt (e.g. `2026-06-01`). |
| `opportunity_id` | From prompt. |
| `customer_id` | From prompt. |
| `customer_name` | From `/api/customers/<id>` → `name`. |
| `stage` | Map opportunity `stage`: `closed_won` → `WON`, otherwise `OPEN` or `LOSS` as appropriate. |
| `won_amount` | `opportunity.won_amount_usd` (two decimals). |
| `phase_total_amount` | Sum of all `phase.amount_usd` values. |
| `opportunity_matches_phase_total` | `won_amount == phase_total_amount`. |
| `total_paid_amount` | Sum of all payment `amount_usd` for this opportunity (or sum of `invoice.paid_amount_usd`). |
| `outstanding_balance` | `opportunity.outstanding_amount_usd`. |
| `primary_contact` | `{ "contact_name": opportunity.contact, "customer_id": customer_id }`. |
| `milestones[]` | One per phase, ordered ascending by phase order (first phase = `MS1`, second = `MS2`, third = `MS3`). |

#### Milestone fields
| Field | How to compute |
|-------|---------------|
| `milestone_id` | `MS1`, `MS2`, `MS3` based on ascending phase order. |
| `amount` | `phase.amount_usd`. |
| `invoice_state` | Map invoice `status`: `paid` → `PAID`; `unpaid`/`overdue`/`draft` → `OPEN`; `void` → `VOID`; otherwise `UNKNOWN`. |
| `payment_state` | `PAID` if `invoice.paid_amount_usd == invoice.amount_usd`; `PARTIAL` if `0 < paid < amount`; `UNPAID` if `paid == 0`; else `UNKNOWN`. |
| `paid_amount` | `invoice.paid_amount_usd`. |
| `due_date` | `invoice.due_date` (or `null` if absent). |
| `recognition_status` | See **Revenue Recognition Rules** below. |

### invoice_actions
| Field | How to compute |
|-------|---------------|
| `primary_accounting_action` | `RECORD_REVENUE_MS2` if a paid milestone has a missing revenue journal (see notes). `VERIFY_REVENUE_ONLY` if there are paid milestones with no missing journal and no action required. `NO_ACCOUNTING_ACTION` if no paid milestones exist or no verification is needed. |
| `collection_action` | `SEND_COLLECTION_NOTICE` if any invoice is unpaid/overdue **and** `due_date < as_of_date`. `MONITOR_UNPAID_NOT_DUE` if unpaid but `due_date >= as_of_date`. `NO_COLLECTION_ACTION` if no outstanding balance. |
| `accounting_action` | Populate `action`, `milestone_id` (`MS2` or `NONE`), `amount` (phase amount or `0.00`), `debit_account` (`DEFERRED_REVENUE` or `NONE`), `credit_account` (`IMPLEMENTATION_SERVICES_REVENUE` or `NONE`), `owner_queue` (`ACCOUNTING` or `NONE`). |
| `collection_task` | Populate `action`, `milestone_id` (unpaid milestone or `NONE`), `amount` (outstanding amount), `due_date`, `owner_queue` (`COLLECTIONS` for overdue, `ACCOUNT_MANAGEMENT` for monitoring, `NONE` otherwise), `contact_name`. |

### event_actions
| Field | How to compute |
|-------|---------------|
| `event_id` | From prompt. |
| `event_status` | Map event `status`: `scheduled`/`confirmed`/`tentative` → `SCHEDULED`; `live` → `ACTIVE`; `completed` → `COMPLETED`; `cancelled` → `CANCELLED`; otherwise `UNKNOWN`. |
| `voucher` | From `/api/vouchers?code=...` or `?opportunity_id=...`. |
| `voucher.voucher_code` | `voucher.code`. |
| `voucher.voucher_status` | Map `active` → `ACTIVE`, `draft` → `DRAFT`, `expired` → `EXPIRED`, `disabled` → `DISABLED`, else `UNKNOWN`. |
| `voucher.discount_amount` | **Ambiguous.** The API only provides `discount_percent`. If no ticket price exists, default to `0.00` or compute from an event fee if one is discoverable. |
| `voucher.max_uses` | `voucher.max_redemptions`. |
| `invite_action` | `SEND_BRIEFING_INVITE` if event is `SCHEDULED`/`ACTIVE` and voucher is `ACTIVE`. `NO_INVITE_ACTION` if event is `CANCELLED` or voucher is not usable. `VERIFY_INVITE_SENT` if event is `COMPLETED`. |
| `invite_task` | Mirror `invite_action` with `event_id`, `voucher_code`, `owner_queue` (`ACCOUNT_MANAGEMENT` or `NONE`), `contact_name`, `customer_id`. |

## Revenue Recognition Rules
The opportunity `notes` field is the primary signal for revenue recognition status:

1. Parse the `notes` string for each phase. Look for phrases like:
   - `"Phase N paid and recognized"` → `RECOGNIZED`
   - `"Phase N is paid ... but journal is missing"` / `"revenue recognition journal is missing"` → `MISSING_REVENUE_JOURNAL`
   - `"Phase N remains unpaid"` / `"Phase N is unpaid"` → `NOT_REQUIRED_UNPAID`

2. If the note does not mention a specific phase:
   - If invoice is unpaid → `NOT_REQUIRED_UNPAID`
   - If invoice is paid but no explicit recognition mention → `UNKNOWN` (or infer from payment data)

3. Priority order:
   - Explicitly missing journal → `MISSING_REVENUE_JOURNAL`
   - Explicitly recognized → `RECOGNIZED`
   - Unpaid → `NOT_REQUIRED_UNPAID`
   - Otherwise → `UNKNOWN`

## Business Logic Summary

### Accounting Action Rules
- **RECORD_REVENUE_MS2**: Triggered when a paid milestone (typically MS2) has a missing revenue journal. Debit `DEFERRED_REVENUE`, credit `IMPLEMENTATION_SERVICES_REVENUE`. Owner queue: `ACCOUNTING`.
- **VERIFY_REVENUE_ONLY**: Use when paid milestones exist, are not missing journals, but should be verified.
- **NO_ACCOUNTING_ACTION**: No paid milestones or nothing to action.

### Collection Action Rules
- **SEND_COLLECTION_NOTICE**: Invoice status is `overdue` (or `due_date < as_of_date` and unpaid). Owner queue: `COLLECTIONS`.
- **MONITOR_UNPAID_NOT_DUE**: Invoice is `unpaid` but `due_date >= as_of_date`. Owner queue: `ACCOUNT_MANAGEMENT`.
- **NO_COLLECTION_ACTION**: No outstanding invoices.

### Invite Action Rules
- **SEND_BRIEFING_INVITE**: Event is upcoming/live (`SCHEDULED`/`ACTIVE`) and voucher is `ACTIVE`.
- **VERIFY_INVITE_SENT**: Event already `COMPLETED`.
- **NO_INVITE_ACTION**: Event `CANCELLED` or voucher unusable.

## Pitfalls
1. **Base URL override**: Always use the runner-provided base URL; do not default to `localhost` or `127.0.0.1` even if the prompt mentions them.
2. **Invoice status mapping**: The API returns statuses like `paid`, `unpaid`, `overdue`, `draft`. The output enum only has `PAID | OPEN | VOID | UNKNOWN`. Map `unpaid`/`overdue`/`draft` → `OPEN`.
3. **Milestone ordering**: Phases must be mapped to `MS1`/`MS2`/`MS3` in the exact order they appear in `opportunity.phases[]` (ascending by array index, not by `phase_id` string).
4. **Opportunity notes parsing**: Revenue recognition status is embedded in free-text `notes`. Look for explicit keywords per phase rather than assuming all paid phases are recognized.
5. **Decimal precision**: All currency values must be formatted to exactly two decimal places.
6. **Event status mapping**: `confirmed` and `tentative` both map to `SCHEDULED`; `live` maps to `ACTIVE`.
7. **No OpenAPI/docs endpoint**: The API does not expose `/docs` or `/openapi.json`. Discover endpoints by querying `/api/<collection>` directly.
8. **Missing revenue journal endpoint**: There is no dedicated `/api/revenue_journals` or `/api/ledger` endpoint in this environment. Recognition status must be inferred from opportunity notes and invoice/payment data.
9. **Discount amount ambiguity**: The voucher API only exposes `discount_percent`, not a fixed amount. If no event ticket price is available, `discount_amount` may need to default to `0.00`.
10. **Return only JSON**: The prompt explicitly forbids narrative outside the JSON response.
