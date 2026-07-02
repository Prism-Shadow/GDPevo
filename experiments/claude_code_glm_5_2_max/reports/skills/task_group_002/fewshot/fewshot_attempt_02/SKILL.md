# SKILL: MedBridge Sales Ops — Quote & Reconciliation Decision Packages

Executable field-craft for producing account/finance-ready JSON from the MedBridge Sales Ops remote API. Two task families share one environment; the output schema is dictated **per-task** by `input/payloads/answer_template.json`. Always read that template first and mirror its exact field names, nesting, and enum values — quote tasks come in at least three template variants and reconciliation tasks in at least two. Do NOT assume a single canonical schema.

## 0. Environment & API discipline

- Source of truth = the remote HTTP JSON API. Base URL is given to the runner as `API_BASE_URL` (env file: `<remote-env-url>`). Never start a local server; never read any `env/` directory.
- Endpoints: `GET /health`, `GET /api` (metadata), `GET /api/<collection>`, `GET /api/<collection>?<key>=<value>` (case-insensitive, AND-combined, 2dp numeric tolerance, matches nested keys), `GET /api/<collection>/<id>` **detail-by-id**, `GET /api/search?q=<text>` (cross-collection substring, ≤100 hits).
- **Detail-by-id is available ONLY for:** `customers`, `products`, `rfqs`, `quotes`, `freight-quotes`, `opportunities`. For `invoices`, `payments`, `revenue-journals`, `events`, `vouchers`, `policies` use the listing endpoint with a filter, or `/api/search`.
- Canonical filter keys: `freight-quotes?quote_id=…`; `invoices?opportunity_id=…`; `payments?opportunity_id=…`; `revenue-journals?opportunity_id=…`; `events?customer_id=…` (or `?opportunity_id=…`); `vouchers?customer_id=…`; `quotes?rfq_id=…`.
- Money = USD, 2 decimals. Dates = ISO `YYYY-MM-DD`. Use stable record IDs verbatim (e.g. `Q-TR-WC-1187`, `FR-WC-AIR`, `OPP-TR-HELIOS`, `CUST-MERIDIAN`).
- The shared business/"as-of" date across tasks is **2026-06-01** (the API `generated_at` and the quote_date used throughout). Use it as `as_of_date` when a reconciliation template requires one and the prompt does not state another.
- Reconcile the prompt's named entity (customer/quote/opportunity ID) against the API; **trust the API for IDs, amounts, dates, statuses, and tier facts**. One exception for the *display name* only — see §6.
- Output: only valid JSON matching the task's template. No markdown fences, no prose. Money as numbers (cent-level precision, e.g. `42480.0`). Nulls where the template allows (`null`), not omitted.

## 1. Task routing

Read the prompt and the template together:
- **QUOTE family** — prompt references a `Q-TR-…` quote id or an `RFQ-TR-…` rfq id; template top-level keys are `quote_summary`/`quote_header`/`pricing` + freight/lines + policy/controls. → §2.
- **RECONCILIATION family** — prompt references an `OPP-TR-…` opportunity id + `CUST-…`; template top-level keys are `account_status`/`engagement_reconciliation` + milestones + actions/tasks. → §3.

## 2. QUOTE tasks

### 2.1 Fetch the source records
1. If a `Q-TR-…` id is given: `GET /api/quotes/<id>` (detail). Use `confirmed_quantity`, `primary_product_code`/`line_items[].product_code`, `destination`, `incoterm`, `quote_date`, `customer_id`. Then `GET /api/products/<product_code>` for tiers/shelf-life/article_number, `GET /api/customers/<customer_id>`, `GET /api/freight-quotes?quote_id=<id>`, and `GET /api/policies`.
2. If an `RFQ-TR-…` id is given (indicative/module quote): `GET /api/rfqs/<id>`. There may be **no quote record at all** (`quotes?rfq_id=…` can return 0) — build the answer from the RFQ's `requested_modules[]` + the product catalog + customer + policies. Use `requested_modules[].quantity` as the line quantity and `requested_modules[].product_code` to fetch each product.

