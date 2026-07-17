# MedBridge API Integration Skill

## Purpose
Solve tasks that integrate with MedBridge backend APIs (Logistics/Procurement and Sales Ops) to produce finance-ready JSON outputs. Tasks fall into two families:
1. **Logistics/Procurement Quoting** — product catalog lookups, freight option evaluation, and quote generation.
2. **Sales Ops Reconciliation** — opportunity-to-milestone reconciliation, invoice/payment state analysis, revenue recognition checks, and event/voucher action routing.

## Prerequisites
- Read `input/prompt.txt` for task instructions and entity IDs.
- Read `input/payloads/answer_template.json` for the exact output schema and enum values.
- The API base URL is typically `http://127.0.0.1:${PORT}` or similar; the prompt will specify the host and port. Treat the date given in the prompt as the current business date.

---

## Step 1: Identify Task Family

| Clue | Family |
|------|--------|
| Mentions "quote", "freight", "RFQ", "product", "catalog", "EXW", "lead time", "shelf life" | **Logistics / Procurement** |
| Mentions "opportunity", "milestone", "invoice", "payment", "revenue recognition", "reconciliation", "briefing", "voucher", "CRM" | **Sales Ops** |

---

## Step 2: Discover API Endpoints

The API is REST-like. Common root resources to probe (append to base URL):

**Logistics / Procurement:**
- `/customers` or `/customers/{id}`
- `/products` or `/catalog` (often filter by `product_code`)
- `/freight_quotes` or `/freight` (often filter by `quote_id` or `customer_id`)
- `/rfqs/{id}`

**Sales Ops:**
- `/opportunities/{id}`
- `/customers/{id}`
- `/contacts` (often filter by `customer_id` or `opportunity_id`)
- `/milestones` (filter by `opportunity_id`)
- `/invoices` (filter by `milestone_id`)
- `/payments` (filter by `invoice_id`)
- `/revenue_journals` (filter by `milestone_id`)
- `/events/{id}`
- `/vouchers/{code}`

If a `GET` on a sub-resource returns 404, try query parameters (`?opportunity_id=...`) or list endpoints and filter client-side.

---

## Step 3: Fetch Strategy

### Logistics / Procurement
1. **Fetch the RFQ / Quote** using the ID from the prompt.
2. **Fetch the Customer** record to obtain policy flags (e.g., `URGENT_VACCINES_AIR_PREFERRED`) and payment terms.
3. **Fetch the Product / Catalog** record using the product code to get unit price, lead time, and shelf life. Determine the correct pricing tier by matching `confirmed_quantity` against tier `min_quantity` / `max_quantity`.
4. **Fetch Freight Quotes** for the request. Expect up to three modes: `AIR`, `SEA`, `ROAD`.
5. Compute:
   - `exw_total_usd = confirmed_quantity × unit_price_usd` (round to 2 decimals)
   - `grand_total_usd = exw_total_usd + freight_cost_usd` for each option
   - Freight validity: compare the API-returned `valid_until` (or `validity_status`) against the current business date. Use the API's own `validity_status` when provided; otherwise compute `VALID` if `valid_until >= current_date`, else `EXPIRED`.
   - Risk level: use API-returned risk fields when available. Fallback heuristics: `ROAD` often carries `MEDIUM` or `HIGH` border risk; `AIR` is usually `LOW`; `SEA` is `LOW` or `MEDIUM`.

### Sales Ops
1. **Fetch the Opportunity** using the ID from the prompt.
2. **Fetch the Customer** record.
3. **Fetch the Contact** linked to the customer/opportunity.
4. **Fetch Milestones** for the opportunity. Order them ascending by `milestone_id` (`MS1`, `MS2`, `MS3`).
5. For **each milestone**, fetch:
   - **Invoice(s)** — determine `invoice_state` (`PAID`, `OPEN`, `VOID`, `UNKNOWN`)
   - **Payment(s)** — determine `payment_state` (`PAID`, `PARTIAL`, `UNPAID`, `UNKNOWN`) and `paid_amount`
   - **Revenue Journal(s)** — determine whether revenue has been recognized
6. Compute reconciliation fields:
   - `phase_total_amount = sum(milestone.amount)`
   - `opportunity_matches_phase_total = abs(opportunity.won_amount - phase_total_amount) < 0.01`
   - `total_paid_amount = sum(milestone.paid_amount)`
   - `outstanding_balance = opportunity.won_amount - total_paid_amount` (round to 2 decimals)
