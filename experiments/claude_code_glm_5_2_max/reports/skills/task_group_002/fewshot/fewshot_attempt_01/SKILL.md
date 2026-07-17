# MedBridge Sales Ops — Account-Manager CRM Skill

Transferable operating procedure for two families of account-manager work against the
MedBridge Sales Ops remote API: **QUOTE decision packages** (reconcile a customer
RFQ/quote against catalog + freight + policies) and **RECONCILIATION packages**
(reconcile a won opportunity against invoices/payments/revenue-journals/events/vouchers).

The rules below are derived from the 5 train tasks and the live API records behind them.
Apply them to unseen tasks; do not memorize train answers.

---

## 0. Output discipline (applies to every task)

- Return **only valid JSON** matching `input/payloads/answer_template.json` exactly:
  same field names, same nesting, same key order, **controlled enum values only**.
- No markdown fences, no prose, no trailing commas, no comments.
- **Money** = USD dollars with **2 decimals** (e.g. `50000.00`, `42480.0`), NOT integer
  cents — despite any "cent-level" wording in a prompt, the template declares
  "USD currency with 2 decimals" and the gold uses dollar amounts.
- **Dates** = ISO `YYYY-MM-DD`. **Nulls** = JSON `null` (not `""`, not omitted).
- **IDs** = stable record IDs exactly as they appear in the API (`Q-TR-WC-1187`,
  `CUST-HHA`, `OPP-TR-HELIOS`, `EVT-MERIDIAN-BRIEFING`, etc.).
- Reconcile the prompt's narrative against the API; **trust the API over narrative
  wording** when they conflict, but read the prompt carefully for *which* entity
  (quote id, opportunity id, customer id, product code, quantities, quote date) to
  reconcile. The prompt's confirmed quantity / quote date override stale quote-record
  priors.