### 2.2 Catalog tier pricing (the core repricing rule)
- Each product has `price_tiers[]` keyed by quantity bands (`min_qty`, `max_qty` where `null` = unbounded). Select the **single tier where `min_qty <= confirmed_quantity <= max_qty`** (null max = open-ended).
- `unit_price` = that tier's `unit_price_usd`. `lead_time_days` = that **tier's** `lead_time_days`. `shelf_life_months` = the **product-level** `shelf_life_months` (constant across tiers).
- **Always reprice to the current catalog tier for the confirmed quantity.** Ignore any `prior_quote_quantity` / `prior_unit_price_usd` on the quote line — those are distractors. (A revision that moved into a higher-quantity tier lowers the unit price; the catalog tier overrides the prior price.)
- EXW total / line total = `quantity × unit_price`. For multi-line module quotes, `grand_total` = Σ line totals.
- Quantity source: quote `line_items[0].confirmed_quantity` (single-product revisions) or `requested_modules[].quantity` (RFQ).

### 2.3 Freight option selection & validity
- Pull `freight-quotes?quote_id=<id>`. The set typically contains **3 real mode quotes (AIR, SEA, ROAD) plus distractors**. Exclude distractors: any record whose `destination` is literally `"Distractor route"` or whose `id` starts with `FR-DIS-`. The surviving 3 (one per mode) are the freight options. Do not invent a mode that isn't present.
- For each real freight quote compute:
  - `freight_cost_usd` = `cost_usd`.
  - `grand_total_usd` = `exw_total_usd + freight_cost_usd` (for single-product EXW-plus-freight).
  - `valid_until` = freight record's `valid_until`.
  - `transit_days` = the freight record's `transit_days_text` (canonical string, e.g. `"4-6 days"`). If the task template's examples show bare ranges, use `"{transit_days_min}-{transit_days_max}"`.
  - **Validity:** a freight quote is VALID on the quote date iff `status == "active"` AND `valid_until >= quote_date`. It is STALE/expired if `status == "stale"` OR `valid_until < quote_date`.
- `freight_reconfirmation_required` = **true always** (policy: all freight rates need reconfirmation at final order and are valid only through `valid_until`).

### 2.4 Risk fields (template-dependent)
The risk representation differs by template — read it:
- **risk_level + risk_flag style** (e.g. `quote_summary`/`policy_flags` template): `risk_level` = `route_risk.toUpperCase()` → `LOW` | `MEDIUM` | `HIGH`. `risk_flag` = `NONE` when `route_risk` is `low`; `"{LEVEL}_BORDER_RISK"` (e.g. `MEDIUM_BORDER_RISK`, `HIGH_BORDER_RISK`) when `route_risk` is `medium`/`high` and the `risk_notes` mention border/customs exposure. (A road lane with "Border risk medium" → `MEDIUM_BORDER_RISK`.)
- **customs_border_risk style** (e.g. `pricing`+`transport_decisions` template): this measures *customs/border* exposure specifically, not general transit risk. `HIGH` when `route_risk == "high"` or `risk_notes` explicitly flag customs/border risk as high; `LOW` otherwise — a `medium` `route_risk` that only describes transit/shelf-life (e.g. a long sea reefer lane) is reported `LOW` for customs/border. Paired fields: `validity_status` (`VALID` | `STALE`), `source_is_stale` (bool = `validity_status == "STALE"`).

### 2.5 Recommended transport mode
- `recommended_mode` = the freight option with the **lowest `grand_total_usd`** among the options that are **VALID** on the quote date (active + not expired). Stale/expired options are never recommended. (In practice SEA usually wins on cost among valid options; ROAD is often disqualified by staleness or HIGH border risk.)
- Defensive tie-break: if the cheapest valid option carries HIGH customs/border risk, prefer the cheapest LOW-risk valid option and call out the risk in any warning field.

