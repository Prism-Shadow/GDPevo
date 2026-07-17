# MedBridge Sales Ops — Quote, Reconciliation & Account Decision Packages

## Environment entrypoint

The MedBridge Sales Ops API is always accessed through the task environment base URL.
When the task text mentions `API_BASE_URL`, `BASE_URL`, `localhost`, `127.0.0.1`, or
`env/setup.sh`, substitute the remote URL declared in the runner's environment access
configuration.  Do **not** start a local env or read an `env/` source directory.

---

## Task taxonomy

MedBridge tasks fall into three patterns.  Identify which one applies before calling
any API endpoint.

### Pattern A — Quote decision package (EXW + freight comparison)

**Recognised by:** a quote ID like `Q-TR-*`, a product code, a confirmed quantity,
and a request for "EXW pricing" plus "freight options" or "transport comparison."

**API endpoints to call (in order):**

1. **Customer record** — resolve the customer ID from the prompt or quote context.
2. **Quote / opportunity** — fetch the quote by ID; confirm `quote_date`, product,
   quantity, and quote basis (`EXW`).
3. **Product catalog** — get the product's unit price and tier (volume bands),
   lead time, and shelf life.
4. **Freight records** — fetch all freight options (`AIR`, `SEA`, `ROAD`) for the
   product or product family.
5. **Policy records** — fetch the customer's account policy (payment terms, NGO
   status, freight reconfirmation flag).

**Calculation rules:**

| Field | Formula |
|---|---|
| `unit_price_usd` | From the catalog tier whose `min_quantity ≤ confirmed_quantity ≤ max_quantity` |
| `exw_total_usd` | `unit_price_usd × confirmed_quantity` |
| `grand_total_usd` (per freight option) | `exw_total_usd + freight_cost_usd` |

**Freight validity check:**
- Compare `valid_until` against `quote_date`.
- If `valid_until < quote_date` → `validity_status: "STALE"`, `source_is_stale: true`.
- If `valid_until ≥ quote_date` → `validity_status: "VALID"`, `source_is_stale: false`.

**Route risk flags:**
- `customs_border_risk`: `"LOW"`, `"MEDIUM"`, or `"HIGH"` — read from the freight
  record's risk assessment.
- `risk_flag`: `"NONE"` when low, `"MEDIUM_BORDER_RISK"` when medium, or a
  descriptive flag from the API payload.
- A road freight option whose `valid_until` is before `quote_date` **and** has
  `HIGH` border risk must trigger `road_quote_invalid_or_stale: true` and a
  human-readable `freight_warning`.

**Recommended transport mode:**
- Default to `"SEA"` when it is valid (not stale) and has low risk — it offers the
  best cost/safety balance.
- If SEA is stale or high-risk, fall back to `"AIR"` if valid.
- Never recommend a stale or high-risk option.

**Freight reconfirmation:**
- `freight_reconfirmation_required: true` whenever **any** freight option is stale
  or has risk level `MEDIUM` or above.

**Payment terms:**
- Recurring NGO accounts → `"NET_30_AFTER_PO"`.
- New NGO / first-time accounts → `"PREPAY_100"`.
- Read the actual term string from the customer policy record — do not hardcode.

**Client warnings (Pattern A variant — see train 004):**
- When the output template includes a `client_warnings` block, include:
  - `road_quote_invalid_or_stale` (boolean).
  - `freight_warning` (human-readable sentence naming the stale freight ID,
    its expiry date, and risk level).
  - `policy_terms` repeating `quote_basis`, `payment_terms`, and
    `freight_reconfirmation_required`.

---

### Pattern B — EXW-only module / RFQ quote (no freight)

**Recognised by:** an RFQ ID like `RFQ-TR-*`, module product codes (e.g.
`IEHK-*`), an explicit instruction to quote EXW only with freight excluded,
and often a "new NGO account."

**API endpoints to call (in order):**

1. **Customer record** — confirm the customer exists and is classified correctly
   (new vs recurring NGO).
2. **RFQ / quote record** — fetch by RFQ ID; get the requested modules and
   their quantities.
3. **Product catalog** — for each module, retrieve `article_number`, `unit_price`,
   `lead_time_days`, and `shelf_life_months`.
4. **Policy records** — get payment terms, offer validity, and WHO documentation
   requirements.

