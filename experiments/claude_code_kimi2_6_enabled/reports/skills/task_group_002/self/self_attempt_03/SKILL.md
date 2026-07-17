# Multi-Service Engagement Reconciliation Skill

## Purpose
This skill describes how to solve tasks that require querying multiple backend services (CRM, Accounting, Events), reconciling data across them, and producing a structured JSON response with engagement reconciliation, invoice actions, and event actions.

## General SOP

### 1. Environment Discovery
Before querying data, discover the available endpoints:
- Check `GET /` or `GET /api` for a root listing
- Check `GET /docs` or `GET /openapi.json` for API documentation
- If none of those work, try common REST patterns based on entity names
- Common service prefixes: `/api/opportunities`, `/api/customers`, `/api/contacts`, `/api/invoices`, `/api/payments`, `/api/revenue-journals`, `/api/events`, `/api/vouchers`

### 2. Data Collection Strategy
Gather ALL required data before doing any computation. The typical data model involves:

**CRM Service:**
- `GET /api/opportunities/{opportunity_id}` — opportunity details (id, name, customer_id, amount, stage)
- `GET /api/customers/{customer_id}` — customer details (id, name)
- `GET /api/contacts?opportunity_id={id}` or `GET /api/contacts?customer_id={id}` — contacts; select the primary one

**Accounting Service:**
- `GET /api/invoices?opportunity_id={id}` or `GET /api/invoices?reference_id={id}` — invoices linked to the opportunity
- `GET /api/payments?invoice_id={id}` — payments for each invoice
- `GET /api/revenue-journals?opportunity_id={id}` — revenue recognition entries

**Events Service:**
- `GET /api/events/{event_id}` — event details (status, etc.)
- `GET /api/vouchers/{voucher_code}` — voucher details (status, discount, max_uses)

**Tip:** If a direct lookup by foreign key fails, fetch the full collection and filter client-side. Some APIs use query parameters like `?opportunity=`, `?reference=`, `?customer=`, or embed the ID in the path.

### 3. Engagement Reconciliation
Fill the `engagement_reconciliation` object with these derived fields:

- `as_of_date`: current date in `YYYY-MM-DD` format
- `opportunity_id`, `customer_id`, `customer_name`, `stage`: from CRM
- `won_amount`: opportunity amount if stage is `WON`, otherwise `0.00`
- `phase_total_amount`: sum of all milestone invoice amounts
- `opportunity_matches_phase_total`: `abs(won_amount - phase_total_amount) < 0.01`
- `total_paid_amount`: sum of all payment amounts across all invoices
- `outstanding_balance`: `phase_total_amount - total_paid_amount`
- `primary_contact`: select the contact associated with the opportunity/customer; if multiple exist, use the one marked primary or the first one

**Milestones (MS1, MS2, MS3):**
Each milestone corresponds to an invoice. For each:
- `milestone_id`: `MS1`, `MS2`, `MS3` (order ascending)
- `amount`: invoice amount
- `invoice_state`: `PAID` if invoice status is paid/closed, `OPEN` if outstanding > 0, `VOID` if cancelled/voided, else `UNKNOWN`
- `payment_state`: `PAID` if fully paid, `PARTIAL` if some payment exists but not full, `UNPAID` if no payments, else `UNKNOWN`
- `paid_amount`: sum of payments for this invoice
- `due_date`: invoice due date or `null`
- `recognition_status`:
  - `RECOGNIZED` if a revenue journal exists for this milestone/opportunity
  - `MISSING_REVENUE_JOURNAL` if the milestone is paid but no revenue journal exists
  - `NOT_REQUIRED_UNPAID` if the milestone is not fully paid
  - `UNKNOWN` if state cannot be determined

### 4. Invoice Actions
Determine accounting and collection actions based on milestone states.

**Primary Accounting Action Rules:**
- `RECORD_REVENUE_MS2`: If milestone MS2 exists, has an invoice, is fully paid (`payment_state: PAID`), AND has no revenue journal (`recognition_status: MISSING_REVENUE_JOURNAL`)
- `VERIFY_REVENUE_ONLY`: If a revenue journal already exists for any milestone (`recognition_status: RECOGNIZED`)
- `NO_ACCOUNTING_ACTION`: Otherwise