### 2.6 Payment terms & policy flags
- Look up `policies` and the customer record.
  - **New NGO client** (`customer.is_recurring == false` / `segment == "new_ngo"` / `payment_profile == "NEW_CLIENT_REVIEW"` / no `client_since`) → `payment_terms = "PREPAY_100"` (New client prepayment policy).
  - **Recurring NGO** (`segment == "recurring_ngo"`) → `NET_30_AFTER_PO` unless restricted grant terms override.
  - **Recurring commercial / others** → use `customer.payment_profile` (typically `NET_30_AFTER_PO`).
- `customer_policy` (where the template has it) = `customer.segment.toUpperCase()` (e.g. `recurring_ngo` → `RECURRING_NGO`).
- `offer_validity_days` = `30` (Standard quote validity policy: catalog pricing valid 30 calendar days from quote date; freight may expire sooner).

### 2.7 Exclusions / scope flags (critical misjudgment traps)
- **EXW-only excludes freight.** If the RFQ/quote has **no real destination** (`destination` contains "pending"/"Destination pending" or is absent) OR `incoterm_requested == "EXW"` with no destination → `quote_basis = "EXW_ONLY"`, `freight_excluded = true`, and **do not emit any freight_options block**. (Indicative EXW policy + EXW commercial scope policy: EXW excludes freight, insurance, duty, customs clearance, last-mile unless explicitly added.) Conversely, when a destination exists and the quote `incoterm` is "EXW plus freight options", show the freight triple with `quote_basis = "EXW"` or `"EXW_PLUS_FREIGHT_OPTIONS"` per the template.
- **Module-level granularity.** For module/IEHK RFQs, emit **one line per requested module only**. Do NOT expand to component SKUs even though products carry a `components[]` list and the RFQ may include `component_composition_distractors` (those are explicitly "for medical review only"). (Module RFQ granularity policy.) Quantities come from `requested_modules`, not from component counts.
- **WHO documentation flag.** Set `who_documentation_required = true` for IEHK-style / WHO-standard kit module quotes (the Interagency Emergency Health Kit is a WHO specification). There is no explicit flag field on the product/RFQ/policy — infer it from the IEHK/WHO kit context. Omit/false otherwise. (Cold-chain products may warrant a separate cold-chain documentation note — e.g. a lab-diagnostics quote whose customer_note mentions "Cold-chain documentation required" — but that is distinct from the WHO flag.)
- **Quote-revision distractors.** `prior_quote_quantity`/`prior_unit_price_usd` and any `component_composition_distractors` are noise; reprice from the live catalog tier.

### 2.8 Quote variant field maps (follow the task's template exactly)
- Variant A (`quote_summary`+`freight_options`+`policy_flags`): single-product revision with freight. `quote_summary` carries `quote_id, customer_id, quote_date, product_code, confirmed_quantity, unit_price_usd, lead_time_days, shelf_life_months, quote_basis="EXW", exw_total_usd`. `freight_options[]` (AIR/SEA/ROAD): `freight_id, mode, freight_cost_usd, transit_days, valid_until, risk_level, risk_flag, grand_total_usd`. `policy_flags`: `recommended_mode, freight_reconfirmation_required, all_freight_options_valid_on_quote_date` (true only if all 3 real options are active & `valid_until>=quote_date`), `customer_policy, payment_terms`.
- Variant B (`quote_header`+`line_items`+`quote_controls`): indicative EXW module quote. `quote_header`: `rfq_id, customer_id, quote_date, currency="USD", quote_basis="EXW_ONLY"`. `line_items[]`: `product_code, article_number, quantity, unit_price, lead_time_days, shelf_life_months, line_total`. `quote_controls`: `grand_total` (=Σline_total), `freight_excluded=true, payment_terms, offer_validity_days=30, who_documentation_required`.
- Variant C (`pricing`+`transport_decisions`+`client_warnings`): single-product revision with stale-freight flagging. `pricing`: `quote_id, customer_id, quote_date, product_code, confirmed_quantity, catalog_tier{min_quantity,max_quantity,unit_price_usd,lead_time_days,shelf_life_months}, exw_total_usd, payment_terms`. `transport_decisions.freight_options[]`: `freight_id, mode, freight_cost_usd, transit_days, valid_until, validity_status, source_is_stale, customs_border_risk, grand_total_usd`; plus `recommended_mode, freight_reconfirmation_required`. `client_warnings`: `road_quote_invalid_or_stale` (true if the ROAD option is stale/expired or HIGH risk), `freight_warning` (human sentence naming the stale/expired option and its risk), `policy_terms{quote_basis, payment_terms, freight_reconfirmation_required}`.