**Critical rule — module level only:**
- Even if the API returns sub-components or BOM details for a module, quote at
  the **module level** as requested by the customer.  Do not explode modules into
  their components in the line items.

**Calculation rules:**

| Field | Formula |
|---|---|
| `line_total` | `unit_price × quantity` |
| `grand_total` | `sum of all line_item.line_total` |

**Fixed controls for Pattern B:**
- `currency`: always `"USD"`.
- `quote_basis`: `"EXW_ONLY"` (not `"EXW"` — the `_ONLY` suffix is significant).
- `freight_excluded`: `true`.
- `payment_terms`: `"PREPAY_100"` for new NGO accounts.
- `offer_validity_days`: `30` (standard for new accounts).
- `who_documentation_required`: `true` for NGO/health-sector accounts.

---

### Pattern C — Account / engagement reconciliation

**Recognised by:** an opportunity ID like `OPP-TR-*`, a request to "reconcile"
or verify milestone invoices, payment state, revenue recognition, and often a
linked event/voucher.

**API endpoints to call (in order):**

1. **CRM opportunity** — fetch by `OPP-TR-*` ID; confirm stage (`WON`), won
   amount, and linked customer.
2. **Customer record** — verify customer name, ID, and primary contact.
3. **Milestone invoices** — fetch all milestones for the opportunity (typically
   `MS1`, `MS2`, `MS3`).
4. **Payments / receivables** — for each milestone, get payment state, amount
   paid, amount unpaid, and due date.
5. **Revenue recognition journal** — check which paid milestones have a
   corresponding revenue recognition entry.
6. **Event / voucher** — fetch the linked event by ID, confirm status, and
   retrieve the attached voucher details.

**Reconciliation checks:**

1. **Opportunity total vs milestone sum:**
   - `phase_total_amount = sum of all milestone.amount`
   - `opportunity_matches_phase_total = (won_amount == phase_total_amount)`

2. **Outstanding balance:**
   - `outstanding_balance = sum of all milestone.amount_unpaid`
   - Also verify: `won_amount - total_paid_amount == outstanding_balance`

3. **Revenue recognition by milestone:**

   | Milestone state | Recognition status |
   |---|---|
   | `PAID` + journal entry exists | `"RECOGNIZED"` |
   | `PAID` + journal entry missing | `"MISSING_REVENUE_JOURNAL"` |
   | `UNPAID` | `"NOT_REQUIRED_UNPAID"` |

4. **Overall recognition status:**
   - If **all** PAID milestones are RECOGNIZED → `"COMPLETE_FOR_PAID_MILESTONES"`.
   - If **any** PAID milestone is MISSING → `"MISSING_FOR_PAID_MILESTONES"`.

**Invoice state vs payment state — important distinction:**
- `invoice_state` reflects whether an invoice was issued (`"PAID"` / `"OPEN"` /
  `"VOID"` / `"UNKNOWN"`).  An invoice can be `"OPEN"` (issued but not yet settled)
  while the payment is still processing.
- `payment_state` reflects actual cash received (`"PAID"` / `"PARTIAL"` /
  `"UNPAID"` / `"UNKNOWN"`).
- These are independent dimensions — do not conflate them.

**Follow-up task generation:**