- For `customer_name` in a reconciliation, use the **name as given in the task prompt**
  (the account-facing label); cross-check `customer_id` and all financial records
  against the API. (The API legal name can differ from the prompt's display name.)

---

## 1. Remote API usage

Base URL is given by the runner (e.g. `<remote-env-url>`). Call with `curl`,
pipe to `python3 -m json.tool`. All responses are JSON.

Endpoints:
- `GET /health`, `GET /api` (lists collections + endpoints).
- `GET /api/<collection>` — list all records (`{collection, count, records}`).
- `GET /api/<collection>?<key>=<value>` — filter (case-insensitive, nested keys, AND
  together, numeric tolerance 2dp).
- `GET /api/<collection>/<id>` — **detail-by-id ONLY works for** `customers`,
  `products`, `rfqs`, `quotes`, `freight-quotes`, `opportunities`. For
  `invoices`, `payments`, `revenue-journals`, `events`, `vouchers`, `policies` use
  the **list + filter** endpoints (filter by `opportunity_id`, `customer_id`,
  `invoice_id`, `phase_id`, `code`, etc.).
- `GET /api/search?q=<text>` — substring search across ALL collections (≤100 hits).

Collections: `customers`, `products`, `rfqs`, `quotes`, `freight-quotes`, `policies`,
`opportunities`, `invoices`, `payments`, `revenue-journals`, `events`, `vouchers`.

### Filter gotchas (important — these waste calls if missed)
- Products' identifying field is **`code`** (the record `id` equals `code`). Filtering
  by `product_code=` returns nothing; filter by `code=` or use detail-by-id
  `/api/products/<code>`.
- Filter `invoices`, `payments`, `revenue-journals` by `opportunity_id=OPP-...` to
  scope a reconciliation. Also `invoice_id=` on payments/revenue-journals ties a
  payment/journal to a specific invoice.
- `events` and `vouchers` filter by `opportunity_id` or `customer_id`; a voucher's
  `code` is its id.

### ID conventions / distractor records (critical exclusion rule)
- IDs prefixed `TR` (e.g. `Q-TR-WC-1187`, `RFQ-TR-IEHK-204`, `OPP-TR-HELIOS`) are the
  reconcilable train/test entities. IDs prefixed `DIS` are **distractors** — never
  select them.
- In `freight-quotes`, **distractor freight records** have `destination` = `"Distractor
  route"` and `id` starting with `FR-DIS-`. Always **exclude** them. The real freight
  options for a quote have a real city destination and id `FR-<family>-<MODE>`
  (e.g. `FR-WC-AIR`, `FR-LD-ROAD`). Also exclude any record with `status: "mismatch"`.
- In `rfqs`, modules may carry `component_composition_distractors` — these are
  explicitly "for medical review only; do not split into component SKUs."
- Quote records carry `prior_quote_quantity` / `prior_unit_price_usd` and a
  `source_notes` hint (e.g. "catalog tier overrides prior unit price") — the **current
  catalog tier wins**, never the prior price.

---

## 2. Policies (always fetch `/api/policies` and apply)

Eight policy records govern decisions. Map them by `policy_area` / `terms_code`:

| Policy | Rule (transferable) |
|---|---|
| `POL-NEW-CLIENT-PAYMENT` (`PREPAY_100`) | New NGO clients with no credit history → **PREPAY_100** before production release. Trigger: customer `payment_profile = NEW_CLIENT_REVIEW` or `segment = new_ngo`. |
| `POL-RECURRING-NGO-PAYMENT` (`NET_30_AFTER_PO`) | Recurring NGO → **NET_30_AFTER_PO** unless grant terms restrict. |
| `POL-INDICATIVE-EXW` (`EXW_ONLY_EXCLUDE_FREIGHT`) | Indicative quote with **no confirmed destination** → **EXW only, freight excluded**. |
| `POL-FREIGHT-RECONFIRM` (`RECONFIRM_AT_ORDER`) | Freight rates need **reconfirmation at final order**; valid only through `valid_until`. → `freight_reconfirmation_required = true` whenever freight is quoted. |
| `POL-MODULE-GRANULARITY` (`MODULE_LINES`) | Module RFQs quoted at **module line level** — do NOT expand into component SKUs. |
| `POL-REVREC` (`RECOGNIZE_PAID_COMPLETE_MILESTONES`) | When a milestone is complete **and paid**, recognize revenue (deferred → income). Unpaid future milestones stay outstanding and drive collection tasks when due/overdue. Paid milestone with **no revenue journal ⇒ REQUIRED_MISSING / MISSING_REVENUE_JOURNAL**. |
| `POL-QUOTE-VALIDITY` (`QUOTE_VALID_30_DAYS`) | Catalog quote pricing valid **30 days** from quote date; freight may expire sooner. → `offer_validity_days = 30`. |
| `POL-EXW-SCOPE` (`EXW_EXCLUSIONS`) | EXW **excludes** freight, insurance, import duty, customs clearance, last-mile — unless explicitly added as separate options. |

---

## 3. QUOTE tasks — two sub-families

### 3A. Quote revision WITH freight options (template has freight_options + grand totals)

Fetch: `GET /api/quotes/<quote_id>` → `customer_id`, `primary_product_code`,
`confirmed_quantity`, `quote_date`, `incoterm`. Then `GET /api/products/<product_code>`
for price tiers, `GET /api/customers/<customer_id>` for payment profile, and
`GET /api/freight-quotes?quote_id=<quote_id>` (then strip distractors, §1).

**Catalog tier selection.** Products expose `price_tiers: [{min_qty, max_qty,
unit_price_usd, lead_time_days, lead_time_weeks}]` (max_qty `null` = unbounded). Pick the
**single tier where `min_qty <= confirmed_quantity <= max_qty`** (null max = infinity).
Use that tier's `unit_price_usd` and `lead_time_days`; `shelf_life_months` is
product-level (same across tiers). Ignore `prior_unit_price_usd`. Round quantities to
the tier the confirmed quantity falls into.

- `exw_total_usd` = `unit_price_usd × confirmed_quantity` (2dp).
- `grand_total_usd` (per freight option) = `exw_total_usd + freight_cost_usd`.

**Freight option selection.** From the filtered freight records for the quote, keep the
3 canonical modes AIR / SEA / ROAD (real destination, id `FR-<family>-{AIR,SEA,ROAD}`).
Exclude `FR-DIS-*` / `destination="Distractor route"` / `status="mismatch"`. **Include a
stale/expired option** (status `stale` or `valid_until < quote_date`) but **flag it** —
do not drop it. Order: AIR, SEA, ROAD.

**Freight validity & staleness.** Compare each option's `valid_until` to the quote date
and its `status`:
- `VALID` (or `all_freight_options_valid_on_quote_date=true`) when `status="active"`
  AND `valid_until >= quote_date`.
- `STALE` / `source_is_stale=true` / `road_quote_invalid_or_stale=true` when
  `status="stale"` OR `valid_until < quote_date`.
- `freight_reconfirmation_required` = **true** whenever freight is quoted (per
  `POL-FREIGHT-RECONFIRM`), independent of validity.

**Risk mapping — NOTE the two schemas differ:**
- *risk_level / risk_flag schema (one freight template):* `risk_level` =
  `route_risk` uppercased (`LOW`/`MEDIUM`/`HIGH`). `risk_flag`: `NONE` when low;
  `MEDIUM_BORDER_RISK` when notes mention border risk medium; `HIGH_*` when high
  border/customs risk.
- *customs_border_risk schema (another template):* `customs_border_risk` reflects
  **customs/border-specific** exposure in `risk_notes`, NOT the generic `route_risk`.
  `LOW` by default; `HIGH` when notes say "customs risk high"/"border risk high";
  `MEDIUM` when notes say border risk medium. A medium `route_risk` driven by
  transit/shelf-life (not customs) still maps to `customs_border_risk = LOW`.

**Recommended mode decision rule:**
1. Exclude candidates that are STALE or HIGH customs/border risk.
2. Among remaining VALID options, pick the **lowest `grand_total_usd`**.
3. SEA is typically the cheapest valid low/medium-risk option → recommended `SEA`.
   If SEA is stale/high-risk, fall back to the next cheapest valid low-risk mode
   (usually AIR). Both observed revisions recommend `SEA`.

**Payment terms.** Map from customer `payment_profile` + policies:
- `NEW_CLIENT_REVIEW` (new NGO, `is_recurring=false`, `status=prospect`) → `PREPAY_100`.
- `NET_30_AFTER_PO` (recurring) → `NET_30_AFTER_PO`.
- `MILESTONE_BILLING` is for services/reconciliation, not catalog quotes.
`customer_policy` (when the template has it) = uppercased customer segment
(e.g. `recurring_ngo` → `RECURRING_NGO`) / matching policy label.

**quote_basis** controlled values: `EXW` (EXW pricing with freight options shown
separately, one template), `EXW_PLUS_FREIGHT_OPTIONS` (the policy_terms block in another
template), `EXW_ONLY` (freight excluded). Match the token the template demonstrates.

**Field map (revision-with-freight), per template:**
- Quote/pricing header: `quote_id`, `customer_id`, `quote_date`, `product_code`,
  `confirmed_quantity`, `unit_price_usd` (or `catalog_tier` sub-object with
  `min_quantity`/`max_quantity`/`unit_price_usd`/`lead_time_days`/`shelf_life_months`),
  `lead_time_days`, `shelf_life_months`, `quote_basis`, `exw_total_usd`, `payment_terms`.
- Freight options: `freight_id`, `mode` (`AIR`/`SEA`/`ROAD` uppercased — API stores
  lowercase), `freight_cost_usd`, `transit_days` (the record's `transit_days_text`;
  some templates expect the bare min-max range — match the template's shown format),
  `valid_until`, risk fields (per schema above), `grand_total_usd`.
- Policy/controls: `recommended_mode`, `freight_reconfirmation_required`,
  `all_freight_options_valid_on_quote_date` (or `road_quote_invalid_or_stale` +
  `freight_warning` text + `policy_terms.{quote_basis,payment_terms,
  freight_reconfirmation_required}`).

### 3B. Indicative EXW-only module quote (RFQ, no destination, freight excluded)

Fetch: `GET /api/rfqs/<rfq_id>` → `customer_id`, `quote_date`, `requested_modules[]`
(each `product_code` + `quantity`), `incoterm_requested`, `destination`. Then
`GET /api/customers/<customer_id>`, and `GET /api/products/<code>` per requested module.

**Granularity rule (`POL-MODULE-GRANULARITY`):** emit **one line per requested module**,
using the module's `code`, `article_number`, the RFQ-requested `quantity`, and the
matching price tier `unit_price`. **Never expand `components[]` into component lines**,
even though the product record lists them — the RFQ says composition is for medical
review only. Select the tier where `min_qty <= quantity <= max_qty` (single-tier modules
have one tier with `min_qty=1, max_qty=null`).

- `line_total` = `unit_price × quantity` (2dp). `grand_total` = sum of `line_total`s.
- `quote_basis = EXW_ONLY`. `freight_excluded = true` (RFQ has no confirmed
  destination → `POL-INDICATIVE-EXW`).
- `payment_terms`: new NGO → `PREPAY_100` (`POL-NEW-CLIENT-PAYMENT`).
- `offer_validity_days = 30` (`POL-QUOTE-VALIDITY`).
- `who_documentation_required = true` for WHO-standard emergency health kit modules
  (e.g. IEHK family / `family = emergency_health_kit`); these carry WHO documentation.
- `currency = USD`.

**Exclusion watch:** an RFQ may include a `component_composition_distractors` list and
the catalog may contain a *different* RFQ for the same customer (e.g. a budgetary-check
RFQ with different quantities/status `draft`) — reconcile only the RFQ id named in the
prompt, at the module level.

---

## 4. RECONCILIATION tasks — won opportunity + milestones + revenue + events

Fetch: `GET /api/opportunities/<opp_id>` → `customer_id`, `contact`, `stage`,
`won_amount_usd`, `phases[]` (each `phase_id`, `amount_usd`, `completion_date`,
`invoice_id`). Then:
- `GET /api/invoices?opportunity_id=<opp>` (one invoice per milestone phase, keyed by
  `phase_id` / `invoice_id`).
- `GET /api/payments?opportunity_id=<opp>` (ties to invoices via `invoice_id`;
  `status="posted"`).
- `GET /api/revenue-journals?opportunity_id=<opp>` (ties to invoices via `invoice_id` /
  `phase_id`; `status="posted"`; `debit_account="Deferred Revenue"`,
  `credit_account="Implementation Services Revenue"`).
- `GET /api/events?opportunity_id=<opp>` and `GET /api/vouchers?opportunity_id=<opp>`
  (or filter vouchers by `event_id`).
- `GET /api/customers/<customer_id>` for contact + name.

### 4.1 Milestone construction & ordering
Emit milestones as **`MS1`, `MS2`, `MS3`, …** in ascending phase order (one per
opportunity phase / invoice). `phase_number` (when the template has it) = the 1-based
phase index. Each milestone maps to exactly one invoice (by `phase_id`/`invoice_id`).

### 4.2 Payment & invoice state enums
Determine from invoice `paid_amount_usd` vs `amount_usd` and `outstanding_amount_usd`:
- **Fully paid** (`paid_amount >= amount`, `outstanding = 0`, `status="paid"`):
  `payment_status/payment_state = PAID`, `amount_paid = amount`, `amount_unpaid = 0`,
  `due_date = null` (paid milestones have **no due date**).
- **Partial** (`0 < paid_amount < amount`): `PARTIAL`, `amount_paid`/`amount_unpaid`
  split, `due_date` retained.
- **Unpaid** (`paid_amount = 0`, `status="unpaid"`): `UNPAID`, `amount_paid = 0`,
  `amount_unpaid = amount`, `due_date` retained.

`invoice_state` enum (where the template separates it): map invoice `status`:
`"paid"` → `PAID`; `"unpaid"` → `OPEN`; `"void"` → `VOID`; unknown → `UNKNOWN`.

### 4.3 due_date rule
- **Paid in full** → `due_date = null`.
- **Unpaid/Partial** → `due_date = invoice.due_date` (the invoice record's contractual
  due date). The collection follow-up task's `due_date` mirrors this milestone due date.
- If an unpaid invoice is **already due/overdue as of the as-of date**, escalate the
  collection action (§4.5) and set the collection task due date to the invoice due date
  (or a near-term forward target if past due).

### 4.4 Revenue recognition status (per milestone)
For each milestone, classify by paid-state AND presence of a matching revenue journal
(a `revenue-journals` record with the same `invoice_id`/`phase_id`, `status="posted"`):
- Paid **and** has a revenue journal → `RECOGNIZED`.
- Paid **and NO** revenue journal → `REQUIRED_MISSING` (one template) /
  `MISSING_REVENUE_JOURNAL` (the other template). This triggers an accounting action
  (§4.6).
- Unpaid/partial → `NOT_REQUIRED_UNPAID`.
- Unknown/incomplete data → `UNKNOWN` (only where the enum allows).

**Overall recognition block (when the template has one):**
- `recognition_status`:
  - `COMPLETE_FOR_PAID_MILESTONES` — every paid milestone has a revenue journal.
  - `MISSING_FOR_PAID_MILESTONES` — at least one paid milestone lacks a journal.
  - `NOT_REQUIRED` — no paid milestones to recognize.
- `recognized_milestones` = list of MS ids that are RECOGNIZED.
- `missing_required_milestones` = list of paid MS ids missing a journal.
- `recognized_amount` = sum of amounts of recognized milestones (2dp).

### 4.5 Collection action routing
Use the as-of date (the prompt's stated current date, e.g. `2026-06-01`; if unstated,
infer from the prompt context). For each **unpaid/partial** milestone:
- **Not yet due** (`invoice.due_date > as_of`): `MONITOR_UNPAID_NOT_DUE`,
  `owner_queue = ACCOUNT_MANAGEMENT`. (No dunning yet.)
- **Due or overdue** (`invoice.due_date <= as_of`): `SEND_COLLECTION_NOTICE`,
  `owner_queue = COLLECTIONS`.
- If no unpaid milestone exists: `NO_COLLECTION_ACTION` / `NONE`.
- Templates with a single collection `next_action` (`COLLECT_UNPAID_MILESTONE`) route
  one collection task per unpaid milestone (owner is implicit/the account contact).

`collection_task` carries: `action`, `milestone_id` (the unpaid MS), `amount` =
unpaid amount, `due_date` = milestone due date, `owner_queue`, `contact_name` =
opportunity contact.

### 4.6 Accounting action routing (revenue recognition)
- If a **paid** milestone is missing its revenue journal → record revenue for it:
  - `primary_accounting_action` / `accounting_action.action` =
    `RECORD_REVENUE_MS<N>` (e.g. `RECORD_REVENUE_MS2`).
  - `milestone_id = MS<N>`, `amount` = milestone amount.
  - `debit_account = DEFERRED_REVENUE`, `credit_account =
    IMPLEMENTATION_SERVICES_REVENUE` (mirrors the posted journal pattern).
  - `owner_queue = ACCOUNTING`.
- If all paid milestones are already recognized → `VERIFY_REVENUE_ONLY` (verify
  journals exist) or `NO_ACCOUNTING_ACTION`, `milestone_id = NONE`, accounts `NONE`,
  owner `ACCOUNTING`/`NONE`.
- `NO_ACCOUNTING_ACTION` when nothing requires recording/verifying.

### 4.7 Event & voucher linkage, invite action
From the event record (`GET /api/events?opportunity_id=...`) and its voucher
(`vouchers?event_id=...` or match `voucher_code` on the event):
- `event_id`, `event_date`, `event_status`: map event `status` →
  `"scheduled"` → `SCHEDULED`; `"confirmed"`/`"live"` → `ACTIVE`; `"completed"` →
  `COMPLETED`; `"cancelled"` → `CANCELLED`; `"tentative"`/unknown → `UNKNOWN`.
- voucher fields: `voucher_code`, `voucher_status` (voucher `status` uppercased:
  `ACTIVE`/`DRAFT`/`EXPIRED`/`DISABLED`/`UNKNOWN`), `discount_amount` /
  `voucher_discount` = voucher `discount_percent` (as a number, e.g. `50.00`, `100.00`),
  `max_uses` / `voucher_max_uses` = voucher `max_redemptions`.

**invite_action** decision:
- `SEND_BRIEFING_INVITE` (or `SEND_EVENT_INVITATION`) when the event is
  scheduled/active, in the future relative to as-of, and the voucher is active → emit
  an invite task.
- `VERIFY_INVITE_SENT` when an invite should already have gone out (e.g. event imminent
  / already started) — verify rather than re-send.
- `NO_INVITE_ACTION` when the event is cancelled/completed or the voucher expired/
  disabled.

**invite task:** `event_id`, `voucher_code`, `owner_queue = ACCOUNT_MANAGEMENT`
(matches the event's `follow_up_owner = "Account Management"`), `contact_name` =
opportunity contact, `customer_id`. For templates with an invite `due_date`, set it to
**`event_date − 21 days`** (send ~3 weeks ahead).

### 4.8 follow_up_tasks (combined collection + event invitation)
When the template uses a flat `follow_up_tasks[]` array, emit:
- One `COLLECTION` task per unpaid milestone: `task_type = COLLECTION`,
  `task_title = "Milestone <N> collection - <customer_name>"`, `next_action =
  COLLECT_UNPAID_MILESTONE`, `milestone_id`, `amount_due`, `due_date` = milestone due
  date, `event_id = null`, `voucher_code = null`.
- One `EVENT_INVITATION` task: `task_type = EVENT_INVITATION`, `task_title =
  "Send <event> invite - <customer_name>"`, `next_action = SEND_EVENT_INVITATION`,
  `milestone_id = null`, `amount_due = null`, `due_date = event_date − 21`,
  `event_id`, `voucher_code`.

Every task links `linked_customer_id`, `linked_opportunity_id`, and `contact_name`
(named in the prompt, e.g. "Mara Okafor", "Daniel Rees") — the contact is tied to all
follow-up work.

### 4.9 Totals & match checks
- `won_amount` / `won_amount_usd` = opportunity `won_amount_usd`.
- `phase_total_amount` / milestone sum = sum of all phase `amount_usd`.
- `opportunity_matches_milestones` / `opportunity_matches_phase_total` = `true` iff
  `won_amount_usd == sum(phase amounts)`.
- `total_paid_amount` = sum of `paid_amount` across milestones.
- `outstanding_balance` = sum of `amount_unpaid` across milestones (should equal
  opportunity `outstanding_amount_usd`).
- `as_of_date` = the prompt's stated current date.

### 4.10 Enum reference (reconciliation)
- `opportunity_stage` / `stage`: `WON` (from `closed_won`), `OPEN`, `LOST`.
- `payment_status` / `payment_state`: `PAID` | `PARTIAL` | `UNPAID` (| `UNKNOWN`).
- `invoice_state`: `PAID` | `OPEN` | `VOID` | `UNKNOWN`.
- per-milestone `recognition_status`: `RECOGNIZED` | `REQUIRED_MISSING` |
  `NOT_REQUIRED_UNPAID` (template A) **or** `RECOGNIZED` | `MISSING_REVENUE_JOURNAL` |
  `NOT_REQUIRED_UNPAID` | `UNKNOWN` (template B) — **use the exact enum the template
  declares**.
- overall `recognition_status`: `COMPLETE_FOR_PAID_MILESTONES` |
  `MISSING_FOR_PAID_MILESTONES` | `NOT_REQUIRED`.
- `primary_accounting_action` / accounting `action`: `RECORD_REVENUE_MS<N>` |
  `VERIFY_REVENUE_ONLY` | `NO_ACCOUNTING_ACTION`.
- `collection_action`: `MONITOR_UNPAID_NOT_DUE` | `SEND_COLLECTION_NOTICE` |
  `NO_COLLECTION_ACTION`.
- `invite_action`: `SEND_BRIEFING_INVITE` | `VERIFY_INVITE_SENT` | `NO_INVITE_ACTION`
  (template B) / `SEND_EVENT_INVITATION` (template A `next_action`).
- `task_type`: `COLLECTION` | `EVENT_INVITATION`.
- `debit_account`: `DEFERRED_REVENUE` | `ACCOUNTS_RECEIVABLE` | `CASH` | `NONE`.
- `credit_account`: `IMPLEMENTATION_SERVICES_REVENUE` | `DEFERRED_REVENUE` |
  `ACCOUNTS_RECEIVABLE` | `NONE`.
- `owner_queue`: `ACCOUNTING` | `ACCOUNT_MANAGEMENT` | `COLLECTIONS` | `EVENTS` |
  `NONE`.
- `event_status`: `SCHEDULED` | `ACTIVE` | `COMPLETED` | `CANCELLED` | `UNKNOWN`.
- `voucher_status`: `ACTIVE` | `DRAFT` | `EXPIRED` | `DISABLED` | `UNKNOWN`.

---

## 5. Common misjudgments & exclusion rules (do NOT do these)

1. **Expanding module RFQs into component lines.** IEHK/WHO modules list `components[]`
   (and `component_composition_distractors`); keep one line per module. Component
   detail is medical-review-only.
2. **Including freight on an EXW-only indicative quote.** No confirmed destination ⇒
   `EXW_ONLY`, `freight_excluded = true`, no freight_options block at all.
3. **Using the prior unit price.** Quote revisions carry `prior_unit_price_usd`; the
   **current catalog tier** for the confirmed quantity overrides it.
4. **Selecting distractor freight.** `FR-DIS-*` / `destination="Distractor route"` /
   `status="mismatch"` are never quoted — even if `status` looks "active".
5. **Dropping a stale/expired freight option.** Include it but flag `STALE` /
   `source_is_stale=true` / `road_quote_invalid_or_stale=true` + a `freight_warning`.
6. **Treating `customs_border_risk` as `route_risk`.** A medium route risk driven by
   shelf-life/transit is still `customs_border_risk = LOW`; only explicit customs/border
   notes raise it.
7. **Keeping a due_date on a paid milestone.** Fully paid ⇒ `due_date = null`.
8. **Marking a paid milestone RECOGNIZED without a revenue journal.** Paid + no
   `revenue-journals` record ⇒ `REQUIRED_MISSING` / `MISSING_REVENUE_JOURNAL` and a
   `RECORD_REVENUE_MS<N>` accounting action (`DEFERRED_REVENUE` →
   `IMPLEMENTATION_SERVICES_REVENUE`, owner `ACCOUNTING`).
9. **Sending a collection notice on a not-yet-due invoice.** `due_date > as_of` ⇒
   `MONITOR_UNPAID_NOT_DUE` (owner `ACCOUNT_MANAGEMENT`), not `SEND_COLLECTION_NOTICE`.
10. **Recommending a stale/high-risk mode.** Exclude stale and HIGH-customs options
    before picking the lowest `grand_total`; default cost-effective choice is `SEA`.
11. **Setting `freight_reconfirmation_required = false`.** It is `true` whenever
    freight options are quoted (policy `POL-FREIGHT-RECONFIRM`).
12. **Wrong money type.** Use 2-decimal USD dollar amounts, not integer cents.
13. **Pulling the wrong RFQ/quote for a customer.** Several customers have multiple
    RFQs (incl. draft/budgetary distractors). Reconcile only the id named in the prompt.
14. **Forgetting WHO documentation.** IEHK / `emergency_health_kit` modules ⇒
    `who_documentation_required = true`.
15. **Mismatching enum tokens across templates.** Two reconciliation templates use
    different recognition tokens (`REQUIRED_MISSING` vs `MISSING_REVENUE_JOURNAL`) and
    different collection/invite tokens (`COLLECT_UNPAID_MILESTONE`/
    `SEND_EVENT_INVITATION` vs `MONITOR_UNPAID_NOT_DUE`/`SEND_COLLECTION_NOTICE`/
    `SEND_BRIEFING_INVITE`). Always copy the enum values **declared in the specific
    answer_template.json** for the task at hand.

---

## 6. Worked decision flow (apply per task)

1. Identify the family (quote vs reconciliation) and the exact entity id(s) from the
   prompt.
2. Fetch the named record(s) by id; fetch related collections via filter; fetch
   `/api/policies`.
3. Reconcile quantities/date against the API; select catalog tier / milestones /
   freight options; classify states using the rules above.
4. Map every field to the **exact** template field names + enum tokens.
5. Compute money (2dp), dates (ISO), totals, and outstanding/recognized amounts.
6. Emit **one JSON object** only — no prose, no fences — matching
   `input/payloads/answer_template.json`.