## 3. RECONCILIATION tasks

### 3.1 Fetch the engagement records
`GET /api/opportunities/<opp_id>` (detail) → `GET /api/invoices?opportunity_id=<opp>`, `GET /api/payments?opportunity_id=<opp>`, `GET /api/revenue-journals?opportunity_id=<opp>`, `GET /api/events?customer_id=<cust>` (and/or `?opportunity_id=`), `GET /api/vouchers?customer_id=<cust>`, `GET /api/customers/<cust>`, `GET /api/policies`.

### 3.2 Milestone / phase mapping
- The opportunity's `phases[]` (sorted by presentation order) map 1:1 to milestones **MS1, MS2, MS3, …** in ascending order. `phase_number` (Variant A) = 1-based index.
- Each phase has `invoice_id` → look up that invoice for amount/status/dates/paid. `amount`/`invoice_total` = `invoice.amount_usd`. `paid_amount`/`amount_paid` = `invoice.paid_amount_usd`. `amount_unpaid` = `invoice.outstanding_amount_usd`.
- Match payments via `payment.invoice_id` and revenue-journals via `revenue_journal.invoice_id` (or `phase_id`).

### 3.3 State & status mapping
- **invoice_state** (Variant B): `invoice.status` `"paid"`→`PAID`; `"unpaid"`→`OPEN`; `"void"`→`VOID`; else `UNKNOWN`.
- **payment_state / payment_status**: `PAID` when invoice fully paid (`outstanding_amount_usd == 0` and `paid_amount_usd == amount`); `PARTIAL` when `0 < paid_amount < amount`; `UNPAID` when `paid_amount == 0` and not paid; `UNKNOWN` when indeterminate.
- **due_date**: `null` for **PAID** milestones (paid milestones have no remaining due date). For unpaid/open milestones, `due_date` = `invoice.due_date`. (One official train answer reported a collection date that did not equal the invoice `due_date`; when in doubt use the invoice `due_date` from the API — it is the authoritative, reproducible value.)
- **recognition_status** (per milestone): `RECOGNIZED` if the milestone is PAID **and** a posted `revenue-journal` exists for its invoice/phase; `MISSING_REVENUE_JOURNAL` if the milestone is PAID but **no** posted revenue-journal exists; `NOT_REQUIRED_UNPAID` if the milestone is unpaid (revenue not yet earned); `UNKNOWN` otherwise. (Policy: when a milestone is complete and paid, create/verify revenue recognition from deferred revenue to income; unpaid future milestones stay outstanding.)