| Condition | Task |
|---|---|
| Any milestone is UNPAID with a future `due_date` | `COLLECTION` → `MONITOR_UNPAID_NOT_DUE` (monitor, don't collect yet) |
| Any milestone is UNPAID with a past `due_date` | `COLLECTION` → `COLLECT_UNPAID_MILESTONE` (active collection) |
| Event is SCHEDULED or ACTIVE | `EVENT_INVITATION` → `SEND_EVENT_INVITATION` (due ~3 weeks before event) |

**Accounting journal entries (Pattern C variant — train 005):**
- When a PAID milestone lacks a revenue recognition entry, generate:
  - `debit_account: "DEFERRED_REVENUE"`
  - `credit_account: "IMPLEMENTATION_SERVICES_REVENUE"`
  - `owner_queue: "ACCOUNTING"`
- When all paid milestones ARE recognized → `primary_accounting_action: "VERIFY_REVENUE_ONLY"`.

**Due-date logic for follow-up tasks:**
- Collection tasks: use the milestone's `due_date`.
- Event invitation tasks: use **21 days before** the event date (rounded to the
  nearest sensible business day; the examples show exact dates — prefer the date
  the API or calculation yields).

---

## Cross-cutting conventions

### Money
- All monetary values are in **USD** with **two decimal places** (cents).
- Use `float` / `number` type in JSON, not strings.
- Nullable money fields use `null` (not `0.0` and not `"N/A"`).

### Dates
- All dates are **ISO 8601** `YYYY-MM-DD` strings.
- Nullable date fields use `null` (not empty string, not `"0000-00-00"`).
- `quote_date` is the business date the customer confirmed — treat it as "today"
  for validity comparisons.

### IDs
- Use the **exact record IDs** returned by the API — do not synthesise, truncate,
  or guess IDs.
- Quote IDs: `Q-TR-*`
- RFQ IDs: `RFQ-TR-*`
- Opportunity IDs: `OPP-TR-*`
- Customer IDs: `CUST-*`
- Freight IDs: `FR-*-AIR`, `FR-*-SEA`, `FR-*-ROAD`
- Event IDs: `EVT-*-*`
- Voucher codes: as returned by the event/voucher endpoint.

### Enums — use exact controlled values
- The answer template declares the permitted enum values in comments
  (e.g. `"enum: WON | OPEN | LOST"`).  Match them **exactly**, including case.
- Do not invent new status values.  If the API returns a status that doesn't
  map cleanly to an enum slot, pick the closest match from the template.

### Output format
- Return **only** valid JSON matching the `input/payloads/answer_template.json`
  structure.
- No markdown fences, no explanatory prose, no trailing text.
- Fill **every** field in the template — no field left as a placeholder.

---

## Common pitfalls

1. **Wrong tier selected for volume pricing.**  A product at 1000 units may fall
   into the 900–1199 band, not the 500–899 band or the 1200+ band.  Always check
   `min_quantity ≤ confirmed_quantity ≤ max_quantity`.

2. **Confusing `EXW` with `EXW_ONLY`.**  `EXW` means "pricing is EXW but freight
   will be compared."  `EXW_ONLY` means "no freight at all — do not fetch or
   include freight records."

3. **Stale freight not flagged.**  If `valid_until < quote_date`, the freight
   option must be marked stale/invalid.  This is the single most common omission.

4. **Forgetting to sum milestone amounts.**  `phase_total_amount` and
   `outstanding_balance` must be computed by summing the individual milestone
   fields — they are not a separate API field.

5. **Invoice state vs payment state confusion.**  A milestone can have
   `invoice_state: "PAID"` (the invoice was issued and marked paid) but
   `payment_state: "PAID"` (cash received) — these should normally agree for
   settled milestones.  When they disagree, reflect both accurately.

6. **Revenue recognition for unpaid milestones.**  An UNPAID milestone never
   requires revenue recognition — its status is always `"NOT_REQUIRED_UNPAID"`,
   never `"MISSING_REVENUE_JOURNAL"`.

7. **Contact linking.**  The contact named in the prompt must appear in every
   follow-up task, the account_status/engagement_reconciliation block, and any
   invite or collection task.  Verify the contact is linked to the correct
   customer and opportunity in the API response.

8. **New NGO vs recurring NGO payment terms.**  New/first-time NGO accounts get
   `PREPAY_100`.  Recurring NGO accounts with established history get
   `NET_30_AFTER_PO`.  Verify by checking the customer's account age or policy
   record — don't assume.

9. **Freight reconfirmation flag.**  Set to `true` when ANY freight option is
   stale OR has medium-or-higher risk.  Even one bad option triggers this — it
   doesn't require all options to be problematic.

10. **Event invitation lead time.**  The invitation task's `due_date` should
    allow reasonable lead time before the event.  The train examples show ~3
    weeks before the event date — apply the same logic but use the actual date
    the API or calculation produces.

---

## API call order (all patterns)

Always follow this dependency order — later calls often need IDs from earlier
responses:

```
1. Customer / account record
2. Quote / RFQ / Opportunity record
3. Product catalog (for quote tasks) or Milestone invoices (for reconciliation tasks)
4. Freight records (Pattern A only)
5. Policy / payment terms
6. Event / voucher (Pattern C only)
7. Revenue recognition journal (Pattern C only)
```

If an upstream call fails or returns no record, do not proceed to dependent
calls — report the gap in the output (use `null` for nullable fields, or the
closest error-indicating enum value).