7. Determine **revenue recognition status** per milestone:
   - If milestone is paid in full and a revenue journal exists → `RECOGNIZED`
   - If milestone is paid in full but no revenue journal → `MISSING_REVENUE_JOURNAL` (or `REQUIRED_MISSING` depending on template)
   - If milestone is unpaid and due date is `null` or in the future → `NOT_REQUIRED_UNPAID`
   - If milestone amount is `0` → `NOT_REQUIRED_UNPAID`
   - Otherwise → `UNKNOWN`
8. Determine **accounting actions** (often driven by `MS2`):
   - If any paid milestone lacks a revenue journal → `RECORD_REVENUE_MS2` (or `VERIFY_REVENUE_ONLY` if journals exist)
   - If no missing journals and no unpaid issues → `NO_ACCOUNTING_ACTION`
9. Determine **collection actions**:
   - If any milestone is unpaid and `due_date` is in the future (or null) → `MONITOR_UNPAID_NOT_DUE`
   - If any milestone is unpaid and `due_date` is in the past → `SEND_COLLECTION_NOTICE`
   - If all paid → `NO_COLLECTION_ACTION`
10. **Fetch the Event** and **Voucher** if referenced in the prompt.
    - `event_status` from API (`SCHEDULED`, `ACTIVE`, `COMPLETED`, `CANCELLED`, `UNKNOWN`)
    - `voucher_status` from API (`ACTIVE`, `DRAFT`, `EXPIRED`, `DISABLED`, `UNKNOWN`)
    - Invite action: if `SCHEDULED` + voucher `ACTIVE` → `SEND_BRIEFING_INVITE` / `SEND_EVENT_INVITATION`; if `COMPLETED` → `VERIFY_INVITE_SENT`; else → `NO_INVITE_ACTION`.

---

## Step 4: Populate the Answer Template

1. Load `input/payloads/answer_template.json`.
2. Map every fetched/computed value into the corresponding field.
3. **Strictly respect enums** defined in the template (e.g., `PAID | PARTIAL | UNPAID | UNKNOWN`). Do not invent new values.
4. **Currency formatting**: all USD amounts must be numbers with exactly 2 decimal places (e.g., `14500.00`). Do not use strings.
5. **Date formatting**: use `YYYY-MM-DD`.
6. **Booleans**: use JSON `true`/`false`, not strings.
7. **Arrays**: maintain ascending sort order when specified (e.g., milestones by `milestone_id`).
8. Remove any comment or schema annotation from the final output; emit **only** the populated JSON object.

---

## Step 5: Validation Checklist

- [ ] JSON parses without errors.
- [ ] No extra keys outside the template schema.
- [ ] No narrative text outside the JSON object.
- [ ] All monetary values are numeric with 2 decimal places.
- [ ] All dates are `YYYY-MM-DD` strings (or `null` where allowed).
- [ ] All enums match the template exactly (case-sensitive).
- [ ] `opportunity_matches_phase_total` (or similar boolean) is derived from the numeric sum, not assumed.
- [ ] Freight validity relies on API-returned status when available, not purely on date math.
- [ ] Event and voucher invite logic respects both `event_status` and `voucher_status`.

---

## Common Pitfalls

1. **Hard-coding output shape** — Always read `answer_template.json`; templates vary even within the same task family (e.g., train_003 vs. train_005).
2. **Ignoring the API port** — The prompt often references a runner-provided port or `http://127.0.0.1:${PORT}`; substitute the actual value.
3. **Computing freight validity from dates alone** — The API may return an explicit `validity_status` (e.g., `EXPIRED` even when the calendar date has not passed). Prefer API fields.
4. **Mishandling zero-amount milestones** — A milestone with `amount = 0` should usually have `NOT_REQUIRED_UNPAID` recognition status and no collection action.
5. **Missed related entities** — The prompt may explicitly request inclusion of an event and voucher (e.g., `EVT-MERIDIAN-BRIEFING` and `MERIDIANBRIEF50`). Fetch them even if they are not strictly needed for the core reconciliation.
6. **Round-off errors** — Use exact decimal arithmetic or round to 2 decimals at the final step; floating-point drift can cause `opportunity_matches_phase_total` to be `false` when it should be `true`.