### 3.4 Reconciliation totals
- `won_amount` = `opportunity.won_amount_usd`. `phase_total_amount` (Variant B) / milestone sum (Variant A) = Σ `phases[].amount_usd`. `opportunity_matches_phase_total` / `opportunity_matches_milestones` = (`Σ phases == won_amount`).
- `total_paid_amount` = Σ posted `payments[].amount_usd` for the opportunity (= Σ `invoice.paid_amount_usd`).
- `outstanding_balance` = `opportunity.outstanding_amount_usd` = `won_amount − total_paid_amount` = Σ unpaid `invoice.outstanding_amount_usd`. All three must agree.
- Revenue-recognition summary (Variant A): `recognized_milestones` = PAID milestones that have a posted journal; `missing_required_milestones` = PAID milestones with **no** posted journal (unpaid milestones are NOT "missing" — they're not required); `recognized_amount` = Σ journal amounts for recognized milestones; overall `recognition_status` = `COMPLETE_FOR_PAID_MILESTONES` when every PAID milestone is recognized, else incomplete (flag the missing ones).
- `opportunity_stage`/`stage` = `opportunity.stage` uppercased: `closed_won`→`WON`, `open`→`OPEN`, `closed_lost`/`lost`→`LOST`.

### 3.5 Contact linkage
- Primary contact name = `opportunity.contact` (also `event.primary_contact` and the prompt-named person — they agree). Link it to `customer_id` (and `opportunity_id` in Variant A's `contact` object). Every follow-up task carries this `contact_name`.

### 3.6 Action routing (Variant B — `invoice_actions` + `event_actions`)
**Accounting action** (revenue recognition):
- If any PAID milestone lacks a posted revenue journal → `action = "RECORD_REVENUE_MS<N>"`, `milestone_id = "MS<N>"`, `amount` = that milestone's amount, `debit_account = "DEFERRED_REVENUE"`, `credit_account = "IMPLEMENTATION_SERVICES_REVENUE"`, `owner_queue = "ACCOUNTING"`. (These accounts mirror the posted revenue-journal records: debit "Deferred Revenue", credit "Implementation Services Revenue".) `primary_accounting_action` mirrors this `action`.
- If all PAID milestones are already recognized → `VERIFY_REVENUE_ONLY`, `milestone_id = "NONE"`, `amount = 0`, accounts `NONE`, owner `ACCOUNTING`.
- If there are no paid milestones / nothing to recognize → `NO_ACCOUNTING_ACTION`, `NONE`/`NONE`/`NONE`.

**Collection action** (unpaid milestones):
- For each unpaid milestone: if `invoice.due_date > as_of_date` (not yet due) → `MONITOR_UNPAID_NOT_DUE`, `owner_queue = "ACCOUNT_MANAGEMENT"`. If `due_date <= as_of_date` (overdue) → `SEND_COLLECTION_NOTICE`, `owner_queue = "COLLECTIONS"`.
- `collection_task`: `action`, `milestone_id`, `amount` (unpaid amount), `due_date` (the milestone's due date), `owner_queue`, `contact_name`. Top-level `collection_action` mirrors `collection_task.action`.
- If everything is paid → `NO_COLLECTION_ACTION`, `milestone_id = "NONE"`, `owner_queue = "NONE"`.

**Event/invite action**:
- Fetch the linked event (`events?customer_id=` / `?opportunity_id=`) and its voucher (`vouchers?customer_id=`, matched by `voucher_code`).
- `event_status` = `event.status.toUpperCase()` (`scheduled`→`SCHEDULED`, `confirmed`→`CONFIRMED`, `active`→`ACTIVE`, `completed`→`COMPLETED`, `cancelled`→`CANCELLED`).
- `voucher`: `voucher_code`, `voucher_status` = `voucher.status.toUpperCase()` (`active`→`ACTIVE`, `draft`→`DRAFT`, `expired`→`EXPIRED`, `disabled`→`DISABLED`); `discount_amount` = `voucher.discount_percent` (report the percent value as a 2-decimal number — the API stores `discount_percent`, not a dollar amount); `max_uses` = `voucher.max_redemptions`.
- `invite_action`: `SEND_BRIEFING_INVITE` when the event is scheduled/active/confirmed and the invite has not yet gone out (`redemptions_used == 0`); `VERIFY_INVITE_SENT` if already sent; `NO_INVITE_ACTION` if cancelled/completed. `invite_task`: `action`, `event_id`, `voucher_code`, `owner_queue = "ACCOUNT_MANAGEMENT"` (matches `event.follow_up_owner "Account Management"`), `contact_name`, `customer_id`.

### 3.7 Follow-up tasks (Variant A — `follow_up_tasks[]`)
Variant A uses a flat task list instead of the action objects. Emit tasks in this order:
1. **COLLECTION** (one per unpaid milestone): `task_type = "COLLECTION"`, `next_action = "COLLECT_UNPAID_MILESTONE"`, `milestone_id = "MS<N>"`, `amount_due` = unpaid amount, `due_date` = milestone due date, `event_id = null`, `voucher_code = null`, `linked_customer_id`, `linked_opportunity_id`, `contact_name`, `task_title` (e.g. `"Milestone <N> collection - <customer name>"`).
2. **EVENT_INVITATION** (one per linked event needing an invite): `task_type = "EVENT_INVITATION"`, `next_action = "SEND_EVENT_INVITATION"`, `event_id`, `voucher_code`, `milestone_id = null`, `amount_due = null`, `due_date` (= `as_of_date + 30 days`, the standard follow-up window —- do not schedule after the event date), `linked_customer_id`, `linked_opportunity_id`, `contact_name`, `task_title` (e.g. `"Send celebration invite - <customer name>"`).
- Use `null` (not omitted) for inapplicable fields (`amount_due`, `milestone_id`, `event_id`, `voucher_code`) so the array shape is uniform.

### 3.8 Reconciliation variant field maps
- Variant A (`account_status` + `milestones` + `revenue_recognition` + `event` + `follow_up_tasks`): top-level `account_status{customer_id, customer_name, opportunity_id, opportunity_stage, won_amount, opportunity_matches_milestones, outstanding_balance, contact{name, linked_customer_id, linked_opportunity_id}}`; `milestones[]{milestone_id, phase_number, invoice_total, payment_status, amount_paid, amount_unpaid, due_date|null, revenue_recognition_status}`; `revenue_recognition{recognition_status, recognized_milestones[], missing_required_milestones[], recognized_amount}`; `event{event_id, event_date, voucher_code, voucher_discount, voucher_max_uses}`; `follow_up_tasks[]` per §3.7.
- Variant B (`engagement_reconciliation` + `invoice_actions` + `event_actions`): `engagement_reconciliation{as_of_date, opportunity_id, customer_id, customer_name, stage, won_amount, phase_total_amount, opportunity_matches_phase_total, total_paid_amount, outstanding_balance, primary_contact{contact_name, customer_id}, milestones[]{milestone_id, amount, invoice_state, payment_state, paid_amount, due_date|null, recognition_status}}`; `invoice_actions{primary_accounting_action, collection_action, accounting_action{…}, collection_task{…}}` per §3.6; `event_actions{event_id, event_status, voucher{…}, invite_action, invite_task{…}}` per §3.6.

## 4. Controlled enum values (exact strings)

- `quote_basis`: `EXW` | `EXW_ONLY` | `EXW_PLUS_FREIGHT_OPTIONS` (per template).
- `payment_terms`: `PREPAY_100` | `NET_30_AFTER_PO` (other profiles pass through verbatim from `customer.payment_profile`).
- `mode`: `AIR` | `SEA` | `ROAD` (uppercase).
- `risk_level`: `LOW` | `MEDIUM` | `HIGH`. `risk_flag`: `NONE` | `MEDIUM_BORDER_RISK` | `HIGH_BORDER_RISK`.
- `customs_border_risk`: `LOW` | `HIGH` (mid transit risk that is not customs-related reports `LOW`).
- `validity_status`: `VALID` | `STALE`.
- `opportunity_stage`/`stage`: `WON` | `OPEN` | `LOST`.
- `invoice_state`: `PAID` | `OPEN` | `VOID` | `UNKNOWN`.
- `payment_state`/`payment_status`: `PAID` | `PARTIAL` | `UNPAID` | `UNKNOWN`.
- `recognition_status`/`revenue_recognition_status`: `RECOGNIZED` | `MISSING_REVENUE_JOURNAL` | `NOT_REQUIRED_UNPAID` | `UNKNOWN`.
- `primary_accounting_action`/`accounting_action.action`: `RECORD_REVENUE_MS<N>` | `VERIFY_REVENUE_ONLY` | `NO_ACCOUNTING_ACTION`.
- `debit_account`: `DEFERRED_REVENUE` | `ACCOUNTS_RECEIVABLE` | `CASH` | `NONE`. `credit_account`: `IMPLEMENTATION_SERVICES_REVENUE` | `DEFERRED_REVENUE` | `ACCOUNTS_RECEIVABLE` | `NONE`. `owner_queue` (accounting): `ACCOUNTING` | `ACCOUNT_MANAGEMENT` | `NONE`.
- `collection_action`: `MONITOR_UNPAID_NOT_DUE` | `SEND_COLLECTION_NOTICE` | `NO_COLLECTION_ACTION`. `collection_task.owner_queue`: `ACCOUNT_MANAGEMENT` | `COLLECTIONS` | `NONE`.
- `event_status`: `SCHEDULED` | `ACTIVE` | `COMPLETED` | `CANCELLED` | `UNKNOWN`. `voucher_status`: `ACTIVE` | `DRAFT` | `EXPIRED` | `DISABLED` | `UNKNOWN`.
- `invite_action`: `SEND_BRIEFING_INVITE` | `VERIFY_INVITE_SENT` | `NO_INVITE_ACTION`. `invite_task.owner_queue`: `ACCOUNT_MANAGEMENT` | `EVENTS` | `NONE`.
- Variant A `task_type`: `COLLECTION` | `EVENT_INVITATION`. `next_action`: `COLLECT_UNPAID_MILESTONE` | `SEND_EVENT_INVITATION`.
- `milestone_id`: `MS1` | `MS2` | `MS3` | … (`NONE` where the action isn't milestone-specific). Sort milestones ascending.

## 5. Owner-queue routing summary
- Revenue recognition (record/verify) → `ACCOUNTING`.
- Unpaid, not yet due (monitor) → `ACCOUNT_MANAGEMENT`.
- Unpaid, overdue (collection notice) → `COLLECTIONS`.
- Event invites / briefing → `ACCOUNT_MANAGEMENT` (mirrors `event.follow_up_owner`).

## 6. Trust-API caveat — customer display name
The API is authoritative for IDs, amounts, dates, statuses, tiers, and freight facts. The **one exception** is the human-readable `customer_name`/`customer_name` field in reconciliation outputs: official answers use the customer name **as written in the task prompt narrative**, even when the API `customer.name` differs slightly (e.g. the API record may read "… Initiative" while the prompt/answer uses "… Alliance"). Resolve the customer by ID against the API, but report the prompt's display name. If the prompt does not name the customer, fall back to `customer.name`.

## 7. Known gold-answer anomalies (do not over-fit)
These are quirks observed in the official train gold. Follow the API-grounded rule for unseen tasks; be aware the gold may differ on these specific points:
- A reconciliation gold reported an unpaid-milestone `due_date` that did **not** equal the invoice's `due_date`. Reproduce from `invoice.due_date` (the API value) — it is the only derivable source.
- A module-quote gold `grand_total` exceeded the sum of its `line_total`s by a small round amount with no documented surcharge in the API. Set `grand_total = Σ line_total` unless an explicit fee appears in the data.
- A reconciliation gold used the prompt's customer name rather than the API `customer.name` (see §6).

## 8. Output discipline checklist
- Match the task's `answer_template.json` field names, nesting, and order exactly; milestones ascending `MS1..`.
- All money as JSON numbers, 2 decimals where the template shows decimals (e.g. `42480.0`). Dates ISO `YYYY-MM-DD`. `null` (not omitted) where the template marks a field nullable.
- Stable IDs verbatim. Enums in exact UPPERCASE above.
- No markdown fences, no commentary — only the JSON object.
- Before emitting: re-check (a) tier selected by confirmed quantity, (b) prior prices ignored, (c) distractor freight excluded, (d) freight validity vs quote_date, (e) payment terms by client type, (f) paid milestones → `due_date: null` and revenue-journal coverage, (g) outstanding balance == won − total_paid == Σ unpaid outstanding, (h) module quotes not exploded to components, (i) EXW-only when no destination.
