## Engagement Reconciliation

Use when the task provides an opportunity ID and customer ID, and asks for milestone, payment, revenue-recognition, event, and voucher reconciliation.

### Step 1: Gather source records

1. `GET /api/opportunities/<opp_id>` — stage, won_amount_usd, phases[], contact, outstanding_amount_usd
2. `GET /api/customers/<customer_id>` — name, segment, payment_profile, contacts
3. `GET /api/invoices` — filter by `opportunity_id`; one invoice per phase typically
4. `GET /api/payments` — filter by `opportunity_id`
5. `GET /api/revenue-journals` — filter by `opportunity_id`
6. `GET /api/events` — filter by `opportunity_id` or `customer_id`
7. `GET /api/vouchers` — filter by `opportunity_id` or `event_id`
8. `GET /api/policies` — capture POL-REVREC, POL-QUOTE-VALIDITY

### Step 2: Build milestone table

Map each phase from the opportunity to its invoice, payment, and revenue journal:

1. For each phase: find the invoice where `invoice_id == phase.invoice_id` (or match by `phase_id`)
2. For each invoice: find payment(s) where `payment.invoice_id == invoice.id`; sum `paid_amount`
3. For each invoice/phase: find any revenue journal where `journal.invoice_id == invoice.id` or `journal.phase_id == phase.phase_id`

Phase → milestone mapping convention:
- Phase 1 → MS1, Phase 2 → MS2, Phase 3 → MS3

### Step 3: Determine milestone states

**Invoice state**: from invoice `status` field
- `paid` → PAID
- `unpaid` → OPEN (or UNPAID if the template uses that enum)
- `overdue` → OPEN with overdue flag

**Payment state**:
- `paid_amount >= invoice.amount_usd` → PAID
- `paid_amount > 0 AND paid_amount < invoice.amount_usd` → PARTIAL
- `paid_amount == 0` → UNPAID

**Recognition status** (POL-REVREC):
- Invoice is PAID AND a revenue journal exists → `RECOGNIZED`
- Invoice is PAID AND no revenue journal exists → `MISSING_REVENUE_JOURNAL`
- Invoice is UNPAID/OPEN → `NOT_REQUIRED_UNPAID`
- Default: `UNKNOWN`

### Step 4: Cross-check opportunity total vs milestone total

Sum all phase `amount_usd` values. Compare to `opportunity.won_amount_usd`:
- Equal → `opportunity_matches_milestones: true` (or `opportunity_matches_phase_total: true`)
- Not equal → false

### Step 5: Revenue recognition summary

- `recognition_status`:
  - All paid milestones have journals → `COMPLETE_FOR_PAID_MILESTONES`
  - Any paid milestone is missing a journal → `MISSING_FOR_PAID_MILESTONES`
  - No milestones are paid → `NOT_REQUIRED`
- `recognized_milestones[]`: list milestone IDs that are RECOGNIZED
- `missing_required_milestones[]`: list milestone IDs that are MISSING_REVENUE_JOURNAL
- `recognized_amount`: sum of amounts for recognized milestones

### Step 6: Determine accounting actions

**Primary accounting action**:
- Any paid milestone missing a revenue journal → `RECORD_REVENUE_MS{n}` (where n is the first such milestone)
- All paid milestones recognized → `VERIFY_REVENUE_ONLY`
- No paid milestones → `NO_ACCOUNTING_ACTION`

**Accounting journal entry** (when RECORD_REVENUE_MS{n}):
- `debit_account`: `DEFERRED_REVENUE`
- `credit_account`: `IMPLEMENTATION_SERVICES_REVENUE`
- `owner_queue`: `ACCOUNTING`
- `amount`: the invoice amount for that milestone

### Step 7: Determine collection actions

**Collection action**:
- Any unpaid invoice with `due_date` in the past (relative to current business date) → `SEND_COLLECTION_NOTICE`
- Any unpaid invoice with `due_date` in the future → `MONITOR_UNPAID_NOT_DUE`
- All invoices paid → `NO_COLLECTION_ACTION`

**Collection task details**:
- `owner_queue`: `COLLECTIONS` if overdue, `ACCOUNT_MANAGEMENT` if monitoring
- `contact_name`: from opportunity `contact` field
- `amount`: unpaid amount

### Step 8: Event and voucher

Match event by `opportunity_id` or `customer_id`:

**Event status mapping**:
- `scheduled` → `SCHEDULED`
- `confirmed` → `SCHEDULED` (or ACTIVE if the template distinguishes)
- `live` → `ACTIVE`
- `completed` → `COMPLETED`
- `tentative` → `SCHEDULED`

**Voucher fields**:
- `voucher_code` from event's `voucher_code`
- Look up in `/api/vouchers/<code>` for `discount_percent`, `max_redemptions`, `status`
- `voucher_discount` / `discount_amount`: the `discount_percent` value
- `voucher_status`: `active` → `ACTIVE`, `draft` → `DRAFT`, etc.

**Invite action**:
- Event scheduled/confirmed and not completed → `SEND_BRIEFING_INVITE` (or `SEND_EVENT_INVITATION`)
- Event already completed → `VERIFY_INVITE_SENT` or `NO_INVITE_ACTION`

**Invite task**:
- `owner_queue`: `ACCOUNT_MANAGEMENT`
- `contact_name`: from task prompt (the named contact) or opportunity `contact` field
- `customer_id`: from opportunity

### Step 9: Fill the template

The template varies between tasks but always expects the reconciliation data filled with actual API values. All USD amounts to two decimal places. Dates in ISO `YYYY-MM-DD`. Use the precise field names and enum values defined in the provided `answer_template.json`.

**Key mapping for common field name variants:**

| Template field (train_003) | Template field (train_005) | Source |
|---|---|---|
| account_status.customer_name | engagement_reconciliation.customer_name | customers.name |
| account_status.opportunity_stage | engagement_reconciliation.stage | opportunities.stage (map closed_won→WON) |
| account_status.won_amount | engagement_reconciliation.won_amount | opportunities.won_amount_usd |
| account_status.outstanding_balance | engagement_reconciliation.outstanding_balance | opportunities.outstanding_amount_usd |
| milestones[].invoice_total | milestones[].amount | invoices.amount_usd |
| milestones[].payment_status | milestones[].payment_state | derived from payments |
| milestones[].amount_paid | milestones[].paid_amount | sum of payments for that invoice |
| milestones[].amount_unpaid | — | invoice total - paid amount |
| milestones[].revenue_recognition_status | milestones[].recognition_status | derived from revenue journal presence |
| milestones[].due_date | milestones[].due_date | invoice.due_date or null |
| revenue_recognition.recognition_status | — | summary from step 5 |
| revenue_recognition.recognized_milestones | — | milestone IDs with journals |
| revenue_recognition.missing_required_milestones | — | paid milestones without journals |
| event.event_id | event_actions.event_id | events.id |
| event.voucher_code | event_actions.voucher.voucher_code | events.voucher_code |
| event.voucher_discount | event_actions.voucher.discount_amount | vouchers.discount_percent |
| follow_up_tasks[].task_type | invoice_actions/event_actions | COLLECTION or EVENT_INVITATION |
| follow_up_tasks[].next_action | invoice_actions.*.action | COLLECT_UNPAID_MILESTONE or SEND_EVENT_INVITATION |
