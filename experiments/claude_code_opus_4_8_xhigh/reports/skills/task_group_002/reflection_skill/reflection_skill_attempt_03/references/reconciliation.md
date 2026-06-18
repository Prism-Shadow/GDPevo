# Receivables / milestone reconciliation families (C, D)

These reconcile a won opportunity against its milestone invoices, payments, and
revenue journals, then route accounting + collection + event follow-ups. Both
families share the same underlying ground truth; only the output shape and a few
enum spellings differ. ALWAYS read the template's declared enums and use those
literal tokens — the "missing journal" and recognition tokens differ between the
two templates.

## Records to pull (filter strictly by `opportunity_id`)

1. `GET /api/opportunities/<id>` → `stage` (closed_won→WON), `won_amount_usd`,
   `outstanding_amount_usd`, `contact`, and `phases[]` (each `phase_id`,
   `amount_usd`, `invoice_id`, `completion_date`). `notes` often states the
   intended answer ("phase 2 paid but revenue journal missing") — use it to
   sanity-check, not as the source of numbers.
2. `GET /api/customers/<id>` → `name`, contact details.
3. `/api/invoices` → keep rows where `opportunity_id` matches; map by `phase_id`.
   Fields: `amount_usd`, `status` (paid/unpaid), `paid_amount_usd`,
   `outstanding_amount_usd`, `due_date`.
4. `/api/payments` → posted payments per invoice (confirms PAID).
5. `/api/revenue-journals` → a posted `RJ-...` per phase confirms recognition.
   If a paid phase has NO journal, that is the "missing journal" case.
6. `/api/events` and `/api/vouchers` → the linked celebration/briefing event and
   its voucher.

## Derivations (same for both families)

- `won_amount` = opportunity `won_amount_usd`.
- phase/milestone total = Σ phase `amount_usd`.
- `opportunity_matches_milestones` / `opportunity_matches_phase_total` =
  (won_amount == Σ phases).
- `outstanding_balance` = Σ unpaid phase amounts (= opportunity
  `outstanding_amount_usd`).
- `total_paid_amount` = Σ paid phase amounts.
- Per milestone:
  - amount / invoice_total = phase `amount_usd`.
  - invoice_state: paid → `PAID`; unpaid → `OPEN`/`UNPAID` per the template's
    enum (Family C invoice_state enum is `PAID|OPEN|VOID|UNKNOWN`; Family D
    payment_status enum is `PAID|PARTIAL|UNPAID`). Read the template.
  - payment_state: `PAID` if a posted payment covers it, else `UNPAID`
    (`PARTIAL` if partly paid).
  - paid_amount / amount_paid = invoice `paid_amount_usd`;
    amount_unpaid = invoice `outstanding_amount_usd`.
  - **due_date: `null` if the milestone is PAID; the invoice `due_date` if
    UNPAID.** (This is the single most common reconciliation error — do not copy
    the invoice due date onto settled milestones.)
  - recognition status — the state machine:
    - PAID + posted revenue journal exists → `RECOGNIZED`.
    - PAID + NO journal → "missing journal" token:
      Family C: `MISSING_REVENUE_JOURNAL`; Family D: `REQUIRED_MISSING`.
    - UNPAID → `NOT_REQUIRED_UNPAID`.

- `milestone_id`: the template says "stable phase or invoice milestone id".
  Two conventions appear and both are defensible; prefer the one the template's
  own enum hints at:
  - If the template declares an enum like `MS1 | MS2 | MS3`, use those
    positional ids (ascending order).
  - Otherwise use the API `phase_id` (e.g. `HEL-P1`, `MER-P2`) as the stable id.
  Be internally consistent and reuse the same id in `milestones`,
  `recognized_milestones`, and follow-up tasks.

## Family C — engagement_reconciliation + invoice_actions + event_actions

