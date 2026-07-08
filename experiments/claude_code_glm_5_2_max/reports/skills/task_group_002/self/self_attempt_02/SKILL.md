# MedBridge Sales Ops — Quote & Reconciliation SOP

Transferable operating procedure for MedBridge Sales Ops CRM tasks (B2B medical wholesale + implementation-services). Two task families: **QUOTE** (reconcile a customer RFQ/quote against the API → account-ready quote decision package) and **RECONCILIATION** (reconcile a won opportunity's invoices/payments/revenue-journals/events → finance-ready reconciliation). All business records come ONLY from the remote HTTP API. Money is USD 2-decimals; dates are ISO `YYYY-MM-DD`; use stable record IDs exactly as they appear.

## 0. API contract (memorize)

- Base URL: from `environment_access.md` (`API_BASE_URL`). All GET.
- `GET /api` → metadata (lists collections + endpoints).
- `GET /api/<collection>` → `{collection, count, records[]}`._collections: `customers, products, rfqs, quotes, freight-quotes, policies, opportunities, invoices, payments, revenue-journals, events, vouchers`.
- `GET /api/<collection>?<key>=<value>` → filter (case-insensitive, matches nested keys, numeric tolerance 2dp, multiple filters AND together). Use this for `invoices?opportunity_id=...`, `payments?opportunity_id=...`, `freight-quotes?quote_id=...`, `revenue-journals?opportunity_id=...`.
- `GET /api/<collection>/<id>` → single record. **Detail-by-id works ONLY for:** `customers, products, rfqs, quotes, freight-quotes, opportunities`. For invoices/payments/revenue-journals/events/vouchers/policies use listing or filter endpoints (no detail-by-id).
- `GET /api/search?q=<text>` → substring search across ALL collections (≤100 hits, each tagged with `collection` + `id`). Great for finding an opportunity's full object graph by customer/opportunity name.
- **Pipeline `python3 -m json.tool`** to read. Prefer writing a fetch-script that dumps all needed endpoints to one file, then Read it (avoids dropped output).

### Critical API gotchas
- `revenue-journals` does NOT reliably filter by `customer_id` — **filter by `opportunity_id`**. (Filtering by customer_id can return empty.)
- Trust the API over the prompt narrative when they conflict, BUT read the prompt carefully for WHICH entity (quote_id / rfq_id / opportunity_id / customer_id) to reconcile.
- Customer/quote/RFQ records contain `component_composition_distractors`, `prior_unit_price_usd`, and "old route" / "Distractor route" freight entries placed to mislead — see pitfalls §5.

## 1. Universal workflow (every task)

1. Read the prompt + `input/payloads/answer_template.json` **fully**. The template is the contract — field names, nesting, and controlled enum values are graded. **Templates vary across tasks even within the same family** (see §3, §4). Never assume a template; copy its exact structure.
2. Identify the anchor ID(s) in the prompt: a `quote_id` / `rfq_id` (quote family) or `opportunity_id` + `customer_id` (reconciliation family), plus any named event_id / voucher_code / contact.
3. Fetch the anchor record, then fan out to the related collections via filter (`?opportunity_id=`, `?quote_id=`) or `/api/search?q=<name>`. Fetch the customer by id, the product by code, policies (all), freight-quotes by quote_id, invoices/payments/revenue-journals/events/vouchers by opportunity_id (or search).
4. Reconcile the narrative against the records: confirm customer, quantity, product, dates; override stale/narrative values with API values.
5. Compute derived fields (pricing tiers, EXW totals, grand totals, paid/outstanding, recognition coverage) using the rules below.
6. Emit ONLY valid JSON matching the template — same keys, same nesting, controlled enum values, no markdown, no prose.

## 2. QUOTE family — business rules

### 2.1 Catalog tier by quantity (THE core pricing rule)
- Product records have `price_tiers[]` sorted by `min_qty` (with `max_qty` possibly `null` = infinity). Each tier carries `unit_price_usd`, `lead_time_days`, `lead_time_weeks`, and the product carries `shelf_life_months`.
- Select the tier where `min_qty <= confirmed_quantity <= max_qty` (treat null max as +∞).
- **The catalog tier OVERRIDES `prior_unit_price_usd`** found in the quote line item. The prior price is a distractor; always use the active tier's `unit_price_usd`.
- Examples (train): WC-KIT-A qty 360 → tier [300–499] @ 118.0 (prior was 124.0 — ignore). LD-REAGENT-44 qty 1000 → tier [900–1199] @ 76.0 (prior was 79.5 — ignore).
- Module products (IEHK-*) often have a single tier (min 1, max null) — just use that price.

### 2.2 EXW vs freight-inclusive
- `exw_total_usd` = `unit_price_usd × confirmed_quantity`. EXW **excludes** freight, insurance, import duty, customs clearance, last-mile (policy `POL-EXW-SCOPE` / `POL-INDICATIVE-EXW`).
- `grand_total_usd` per freight option = `exw_total_usd + freight_cost_usd` (EXW plus that freight).
- For EXW-only / indicative module quotes with no destination: `freight_excluded = true`, `quote_basis = "EXW_ONLY"`, **no** freight_options, `grand_total` = sum of line_totals.

### 2.3 Freight validity vs quote date (source-validity)
- Quote pricing is valid 30 calendar days from quote_date (`POL-QUOTE-VALIDITY`). Freight `valid_until` may expire sooner (`POL-FREIGHT-RECONFIRM`).
- A freight quote is **valid on the quote date** iff `valid_until >= quote_date` AND `status == "active"`.
- `valid_until < quote_date` → expired. `status == "stale"` → stale source. Either makes the option invalid/unusable for a clean recommendation.
- `freight_reconfirmation_required = true` (policy `POL-FREIGHT-RECONFIRM`: rates need reconfirmation at final order). Practically always true because freight `valid_until` precedes the 30-day quote window.
- `all_freight_options_valid_on_quote_date = true` only when every INCLUDED (real, active) freight option has `valid_until >= quote_date`.

### 2.4 Route risk enums
- Freight `route_risk` values: `low`, `medium`, `high` → emit as `LOW`, `MEDIUM`, `HIGH`.
- `risk_flag` / `customs_border_risk` is keyword-derived from `risk_notes`:
  - "border"/"customs" → `{LEVEL}_BORDER_RISK` (e.g. `MEDIUM_BORDER_RISK`, `HIGH_BORDER_RISK`).
  - "shelf-life"/"shelf life" → `SHELF_LIFE_RISK`.
  - low risk with no specific keyword → `NONE`.
  - Read `risk_notes` literally; do not assume all medium → BORDER_RISK (a reefer sea option may be medium due to shelf-life, not border).

### 2.5 Recommended transport mode (judgment rule)
Exclude stale/expired/distractor freight first, then:
1. **Cold-chain product** (`product.cold_chain_required == true`): recommend an active option with `cold_chain_support == true` and LOW risk, preferring **AIR** (shortest transit protects temperature + shelf life). (train_004 LD-REAGENT-44 → AIR.)
2. **Non-cold-chain**: recommend the active LOW-risk option with the **lowest grand_total** (cost-effective for NGO/wholesale). If no low-risk option exists, recommend the lowest-risk available. (train_001 WC-KIT-A → SEA: both AIR & SEA are low risk, SEA grand 46360 < AIR 58680.)
3. If the quote carries a `grant_delivery_need_by` date, ensure `quote_date + lead_time_days + transit_days_max` fits; if not, upgrade toward AIR.
Flag recommended_mode as the single mode string (e.g. `"AIR"`, `"SEA"`, `"ROAD"`). This is the most uncertain field — weigh cold-chain, risk, transit vs deadline, and cost, in that priority.

### 2.6 Payment terms & customer policy
- Fetch `/api/policies` and match `policy_area == "payment_terms"` to the customer's segment/payment_profile:
  - New NGO (`is_recurring == false`, `payment_profile == "NEW_CLIENT_REVIEW"`, `segment == "new_ngo"`) → policy `POL-NEW-CLIENT-PAYMENT` → **`PREPAY_100`** (prepay before production release).
  - Recurring NGO (`is_recurring == true`, `segment == "recurring_ngo"`) → `POL-RECURRING-NGO-PAYMENT` → `NET_30_AFTER_PO` (unless restricted grant terms say otherwise).
  - Commercial/government/distributor: use the customer's `payment_profile` (e.g. `NET_45_APPROVED`, `NET_30_AFTER_PO`, `PREPAY_50_BALANCE_BEFORE_SHIP`); if no dedicated policy, `customer_policy` = the `payment_profile` string.
- `payment_terms` = the resolved terms_code (policy `terms_code` if a policy matches, else `payment_profile`).
- `customer_policy` (001-style template) = the governing policy **id** (e.g. `POL-RECURRING-NGO-PAYMENT`) when one matches; else the `payment_profile`.

### 2.7 Module-level granularity (IEHK / field-clinic module quotes)
- Policy `POL-MODULE-GRANULARITY`: quote module RFQs at **module line level only**. Do NOT expand `components[]` into component SKUs, even though the product record lists components and the RFQ may carry `component_composition_distractors`. One line_item per requested module.
- For indicative module quotes with no destination → EXW only, exclude freight (`POL-INDICATIVE-EXW`).
- `offer_validity_days = 30` (`POL-QUOTE-VALIDITY`).
- **WHO documentation flag**: `who_documentation_required = true` for IEHK-style / medicine-containing modules (product `family == "emergency_health_kit"` with medicine components like "essential medicines", "oral medicines", "injectables support", "malaria medicines"). These are WHO-standardized kits. False for non-medicine products.
- Line item fields: `product_code`, `article_number` (from product), `quantity`, `unit_price` (tier), `lead_time_days`, `shelf_life_months`, `line_total` = qty × unit_price. `grand_total` = Σ line_totals.

## 3. QUOTE family — TWO template variants (match exactly)

### Variant A — "quote decision package" (train_001 style)
Top keys: `quote_summary`, `freight_options[]`, `policy_flags`.
- `quote_summary`: quote_id, customer_id, quote_date, product_code, confirmed_quantity, unit_price_usd, lead_time_days, shelf_life_months, quote_basis (`"EXW"`), exw_total_usd.
- `freight_options[]` (one per **active, real-destination** option; EXCLUDE stale & "Distractor route"): freight_id, mode (`AIR`/`SEA`/`ROAD`), freight_cost_usd, transit_days (use `transit_days_text` e.g. `"4-6 days"`), valid_until, risk_level, risk_flag, grand_total_usd.
- `policy_flags`: recommended_mode, freight_reconfirmation_required, all_freight_options_valid_on_quote_date, customer_policy, payment_terms.
- train_001: 3 options (AIR/SEA/ROAD all active); exclude `FR-DIS-WC-OLD-AIR` (stale, Distractor) & `FR-DIS-WC-HEAVY-SEA` (Distractor route).

### Variant B — "revised quote with source-validity warnings" (train_004 style)
Top keys: `pricing`, `transport_decisions`, `client_warnings`.
- `pricing`: quote_id, customer_id, quote_date, product_code, confirmed_quantity, **`catalog_tier`{min_quantity, max_quantity, unit_price_usd, lead_time_days, shelf_life_months}**, exw_total_usd, payment_terms.
- `transport_decisions.freight_options[]`: freight_id, mode, freight_cost_usd, transit_days, valid_until, **validity_status** (`VALID` if valid_until≥quote_date & active; `EXPIRED` if valid_until<quote_date), **source_is_stale** (bool = `status=="stale"`), **customs_border_risk** (`LOW`/`MEDIUM`/`HIGH` from route_risk), grand_total_usd. **Include stale real-destination options** (e.g. the stale road quote) so they can be flagged; still exclude "Distractor route" entries.
- `transport_decisions`: recommended_mode, freight_reconfirmation_required.
- `client_warnings`: **road_quote_invalid_or_stale** (bool true when the road option is stale/expired), **freight_warning** (short string describing the concern), **policy_terms{quote_basis, payment_terms, freight_reconfirmation_required}**.
- train_004: include AIR (VALID), SEA (VALID), ROAD (EXPIRED/source_is_stale=true, customs_border_risk=HIGH); exclude `FR-DIS-LD-OLD-SEA` (Distractor route).

**Always read the task's own template** — field names and nesting differ between variants.

## 4. RECONCILIATION family — business rules

### 4.1 Anchor & object graph
- Fetch `opportunities/<opp_id>`, then `invoices?opportunity_id=`, `payments?opportunity_id=`, `revenue-journals?opportunity_id=`, and the linked event+voucher (via `/api/search?q=<opp or customer>` or filter events/vouchers by `opportunity_id`).
- Opportunity `stage`: `closed_won` → `WON`; `open` → `OPEN`; `closed_lost`/`lost` → `LOST`.
- `won_amount_usd` = opportunity's won amount. `phase_total_amount` = Σ `phases[].amount_usd`. `opportunity_matches_milestones`/`opportunity_matches_phase_total` = (`won_amount == phase_total`).
- `total_paid_amount` = Σ invoice `paid_amount_usd`. `outstanding_balance` = Σ invoice `outstanding_amount_usd` (should equal opportunity `outstanding_amount_usd`).
- `primary_contact`/`contact` = opportunity `contact` (a name); link `customer_id` and `opportunity_id`.

### 4.2 Milestone / invoice / payment state mapping
Each opportunity `phases[]` entry has a `phase_id`, `amount_usd`, `completion_date`, `invoice_id`. Join to the invoice by `invoice_id` (or `phase_id`). For each milestone:
- `invoice_state` (enum PAID|OPEN|VOID|UNKNOWN) from invoice `status`: `paid`→PAID; `unpaid`→OPEN; `overdue`→OPEN; `draft`→OPEN (or UNKNOWN if not yet issued; lean OPEN). `void`→VOID. No invoice record → UNKNOWN.
- `payment_state` (PAID|PARTIAL|UNPAID|UNKNOWN): `paid_amount==amount`→PAID; `0<paid_amount<amount`→PARTIAL; `paid_amount==0`→UNPAID; no invoice→UNKNOWN.
- `paid_amount` = invoice `paid_amount_usd`.
- **`due_date`: set `null` for PAID milestones** (obligation settled); report the invoice `due_date` only for PARTIAL/UNPAID milestones. (This is a deliberate output convention — do not copy the paid invoice's due_date.)
- Milestone id: some templates use `MS1|MS2|MS3` (ordered ascending by phase); others use the stable `phase_id`/`invoice_id`. Use exactly what the template declares.

### 4.3 Revenue-recognition state mapping
Policy `POL-REVREC`: when a milestone is complete AND paid, recognize revenue (deferred revenue → income); unpaid future milestones remain outstanding and drive collection when due/overdue.
Per-milestone `recognition_status`:
- Paid milestone + a `revenue-journals` record exists for its `phase_id`/`invoice_id` (status `posted`) → **RECOGNIZED** (train_003: `RECOGNIZED`; train_005: `RECOGNIZED`).
- Paid milestone + NO revenue journal → **REQUIRED_MISSING** (train_003 enum) / **MISSING_REVENUE_JOURNAL** (train_005 enum). (train_005 MS2: paid 45000 but no RJ → missing.)
- Unpaid milestone → **NOT_REQUIRED_UNPAID** (not yet earned).
- No invoice → UNKNOWN (train_005 only).
- Existing RJ pattern: `debit_account="Deferred Revenue"`, `credit_account="Implementation Services Revenue"`.

Aggregate (train_003 `revenue_recognition`):
- `recognition_status`: all paid milestones recognized → `COMPLETE_FOR_PAID_MILESTONES`; any paid milestone missing RJ → `MISSING_FOR_PAID_MILESTONES`; no paid milestones → `NOT_REQUIRED`.
- `recognized_milestones[]` = phase_ids with a posted RJ. `missing_required_milestones[]` = paid phase_ids lacking an RJ. `recognized_amount` = Σ RJ `amount_usd`.
- train_003 Helios: P1 recognized, P2 unpaid → COMPLETE_FOR_PAID_MILESTONES; recognized [HEL-P1]; recognized_amount 50000.

### 4.4 Follow-up routing (template-dependent)

**train_003 style** (`follow_up_tasks[]`, `task_type` COLLECTION|EVENT_INVITATION, `next_action` COLLECT_UNPAID_MILESTONE|SEND_EVENT_INVITATION):
- One COLLECTION task per unpaid/partial milestone: `task_type=COLLECTION`, `next_action=COLLECT_UNPAID_MILESTONE`, `milestone_id`=phase/invoice id, `amount_due`=outstanding, `due_date`=invoice due_date, `event_id=null`, `voucher_code=null`.
- One EVENT_INVITATION task per linked event when invite not yet sent (`voucher.redemptions_used==0` and event not completed/cancelled): `task_type=EVENT_INVITATION`, `next_action=SEND_EVENT_INVITATION`, `event_id`, `voucher_code`, `milestone_id=null`, `amount_due=null`, `due_date`=event_date.
- All tasks: `linked_customer_id`, `linked_opportunity_id`, `contact_name` = opportunity contact (prompt may name the contact to tie work to, e.g. "Mara Okafor").
- train_003: COLLECTION for INV-HELIOS-P2 (70000, due 2026-06-27) + EVENT_INVITATION for EVT-HELIOS-CELEBRATION (HELIOSVIP100, 2026-07-22).

**train_005 style** (`invoice_actions` + `event_actions`, more granular):
- `primary_accounting_action`: a paid milestone missing RJ → `RECORD_REVENUE_MS<n>`; all paid milestones have RJ → `VERIFY_REVENUE_ONLY`; nothing paid / nothing to do → `NO_ACCOUNTING_ACTION`.
- `accounting_action`: action, milestone_id (MS1|MS2|MS3|NONE), amount = the missing-RJ milestone's paid amount, `debit_account=DEFERRED_REVENUE`, `credit_account=IMPLEMENTATION_SERVICES_REVENUE`, `owner_queue=ACCOUNTING`.
- `collection_action` / `collection_task` (route by due_date vs as-of date — use the prompt's as-of date, e.g. 2026-06-01; if unstated, use the env business date 2026-06-01):
  - Unpaid + `due_date < as_of` (overdue) → `SEND_COLLECTION_NOTICE`, `owner_queue=COLLECTIONS`.
  - Unpaid + `due_date >= as_of` or null (not yet due) → `MONITOR_UNPAID_NOT_DUE`, `owner_queue=ACCOUNT_MANAGEMENT`.
  - No unpaid milestones → `NO_COLLECTION_ACTION`, owner NONE.
  - `collection_task.milestone_id` = the unpaid milestone, `amount` = its outstanding, `due_date` = its invoice due_date, `contact_name` = opportunity contact.
- `event_actions`: `event_id`, `event_status` (map event.status: scheduled→SCHEDULED, live→ACTIVE, completed→COMPLETED, confirmed→ACTIVE, tentative→SCHEDULED, cancelled→CANCELLED, else UNKNOWN), `voucher{voucher_code, voucher_status (active→ACTIVE; if valid_until<as_of treat EXPIRED; draft→DRAFT; disabled→DISABLED), discount_amount (=voucher.discount_percent as a number, e.g. 50.00), max_uses (=max_redemptions)}`, `invite_action` (redemptions_used==0 & event not completed/cancelled → `SEND_BRIEFING_INVITE`; redemptions_used>0 → `VERIFY_INVITE_SENT`; else `NO_INVITE_ACTION`), `invite_task{action, event_id, voucher_code, owner_queue (event.follow_up_owner=="Account Management"→ACCOUNT_MANAGEMENT else EVENTS), contact_name, customer_id}`.
- train_005 Meridian (as-of 2026-06-01): RECORD_REVENUE_MS2 (amount 45000, DR Deferred Revenue / CR Implementation Services Revenue, ACCOUNTING); collection MONITOR_UNPAID_NOT_DUE for MS3 (25000, due 2026-07-15 future, ACCOUNT_MANAGEMENT, contact Daniel Rees); event EVT-MERIDIAN-BRIEFING SCHEDULED, voucher MERIDIANBRIEF50 ACTIVE discount 50.00 max_uses 20, invite SEND_BRIEFING_INVITE.

### 4.5 Event & voucher linkage
- Linked event: filter `events` by `opportunity_id` (or the event_id named in prompt). Fields: `event_date`, `status`, `primary_contact`, `voucher_code`, `follow_up_owner`.
- Linked voucher: code = event's `voucher_code`; fields `discount_percent`, `max_redemptions`, `redemptions_used`, `status`, `valid_until`.
- train_003 `event` block: event_id, event_date, voucher_code, voucher_discount (=discount_percent), voucher_max_uses (=max_redemptions). (Helios: EVT-HELIOS-CELEBRATION, 2026-07-22, HELIOSVIP100, 100, 4.)

## 5. Common pitfalls / distractors (verified in train data)

1. **Narrative customer-name mismatch**: prompt may say "Health Horizon Aid" / "GreenHarvest Labs" but the quote's `customer_id` resolves to "HealthHands Alliance" (CUST-HHA) / "Global Health Laboratories" (CUST-GHL). Always take customer_id from the quote/RFQ and fetch the canonical name from `/api/customers/<id>`.
2. **prior_unit_price_usd distractor**: the quote line item's prior price is NOT the price — the active catalog tier by quantity is. (train_001: 124.0→118.0; train_004: 79.5→76.0.)
3. **Distractor freight quotes**: entries with `destination == "Distractor route"`, or stale/expired "old route benchmark" quotes (status stale, valid_until before quote_date) — exclude from clean option sets; in Variant B include the real-but-stale road option only to flag it (`source_is_stale=true`, `road_quote_invalid_or_stale=true`).
4. **EXW-only excludes freight**: indicative/module quotes with no destination have NO freight_options; `freight_excluded=true`, `quote_basis="EXW_ONLY"`. Don't invent freight.
5. **Module granularity**: do NOT expand `components[]` / `component_composition_distractors` into component lines. One line per module. (POL-MODULE-GRANULARITY.)
6. **New-client prepay**: new NGO (`is_recurring=false`, `NEW_CLIENT_REVIEW`) → `PREPAY_100`, not net terms. (POL-NEW-CLIENT-PAYMENT.)
7. **Paid milestones → due_date null** in milestone output (obligation settled); report due_date only for unpaid/partial.
8. **revenue-journals filter by opportunity_id, not customer_id** (customer_id filter can return empty).
9. **Paid-without-RJ is the key reconciliation defect**: a paid milestone with no matching revenue journal drives `RECORD_REVENUE_MS<n>` / `MISSING_FOR_PAID_MILESTONES` / `REQUIRED_MISSING`. Always join invoices↔revenue-journals by `phase_id`/`invoice_id`.
10. **Collection routing depends on as-of date**: overdue (due_date < as_of) → SEND_COLLECTION_NOTICE/COLLECTIONS; not-yet-due → MONITOR_UNPAID_NOT_DUE/ACCOUNT_MANAGEMENT. Use the prompt's as-of date (default 2026-06-01).
11. **discount_amount == discount_percent**: voucher records store `discount_percent`; report it as the numeric discount (e.g. 50.00, 100.00) — there is no separate dollar amount.
12. **Two quote templates & two reconciliation templates exist** — always match the specific `answer_template.json`. Variant A quote (risk_level/risk_flag, exclude stale) vs Variant B quote (catalog_tier/source_is_stale/validity_status/customs_border_risk, flag stale road). train_003 reconciliation (account_status/milestones/revenue_recognition/event/follow_up_tasks) vs train_005 reconciliation (engagement_reconciliation/invoice_actions/event_actions).
13. **WHO doc flag** true for IEHK/medicine modules; not applicable to non-medicine product quotes.
14. **Distractor RFQs/quotes**: older `RFQ-DIS-*` / `Q-DIS-*` records (draft, different dates, "Distractor" notes) — use only the ID named in the prompt.

## 6. Quick reference — controlled enum values

- `opportunity_stage` / `stage`: WON | OPEN | LOST
- `invoice_state`: PAID | OPEN | VOID | UNKNOWN
- `payment_state` (per template): PAID | PARTIAL | UNPAID | UNKNOWN  (train_003 simplified: PAID | PARTIAL | UNPAID)
- `recognition_status` (train_003): RECOGNIZED | REQUIRED_MISSING | NOT_REQUIRED_UNPAID
- `recognition_status` (train_005): RECOGNIZED | MISSING_REVENUE_JOURNAL | NOT_REQUIRED_UNPAID | UNKNOWN
- `revenue_recognition.recognition_status` (train_003): COMPLETE_FOR_PAID_MILESTONES | MISSING_FOR_PAID_MILESTONES | NOT_REQUIRED
- `task_type`: COLLECTION | EVENT_INVITATION
- `next_action`: COLLECT_UNPAID_MILESTONE | SEND_EVENT_INVITATION
- `primary_accounting_action`: RECORD_REVENUE_MS2 | VERIFY_REVENUE_ONLY | NO_ACCOUNTING_ACTION (use the MSn matching the missing-RJ milestone)
- `collection_action`: MONITOR_UNPAID_NOT_DUE | SEND_COLLECTION_NOTICE | NO_COLLECTION_ACTION
- `accounting_action.debit_account`: DEFERRED_REVENUE | ACCOUNTS_RECEIVABLE | CASH | NONE
- `accounting_action.credit_account`: IMPLEMENTATION_SERVICES_REVENUE | DEFERRED_REVENUE | ACCOUNTS_RECEIVABLE | NONE
- `owner_queue` (accounting/collection): ACCOUNTING | ACCOUNT_MANAGEMENT | COLLECTIONS | NONE
- `event_status`: SCHEDULED | ACTIVE | COMPLETED | CANCELLED | UNKNOWN
- `voucher_status`: ACTIVE | DRAFT | EXPIRED | DISABLED | UNKNOWN
- `invite_action`: SEND_BRIEFING_INVITE | VERIFY_INVITE_SENT | NO_INVITE_ACTION
- `invite_task.owner_queue`: ACCOUNT_MANAGEMENT | EVENTS | NONE
- `mode`: AIR | SEA | ROAD
- `risk_level` / `customs_border_risk`: LOW | MEDIUM | HIGH
- `validity_status`: VALID | EXPIRED (STALE if template requires)
- `quote_basis`: EXW | EXW_ONLY

## 7. Worked train results (for self-check, NOT for copying — test tasks differ)

- **train_001** Q-TR-WC-1187 / CUST-HHA: qty 360 @ 118.0, EXW 42480.00; AIR grand 58680.00 (LOW/NONE), SEA 46360.00 (LOW/NONE), ROAD 48630.00 (MEDIUM/MEDIUM_BORDER_RISK); recommended SEA; freight_reconfirm true; all_valid_on_quote_date true; customer_policy POL-RECURRING-NGO-PAYMENT; payment_terms NET_30_AFTER_PO.
- **train_002** RFQ-TR-IEHK-204 / CUST-NOVAID: 5 module lines (BASIC 24200, SUPP-A 1380, SUPP-B 1525, TRAUMA 3100, MALARIA 1880), grand_total 32085.00; EXW_ONLY; freight_excluded true; payment_terms PREPAY_100; offer_validity_days 30; who_documentation_required true.
- **train_003** OPP-TR-HELIOS / CUST-HELIOS: WON 120000 (matches phases 50000+70000); outstanding 70000; P1 RECOGNIZED, P2 NOT_REQUIRED_UNPAID; recognition COMPLETE_FOR_PAID_MILESTONES, recognized [HEL-P1] 50000; event EVT-HELIOS-CELEBRATION 2026-07-22 / HELIOSVIP100 / 100 / 4; follow-ups: COLLECTION (INV-HELIOS-P2, 70000, due 2026-06-27) + EVENT_INVITATION.
- **train_004** Q-TR-LD-5521 / CUST-GHL: qty 1000 @ 76.0 (tier 900–1199, lead 14, shelf 18), EXW 76000.00; AIR 97400.00 (VALID, LOW), SEA 81200.00 (VALID, MEDIUM), ROAD 80800.00 (EXPIRED/source_is_stale true, HIGH); recommended AIR; road_quote_invalid_or_stale true; freight_reconfirm true; payment_terms NET_30_AFTER_PO.
- **train_005** OPP-TR-MERIDIAN / CUST-MERIDIAN (as-of 2026-06-01): WON 100000 (matches 30000+45000+25000); paid 75000; outstanding 25000; MS1 RECOGNIZED, MS2 MISSING_REVENUE_JOURNAL, MS3 NOT_REQUIRED_UNPAID; RECORD_REVENUE_MS2 (45000, DR Deferred Revenue / CR Implementation Services Revenue, ACCOUNTING); collection MONITOR_UNPAID_NOT_DUE (MS3, 25000, due 2026-07-15, ACCOUNT_MANAGEMENT, Daniel Rees); event EVT-MERIDIAN-BRIEFING SCHEDULED, voucher MERIDIANBRIEF50 ACTIVE 50.00 / 20, SEND_BRIEFING_INVITE.