The `accounting_action` object mirrors the primary action and specifies:
- `action`: same as primary
- `milestone_id`: `MS2` for `RECORD_REVENUE_MS2`, the recognized milestone for `VERIFY_REVENUE_ONLY`, else `NONE`
- `amount`: the milestone amount for `RECORD_REVENUE_MS2`, `0.00` otherwise
- `debit_account`: `DEFERRED_REVENUE` for `RECORD_REVENUE_MS2`, `NONE` otherwise
- `credit_account`: `IMPLEMENTATION_SERVICES_REVENUE` for `RECORD_REVENUE_MS2`, `NONE` otherwise
- `owner_queue`: `ACCOUNTING` for revenue actions, `NONE` otherwise

**Collection Action Rules:**
- `MONITOR_UNPAID_NOT_DUE`: If there is an open/unpaid invoice with a future due date
- `SEND_COLLECTION_NOTICE`: If there is an open/unpaid invoice with a past due date
- `NO_COLLECTION_ACTION`: If no open/unpaid invoices exist

The `collection_task` object specifies:
- `action`: same as collection action
- `milestone_id`: the milestone with the open/unpaid invoice, or `NONE`
- `amount`: the outstanding amount of that invoice, or `0.00`
- `due_date`: the due date of that invoice, or `null`
- `owner_queue`: `COLLECTIONS` for `SEND_COLLECTION_NOTICE`, `ACCOUNT_MANAGEMENT` for `MONITOR_UNPAID_NOT_DUE`, `NONE` otherwise
- `contact_name`: primary contact name

**Priority:** If multiple milestones qualify for collection action, prefer the one that is past due (`SEND_COLLECTION_NOTICE`) over future due (`MONITOR_UNPAID_NOT_DUE`). If multiple past-due, prefer the earliest due date.

### 5. Event Actions
Determine event-related actions.

- `event_status`: from events service (`SCHEDULED`, `ACTIVE`, `COMPLETED`, `CANCELLED`, `UNKNOWN`)
- `voucher`: map voucher fields directly from events service response

**Invite Action Rules:**
- `SEND_BRIEFING_INVITE`: If event status is `SCHEDULED` or `ACTIVE`, AND voucher status is `ACTIVE`
- `VERIFY_INVITE_SENT`: If event status is `SCHEDULED` or `ACTIVE`, but voucher status is NOT `ACTIVE`
- `NO_INVITE_ACTION`: If event is `COMPLETED`, `CANCELLED`, or `UNKNOWN`

The `invite_task` object specifies:
- `action`: same as invite action
- `event_id`: the event ID
- `voucher_code`: the voucher code
- `owner_queue`: `EVENTS` for `SEND_BRIEFING_INVITE`, `ACCOUNT_MANAGEMENT` for `VERIFY_INVITE_SENT`, `NONE` otherwise
- `contact_name`: primary contact name
- `customer_id`: the customer ID

### 6. Output Formatting
- Return **only** the JSON object matching the answer template
- All monetary values are USD with exactly two decimal places (e.g., `1234.50`)
- Use `YYYY-MM-DD` for dates
- Use the exact enum values specified in the template (uppercase, underscores)
- Order arrays as specified (e.g., milestones ascending by `milestone_id`)
- Use `null` for missing dates, not empty strings
- Booleans must be literal `true`/`false`, not strings

## Common Pitfalls
1. **Wrong endpoint paths:** Services may use `/api/invoices?opportunity_id=X` vs `/api/invoices?reference=X`. Try both or fetch all and filter.
2. **Contact selection:** If the API returns multiple contacts, prefer the one tied to the opportunity over the customer, or the one explicitly marked `is_primary: true`.
3. **Payment aggregation:** A single invoice may have multiple payment records. Sum them all.
4. **Revenue journal matching:** A revenue journal may reference the opportunity or a specific milestone. Check both `opportunity_id` and `milestone_id` fields in the journal.
5. **Date comparison:** Use strict date comparison without time-of-day. `due_date < today` means past due; `due_date >= today` means not yet due.
6. **Stage case sensitivity:** CRM may return `won`, `Won`, or `WON`. Normalize to uppercase before comparing.
7. **Voucher status:** A voucher might be `DRAFT` or `EXPIRED` even when associated with an active event. The invite action depends on BOTH event status and voucher status.
8. **Milestone ordering:** Always output MS1, MS2, MS3 in that order, even if some are missing from the data. Include all three if the template expects them, using `0.00` / `UNKNOWN` defaults when data is absent.
9. **Opportunity amount vs invoice amount:** The `won_amount` comes from the CRM opportunity; `phase_total_amount` comes from summing invoices. Do not conflate them.
10. **Missing services:** If the events service is down or the event/voucher does not exist, use `UNKNOWN` for statuses and `NO_INVITE_ACTION` for the invite action.