Adds an `as_of_date` (use the prompt's business date, e.g. 2026-06-01) and
routes two actions plus an event invite. Milestone `milestone_id` enum here is
`MS1|MS2|MS3`; order ascending.

- `primary_accounting_action` / `accounting_action`: if exactly one paid
  milestone is missing its journal → `RECORD_REVENUE_MS<n>` with
  `milestone_id` = that milestone, `amount` = its value,
  `debit_account: DEFERRED_REVENUE`, `credit_account:
  IMPLEMENTATION_SERVICES_REVENUE`, `owner_queue: ACCOUNTING`. If every paid
  milestone is recognized → `VERIFY_REVENUE_ONLY` / `NO_ACCOUNTING_ACTION` with
  `milestone_id: NONE` per the enum.
- `collection_action` / `collection_task`: for the unpaid milestone, compare its
  invoice `due_date` to `as_of_date`:
  - due_date > as_of (not yet due) → `MONITOR_UNPAID_NOT_DUE`,
    `owner_queue: ACCOUNT_MANAGEMENT`.
  - due_date <= as_of (due/overdue) → `SEND_COLLECTION_NOTICE`,
    `owner_queue: COLLECTIONS`.
  Carry the unpaid `milestone_id`, `amount`, `due_date`, and the primary
  `contact_name`.
- `event_actions`: `event_status` = UPPERCASE of event `status` (scheduled →
  `SCHEDULED`). voucher block: `voucher_status` = UPPERCASE of voucher status
  (active → `ACTIVE`); `discount_amount` = the voucher's `discount_percent`
  number as-is (NOT a USD conversion); `max_uses` = `max_redemptions`.
  `invite_action`/`invite_task.action` = `SEND_BRIEFING_INVITE` (when invite not
  yet sent), with the event id, voucher code, `owner_queue: ACCOUNT_MANAGEMENT`,
  contact, customer_id.

## Family D — account_status + milestones + revenue_recognition + follow_up_tasks

Milestone `revenue_recognition_status` enum here is
`RECOGNIZED | REQUIRED_MISSING | NOT_REQUIRED_UNPAID`.

- `account_status`: customer/opportunity ids, `opportunity_stage` (WON),
  `won_amount`, `opportunity_matches_milestones`, `outstanding_balance`, and a
  `contact` block linking the named account contact to customer + opportunity.
- top-level `revenue_recognition`:
  - `recognition_status`: `COMPLETE_FOR_PAID_MILESTONES` if every paid milestone
    has a journal; `MISSING_FOR_PAID_MILESTONES` if a paid milestone lacks one;
    `NOT_REQUIRED` if nothing is paid.
  - `recognized_milestones`: ids of paid+journaled milestones.
  - `missing_required_milestones`: ids of paid milestones lacking a journal
    (often `[]`).
  - `recognized_amount`: Σ recognized milestone amounts.
- `follow_up_tasks` (one per applicable action):
  - For each UNPAID milestone → a `COLLECTION` task:
    `next_action: COLLECT_UNPAID_MILESTONE`, `due_date` = invoice due_date,
    `milestone_id` set, `amount_due` set, event/voucher fields `null`.
  - For the linked celebration event → an `EVENT_INVITATION` task:
    `next_action: SEND_EVENT_INVITATION`, `event_id` + `voucher_code` set,
    `milestone_id`/`amount_due` `null`. The event-invite `due_date` is the event
    date (or a lead time before it — if the template/prompt does not specify a
    lead, use the event date). Always attach the named account contact and link
    customer + opportunity on every task.

## Mistakes I made here (and the fix)
- Kept invoice `due_date` on PAID milestones. FIX: paid → `due_date: null`.
- Mixed up the recognition/"missing journal" enum across templates. FIX: copy
  the literal token from the template's declared enum (`MISSING_REVENUE_JOURNAL`
  for Family C vs `REQUIRED_MISSING` for Family D).
- Solved the wrong opportunity / used the wrong template family entirely. FIX:
  confirm the opportunity id from the prompt and pick the family by the
  template's top-level keys before pulling anything.
- Converted voucher `discount_percent` toward a USD value. FIX: place the
  percent number straight into `discount_amount`/`voucher_discount`.

## Voucher / event quick map
- voucher `code` → `voucher_code`; `discount_percent` → `discount_amount` /
  `voucher_discount` (number as-is); `max_redemptions` → `max_uses` /
  `voucher_max_uses`; `status` → UPPERCASE voucher_status.
- event `status` → UPPERCASE event_status; `event_date` → event_date;
  `primary_contact` should equal the account contact named in the prompt.
