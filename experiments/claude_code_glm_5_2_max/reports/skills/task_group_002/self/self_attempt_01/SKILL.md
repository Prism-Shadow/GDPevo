# MedBridge Sales Ops — CRM Reconciliation & Quote Decision SOP

Transferable skill for two task families in the MedBridge Sales Ops domain:
- **QUOTE tasks** — reconcile a customer RFQ/quote against the API (customer, quote, product catalog tiers, freight quotes, policies) into an account-ready quote decision package (EXW pricing, freight options with grand totals, route risk flags, recommended transport mode, freight-validity warnings, payment terms).
- **RECONCILIATION tasks** — reconcile a won opportunity (CRM opportunity, milestone invoices, payments, revenue-recognition journals, events, vouchers) into a finance-ready reconciliation (paid/unpaid state, outstanding balance, revenue-recognition coverage, CRM follow-up tasks, event/voucher linkage).

All rules below were distilled from actually solving the 5 train tasks against the live remote API. They transfer to unseen test tasks.

---

## 0. Environment & API access

- Base URL: `<remote-env-url>` (from `environment_access.md`). All business records come ONLY through this HTTP API. Do not read any local `env/` directory.
- `GET /health` — health check. `GET /api` — lists `collections` and `endpoints`.
- `GET /api/<collection>` — list all records (`{collection, count, records}`).
- `GET /api/<collection>?<key>=<value>` — case-insensitive filter; matches nested keys; multiple filters AND. Numeric tolerance 2dp.
- `GET /api/<collection>/<id>` — detail by id. **ONLY available for:** `customers`, `products`, `rfqs`, `quotes`, `freight-quotes`, `opportunities`. For all other collections use listing/filter or `/api/search`.
- `GET /api/search?q=<text>` — substring search across ALL collections (up to 100 hits, each tagged with `collection` + `id` + full `record`). Best tool for finding linked events/vouchers by customer or opportunity name.
- Collections: `customers`, `products`, `rfqs`, `quotes`, `freight-quotes`, `policies`, `opportunities`, `invoices`, `payments`, `revenue-journals`, `events`, `vouchers`.
- Money = USD, 2 decimals. Dates = ISO `YYYY-MM-DD`. Use stable record IDs exactly as they appear.
- Trust the API over prompt narrative when they conflict (e.g. prompt says "Health Horizon Aid" but API customer name is "HealthHands Alliance"; prompt says "GreenHarvest Labs" but API name is "Global Health Laboratories"). Always use API record values for output. But read the prompt carefully for WHICH entity (quote_id / opportunity_id / customer_id) to reconcile.

### Query strategy by task family
- **QUOTE task**: fetch `quote` by id → get `customer_id`, `primary_product_code`/line items, `confirmed_quantity`, `quote_date`, `destination`. Then fetch `customer` by id, `product` by code, `freight-quotes?quote_id=<quote_id>`, and list/read `policies`.
- **RECONCILIATION task**: fetch `opportunity` by id → get `customer_id`, phases, `won_amount_usd`, `stage`, `contact`. Then:
  - `invoices?opportunity_id=<opp_id>` (or `?customer_id=`)
  - `payments?opportunity_id=<opp_id>`
  - **`revenue-journals?opportunity_id=<opp_id>`** — see pitfall below
  - `/api/search?q=<customer/opportunity name>` to find linked `events` and `vouchers`, OR `events?customer_id=` / `vouchers?customer_id=`.

---

## 1. QUOTE TASK SOP

### 1.1 Identify the entity & fetch records
1. Read the prompt for the quote_id (e.g. `Q-TR-WC-1187`, `Q-TR-LD-5521`) or rfq_id (e.g. `RFQ-TR-IEHK-204`).
2. `GET /api/quotes/<quote_id>` (or `/api/rfqs/<rfq_id>`). Extract: `customer_id`, `primary_product_code` / `line_items[].product_code`, `confirmed_quantity` (quote) or `requested_modules[].quantity` (rfq), `quote_date`, `destination`, `incoterm`.
3. `GET /api/customers/<customer_id>` — get `name`, `customer_type`, `is_recurring`, `segment`, `payment_profile`, `grant_terms`, `contacts`.
4. `GET /api/products/<product_code>` — get `price_tiers`, `shelf_life_months`, `cold_chain_required`, `article_number`, `components`, `family`, `unit`.
5. `GET /api/freight-quotes?quote_id=<quote_id>` — get all freight options (including distractors; filter per §1.5).
6. `GET /api/policies` — read the relevant policy records (payment_terms, quote_scope, freight, quote_lines, incoterms, quote_validity).

### 1.2 Catalog tier by quantity (CRITICAL — overrides prior price)
- A product has `price_tiers` each with `min_qty`, `max_qty` (null = unbounded), `unit_price_usd`, `lead_time_days`.
- Select the tier where `min_qty <= confirmed_quantity <= max_qty` (treat `max_qty: null` as infinity).
- Use THAT tier's `unit_price_usd` and `lead_time_days`. `shelf_life_months` is product-level (same across tiers).
- **EXCLUDE the quote's `prior_unit_price_usd` / line `prior_quote_quantity`** — these are the OLD price at the OLD quantity. The prompt/source_notes explicitly state "catalog tier overrides prior unit price." Using the prior price is the #1 quote misjudgment. (Example: Q-TR-WC-1187 prior_unit_price 124.0 was the 150-299 tier; at 360 units the correct tier is 300-499 @ 118.0.)
- For module RFQs (no quantity tiers, single tier with `min_qty:1`/`max_qty:null`): unit_price is the flat module price; quantity comes from the RFQ `requested_modules[].quantity`.

### 1.3 EXW pricing & totals
- `quote_basis` = `EXW` for freight-option quotes; `EXW_ONLY` for indicative quotes with no destination.
- **EXW excludes freight, insurance, import duty, customs clearance, and last-mile** (policy `POL-EXW-SCOPE` / `EXW_EXCLUSIONS`).
- `exw_total_usd` = `unit_price_usd × confirmed_quantity` (single-line quote), or `Σ(unit_price × quantity)` across module line items.
- Per-freight `grand_total_usd` = `exw_total_usd + freight_cost_usd`.
- For EXW-only/module quotes: `freight_excluded = true`, `grand_total = exw_total` (no freight added), because there is no destination (policy `POL-INDICATIVE-EXW` / `EXW_ONLY_EXCLUDE_FREIGHT`).

### 1.4 Freight option selection & distractor exclusion
A `freight-quotes?quote_id=` response contains REAL options PLUS distractor/benchmark quotes. Select the real options and exclude distractors:

**Exclude a freight quote when ANY of:**
- `destination` contains "Distractor" (e.g. "Distractor route") — it's a benchmark, not the real route.
- `id` contains `DIS-` (distractor naming convention) AND it does not match the 3 transport modes for the real destination.
- It has wrong shipment dimensions that don't match the other real options (distractors often carry a different `shipment_cbm`/`shipment_weight_kg` than the consistent set).

**Keep** the quote's three transport modes (AIR, SEA, ROAD) for the real destination, even if one is stale/expired — a stale road quote is still REPORTED (with validity flags) because the customer asked to compare all three; it is just excluded from the recommendation.

### 1.5 Freight validity vs quote date
- A freight option is **valid on the quote date** iff `status == "active"` AND `valid_until >= quote_date`.
- `valid_until < quote_date` → EXPIRED. `status == "stale"` → source is stale.
- Report per-option:
  - `valid_until` (the date).
  - `validity_status` / `all_freight_options_valid_on_quote_date`: `VALID` if active and valid_until >= quote_date, else `EXPIRED` (or `STALE`).
  - `source_is_stale` (bool) = (`status == "stale"`).
- `freight_reconfirmation_required` = **always true** (policy `POL-FREIGHT-RECONFIRM`: "Freight rates need reconfirmation at final order and are valid only through the freight quote valid_until date."). Set true for every freight-bearing quote.
- `road_quote_invalid_or_stale` (train_004 template) = true when the ROAD freight option is stale or valid_until < quote_date.

### 1.6 Route risk enums & flags
Map the freight record's `route_risk` (lowercase: low/medium/high) to template enums (uppercase: LOW/MEDIUM/HIGH).
- **train_001-style template** (`risk_level` + `risk_flag`):
  - `risk_level` = uppercase(`route_risk`).
  - `risk_flag`: `NONE` when low; derive from `risk_notes` when medium/high — e.g. notes mentioning "border risk medium" → `MEDIUM_BORDER_RISK`. Use `NONE` for low-risk options with no specific flag.
- **train_004-style template** (`customs_border_risk`):
  - `customs_border_risk` = uppercase(`route_risk`). ROAD high-risk notes ("customs risk high") → `HIGH`.

### 1.7 Recommended transport mode rule
1. Start from the REAL freight options (distractors excluded, §1.4).
2. Filter to options VALID on the quote date (`status==active` AND `valid_until >= quote_date`). Stale/expired options are never recommended.
3. If the product `cold_chain_required == true`, keep only options with `cold_chain_support == true`.
4. Recommend the remaining option with the **lowest `grand_total_usd`**.
5. Safety override: if that lowest-cost option has `route_risk == high`, escalate to the next-cheapest valid option whose risk is not high.

Result on train data: Q-TR-WC-1187 → SEA (cheapest valid, low risk). Q-TR-LD-5521 → SEA (ROAD is stale/excluded; SEA cheapest valid + cold-chain supported). Risk levels are reported as flags but cost drives the recommendation unless a HIGH-risk safety valve triggers.

### 1.8 Payment terms & customer policy
Determine `payment_terms` from the customer record + policies:
- **New NGO client** (`is_recurring == false`, `segment == new_ngo`, `status == prospect`, `payment_profile == NEW_CLIENT_REVIEW`, `client_since == null`) → `PREPAY_100` (policy `POL-NEW-CLIENT-PAYMENT`: "New NGO clients require PREPAY_100 before production release."). Grant terms like "restricted donor review" reinforce prepay.
- **Recurring NGO** (`is_recurring == true`, `segment == recurring_ngo`, `payment_profile == NET_30_AFTER_PO`) → `NET_30_AFTER_PO` (policy `POL-RECURRING-NGO-PAYMENT`), UNLESS `grant_terms` explicitly restrict net terms.
- **Recurring commercial** (`segment == recurring_commercial`, `payment_profile == NET_30_AFTER_PO`) → `NET_30_AFTER_PO`.
- `customer_policy` field (where present) = the segment/policy that applied (e.g. `recurring_ngo`, `new_ngo`, `recurring_commercial`) or the policy id (`POL-RECURRING-NGO-PAYMENT`).

### 1.9 Module-level quote rule (no component expansion)
- For module RFQs (request_type `indicative_module_quote`), quote at the **module line level only** (policy `POL-MODULE-GRANULARITY` / `MODULE_LINES`).
- **DO NOT expand `product.components` into component line items**, and ignore `rfq.component_composition_distractors` — those are explicitly "for medical review only."
- Each `requested_modules[]` entry = one line item: `product_code`, `article_number` (from product record), `quantity`, `unit_price` (single flat tier), `lead_time_days`, `shelf_life_months`, `line_total = unit_price × quantity`.
- `grand_total = Σ line_total`. EXW only, freight excluded (no destination).

### 1.10 WHO documentation flag
- `who_documentation_required` is NOT a field on product records. Derive it from the product family/name:
  - `family == "emergency_health_kit"` OR name contains "IEHK" (Interagency Emergency Health Kit, a WHO-standardized kit) → **true**.
  - Otherwise → false (or omit if the template has no such field).
- Set `offer_validity_days = 30` (policy `POL-QUOTE-VALIDITY`: "Catalog quote pricing is valid for 30 calendar days from quote date; freight validity may expire sooner.").

---

## 2. RECONCILIATION TASK SOP

### 2.1 Identify the entity & fetch records
1. Prompt gives `opportunity_id` (e.g. `OPP-TR-HELIOS`, `OPP-TR-MERIDIAN`) and `customer_id`.
2. `GET /api/opportunities/<opp_id>` → `customer_id`, `stage`, `won_amount_usd`, `outstanding_amount_usd`, `contact`, `phases[]` (each with `phase_id`, `amount_usd`, `completion_date`, `invoice_id`).
3. `GET /api/customers/<customer_id>` → `name`, `contacts`, `segment`, `payment_profile`.
4. `GET /api/invoices?opportunity_id=<opp_id>` → one invoice per phase: `amount_usd`, `status`, `paid_amount_usd`, `outstanding_amount_usd`, `due_date`, `phase_id`, `issue_date`.
5. `GET /api/payments?opportunity_id=<opp_id>` → payments with `invoice_id`, `amount_usd`, `status`, `payment_date`.
6. `GET /api/revenue-journals?opportunity_id=<opp_id>` → revenue journals keyed by `phase_id`/`invoice_id`. **PITFALL: see §2.4.**
7. `/api/search?q=<customer or opportunity name>` or `events?customer_id=` / `vouchers?customer_id=` → linked event + voucher.

### 2.2 Opportunity & milestone mapping
- `stage`: `closed_won` → `WON`; `open`/`in_progress` → `OPEN`; `lost`/`closed_lost` → `LOST`.
- `won_amount` = `opportunity.won_amount_usd`.
- `phase_total_amount` = `Σ phases[].amount_usd`.
- `opportunity_matches_phase_total` / `opportunity_matches_milestones` = (`won_amount == phase_total`). True when they agree.
- Milestones output in **ascending phase order**. Two id conventions seen:
  - train_003-style: `milestone_id` = the stable phase id (e.g. `HEL-P1`, `HEL-P2`) + a `phase_number` (1, 2, …).
  - train_005-style: `milestone_id` = `MS1`/`MS2`/`MS3` (one per phase, ascending). Map phase 1 → MS1, etc. The enum is explicitly `MS1 | MS2 | MS3`.
- `milestone.amount` / `invoice_total` = the phase `amount_usd` (== invoice `amount_usd`).

### 2.3 Invoice & payment state mapping
Per milestone/phase, map invoice + payment data to output enums:

**train_003-style (`payment_status`: PAID | PARTIAL | UNPAID):**
- invoice `status == "paid"` AND `paid_amount_usd == amount_usd` → `PAID`.
- `paid_amount_usd > 0` AND `< amount_usd` → `PARTIAL`.
- `status` in `("unpaid","overdue")` AND `paid_amount_usd == 0` → `UNPAID`. (Overdue invoices are still unpaid.)
- `amount_paid` = invoice `paid_amount_usd`; `amount_unpaid` = invoice `outstanding_amount_usd`.

**train_005-style (`invoice_state`: PAID | OPEN | VOID | UNKNOWN; `payment_state`: PAID | PARTIAL | UNPAID | UNKNOWN):**
- `invoice_state`: `paid` → PAID; `unpaid`/`overdue` → OPEN; `draft`/anything not finalized → UNKNOWN (or VOID if explicitly voided).
- `payment_state`: `paid`+full → PAID; partial → PARTIAL; `unpaid`/`overdue` → UNPAID; `draft` → UNKNOWN.

### 2.4 Revenue-recognition state mapping (CRITICAL PITFALL)
**PITFALL — `revenue-journals` has NO `customer_id` field.** Filtering `revenue-journals?customer_id=<id>` returns `count: 0` even when journals exist. You MUST filter by `opportunity_id` (or `invoice_id`/`phase_id`), or list all `revenue-journals` and match on `phase_id`/`invoice_id`, or use `/api/search?q=<name>`. A returned count of 0 from a `customer_id` filter is a false negative — do NOT conclude "no revenue recognized" from it.

A revenue-journal record looks like: `{id, opportunity_id, invoice_id, phase_id, amount_usd, debit_account:"Deferred Revenue", credit_account:"Implementation Services Revenue", posted_date, status:"posted", memo}`.

Per-milestone `recognition_status`:
- Milestone PAID (or PARTIAL with a payment) AND a posted revenue-journal exists for its `phase_id`/`invoice_id` → `RECOGNIZED` (train_005) / `RECOGNIZED` (train_003).
- Milestone PAID but NO revenue-journal found → `MISSING_REVENUE_JOURNAL` (train_005) / `REQUIRED_MISSING` (train_003). **This is the key train_005 case: Meridian P2 is paid (PAY-MERIDIAN-P2 posted) but has no RJ-MERIDIAN-P2.** Policy `POL-REVREC` requires recognizing revenue when a milestone is complete and paid.
- Milestone UNPAID/PARTIAL-not-fully-paid → `NOT_REQUIRED_UNPAID` (recognition not required until paid). No unpaid milestone should be flagged missing a journal.
- Unknown/no invoice → `UNKNOWN`.

Overall `recognition_status` / `recognition_status` (revenue_recognition block):
- All PAID milestones have journals → `COMPLETE_FOR_PAID_MILESTONES`.
- At least one PAID milestone lacks a journal → `MISSING_FOR_PAID_MILESTONES`.
- No paid milestones at all → `NOT_REQUIRED`.
- `recognized_milestones` = list of phase ids with posted journals; `missing_required_milestones` = paid phase ids lacking journals; `recognized_amount` = `Σ` of posted journal amounts.

Examples: HELIOS → P1 paid+recognized, P2 unpaid → `COMPLETE_FOR_PAID_MILESTONES`, recognized=`[HEL-P1]`, missing=`[]`, recognized_amount=50000. MERIDIAN → P1 recognized, P2 paid+MISSING, P3 unpaid → `MISSING_FOR_PAID_MILESTONES`, recognized=`[MER-P1]`(or `MS1`), missing=`[MS2]`, recognized_amount=30000.

### 2.5 Outstanding balance & paid totals
- `outstanding_balance` = `Σ invoice.outstanding_amount_usd` across all milestone invoices == `opportunity.outstanding_amount_usd` (they should agree).
- `total_paid_amount` = `Σ invoice.paid_amount_usd` == `Σ payment.amount_usd` (posted payments).
- `won_amount` should equal `total_paid + outstanding_balance` (and equal `phase_total`).

### 2.6 Due-date convention — PAID milestones get null due_date
- **OUTPUT convention:** in the milestones array, `due_date` = **null for PAID milestones** (the obligation is settled; "due_date when applicable" means only outstanding milestones carry a due date). For UNPAID/PARTIAL/open milestones, `due_date` = the invoice `due_date`.
- The API invoices all carry a populated `due_date` regardless of status — nulling it is an output formatting rule, not an API fact.
- Examples: HELIOS P1 (paid) → due_date null; P2 (unpaid) → 2026-06-27. MERIDIAN MS1/MS2 (paid) → null; MS3 (unpaid) → 2026-07-15.

### 2.7 Follow-up task routing (collection vs accounting vs event-invitation)
Distinguish THREE routing lanes; do not conflate them:

**(A) COLLECTION lane** — for any milestone with `amount_unpaid > 0`. Task ties to the unpaid milestone + the account contact.
- train_003-style (`follow_up_tasks[]`): `task_type=COLLECTION`, `next_action=COLLECT_UNPAID_MILESTONE`, `milestone_id=<unpaid phase id>`, `amount_due=<outstanding>`, `due_date=<invoice due_date>`, `event_id=null`, `voucher_code=null`, `contact_name=<account contact>`, `linked_customer_id`, `linked_opportunity_id`.
- train_005-style (`collection_task` + `collection_action` enum: `MONITOR_UNPAID_NOT_DUE | SEND_COLLECTION_NOTICE | NO_COLLECTION_ACTION`):
  - Establish the `as_of_date` from the prompt (e.g. 2026-06-01).
  - Unpaid milestone whose `due_date <= as_of_date` (or invoice `status=="overdue"`) → `SEND_COLLECTION_NOTICE`, `owner_queue=COLLECTIONS`.
  - Unpaid milestone whose `due_date > as_of_date` (not yet due) → `MONITOR_UNPAID_NOT_DUE`, `owner_queue=ACCOUNT_MANAGEMENT`. (MERIDIAN MS3 due 2026-07-15 as of 2026-06-01 → MONITOR.)
  - No unpaid milestone → `NO_COLLECTION_ACTION`, milestone_id `NONE`, owner_queue `NONE`.

**(B) ACCOUNTING lane** — revenue recognition. `primary_accounting_action` / `accounting_action` enum: `RECORD_REVENUE_MS2 | VERIFY_REVENUE_ONLY | NO_ACCOUNTING_ACTION`.
- If a PAID milestone lacks a revenue journal → `RECORD_REVENUE_<MSn>`. Action object: `milestone_id=<that MSn>`, `amount=<milestone amount>`, `debit_account=DEFERRED_REVENUE`, `credit_account=IMPLEMENTATION_SERVICES_REVENUE`, `owner_queue=ACCOUNTING`. (MERIDIAN MS2 paid+missing → `RECORD_REVENUE_MS2`, 45000, debit DEFERRED_REVENUE, credit IMPLEMENTATION_SERVICES_REVENUE, ACCOUNTING.) The debit/credit accounts come straight from existing posted journal records in the API.
- If all paid milestones already have journals → `VERIFY_REVENUE_ONLY` (verify, don't create), `milestone_id=NONE`, amount 0, debit/credit `NONE`, owner_queue `ACCOUNTING`.
- If no paid milestones → `NO_ACCOUNTING_ACTION`.

**(C) EVENT-INVITATION lane** — for the linked event/voucher.
- train_003-style: `task_type=EVENT_INVITATION`, `next_action=SEND_EVENT_INVITATION`, `event_id=<event id>`, `voucher_code=<voucher code>`, `milestone_id=null`, `amount_due=null`, `due_date=<event date or pre-event date>`, contact = account contact.
- train_005-style (`invite_action` enum: `SEND_BRIEFING_INVITE | VERIFY_INVITE_SENT | NO_INVITE_ACTION`; `invite_task`):
  - Event `status=="scheduled"`/`confirmed` AND voucher `redemptions_used == 0` (invite not yet sent) → `SEND_BRIEFING_INVITE` (MERIDIAN briefing: scheduled, 0 redemptions).
  - Invite already sent (redemptions > 0 / status shows invited) → `VERIFY_INVITE_SENT`.
  - No linked event → `NO_INVITE_ACTION`.
  - `invite_task.owner_queue` = map event `follow_up_owner` ("Account Management" → `ACCOUNT_MANAGEMENT`; "Events" → `EVENTS`). `contact_name` = account contact; `customer_id` = customer; `event_id` + `voucher_code` carried through.

### 2.8 Event & voucher linkage
- Event record: `{id, customer_id, opportunity_id, event_date, status, primary_contact, follow_up_owner, voucher_code, name}`.
- Voucher record: `{code, customer_id, opportunity_id, event_id, discount_percent, max_redemptions, redemptions_used, status, valid_until, description}`.
- Output mapping:
  - `event_id`, `event_date` from event.
  - `voucher_code` from event.voucher_code (== voucher.code). `voucher_discount` = voucher `discount_percent` (an integer percent, e.g. 50 or 100). `voucher_max_uses` / `voucher_max_uses` = voucher `max_redemptions`.
  - `event_status` enum (`SCHEDULED|ACTIVE|COMPLETED|CANCELLED|UNKNOWN`): map `scheduled`→SCHEDULED, `confirmed`→ACTIVE, `completed`→COMPLETED, `cancelled`→CANCELLED.
  - `voucher_status` enum (`ACTIVE|DRAFT|EXPIRED|DISABLED|UNKNOWN`): map voucher `status` ("active"→ACTIVE, "draft"→DRAFT, "expired"→EXPIRED, "disabled"→DISABLED).

### 2.9 Contact linkage
- The account contact named in the prompt (e.g. "Mara Okafor", "Daniel Rees") must appear on every follow-up task and in the primary_contact block.
- Source: `opportunity.contact` and/or `customer.contacts[].name` (match by name). Tie to `customer_id` and `opportunity_id`.
- train_003 `contact` block: `{name, linked_customer_id, linked_opportunity_id}`.
- train_005 `primary_contact` block: `{contact_name, customer_id}`.

---

## 3. Output field definitions & controlled enums (reference)

### QUOTE — train_001 style (`quote_summary` + `freight_options` + `policy_flags`)
- `quote_summary`: `quote_id`, `customer_id`, `quote_date`, `product_code`, `confirmed_quantity`, `unit_price_usd` (tier price), `lead_time_days` (tier), `shelf_life_months` (product), `quote_basis`="EXW", `exw_total_usd`.
- `freight_options[]` (one per real mode AIR/SEA/ROAD): `freight_id`, `mode` (AIR|SEA|ROAD), `freight_cost_usd`, `transit_days` (use the API `transit_days_text` e.g. "4-6 days"), `valid_until`, `risk_level` (LOW|MEDIUM|HIGH), `risk_flag` (NONE|MEDIUM_BORDER_RISK|…), `grand_total_usd`.
- `policy_flags`: `recommended_mode`, `freight_reconfirmation_required` (true), `all_freight_options_valid_on_quote_date` (bool), `customer_policy`, `payment_terms`.

### QUOTE — train_002 style (module/EXW-only)
- `quote_header`: `rfq_id`, `customer_id`, `quote_date`, `currency`="USD", `quote_basis`="EXW_ONLY".
- `line_items[]`: `product_code`, `article_number`, `quantity`, `unit_price`, `lead_time_days`, `shelf_life_months`, `line_total`.
- `quote_controls`: `grand_total` (= Σ line_total), `freight_excluded`=true, `payment_terms` (PREPAY_100 for new NGO), `offer_validity_days`=30, `who_documentation_required`=true for IEHK/emergency_health_kit.

### QUOTE — train_004 style (`pricing` + `transport_decisions` + `client_warnings`)
- `pricing`: `quote_id`, `customer_id`, `quote_date`, `product_code`, `confirmed_quantity`, `catalog_tier` {min_quantity, max_quantity, unit_price_usd, lead_time_days, shelf_life_months}, `exw_total_usd`, `payment_terms`.
- `transport_decisions.freight_options[]`: `freight_id`, `mode`, `freight_cost_usd`, `transit_days`, `valid_until`, `validity_status` (VALID|EXPIRED|STALE), `source_is_stale` (bool), `customs_border_risk` (LOW|MEDIUM/HIGH), `grand_total_usd`. `recommended_mode`, `freight_reconfirmation_required` (true).
- `client_warnings`: `road_quote_invalid_or_stale` (bool), `freight_warning` (string), `policy_terms` {quote_basis, payment_terms, freight_reconfirmation_required}.

### RECONCILIATION — train_003 style
- `account_status`: customer_id, customer_name, opportunity_id, opportunity_stage (WON|OPEN|LOST), won_amount, opportunity_matches_milestones (bool), outstanding_balance, contact{name, linked_customer_id, linked_opportunity_id}.
- `milestones[]`: milestone_id (phase id), phase_number, invoice_total, payment_status (PAID|PARTIAL|UNPAID), amount_paid, amount_unpaid, due_date (null if paid), revenue_recognition_status (RECOGNIZED|REQUIRED_MISSING|NOT_REQUIRED_UNPAID).
- `revenue_recognition`: recognition_status (COMPLETE_FOR_PAID_MILESTONES|MISSING_FOR_PAID_MILESTONES|NOT_REQUIRED), recognized_milestones[], missing_required_milestones[], recognized_amount.
- `event`: event_id, event_date, voucher_code, voucher_discount (discount_percent), voucher_max_uses (max_redemptions).
- `follow_up_tasks[]`: task_type (COLLECTION|EVENT_INVITATION), task_title, linked_customer_id, linked_opportunity_id, contact_name, due_date, next_action (COLLECT_UNPAID_MILESTONE|SEND_EVENT_INVITATION), milestone_id (or null), amount_due (or null), event_id (or null), voucher_code (or null).

### RECONCILIATION — train_005 style
- `engagement_reconciliation`: as_of_date, opportunity_id, customer_id, customer_name, stage (WON|OPEN|LOST), won_amount, phase_total_amount, opportunity_matches_phase_total (bool), total_paid_amount, outstanding_balance, primary_contact{contact_name, customer_id}, milestones[] {milestone_id (MS1|MS2|MS3 ascending), amount, invoice_state (PAID|OPEN|VOID|UNKNOWN), payment_state (PAID|PARTIAL|UNPAID|UNKNOWN), paid_amount, due_date (null if paid), recognition_status (RECOGNIZED|MISSING_REVENUE_JOURNAL|NOT_REQUIRED_UNPAID|UNKNOWN)}.
- `invoice_actions`: primary_accounting_action (RECORD_REVENUE_MS2|VERIFY_REVENUE_ONLY|NO_ACCOUNTING_ACTION), collection_action (MONITOR_UNPAID_NOT_DUE|SEND_COLLECTION_NOTICE|NO_COLLECTION_ACTION), accounting_action{action, milestone_id(MS1|MS2|MS3|NONE), amount, debit_account(DEFERRED_REVENUE|ACCOUNTS_RECEIVABLE|CASH|NONE), credit_account(IMPLEMENTATION_SERVICES_REVENUE|DEFERRED_REVENUE|ACCOUNTS_RECEIVABLE|NONE), owner_queue(ACCOUNTING|ACCOUNT_MANAGEMENT|NONE)}, collection_task{action, milestone_id, amount, due_date, owner_queue(ACCOUNT_MANAGEMENT|COLLECTIONS|NONE), contact_name}.
- `event_actions`: event_id, event_status (SCHEDULED|ACTIVE|COMPLETED|CANCELLED|UNKNOWN), voucher{voucher_code, voucher_status(ACTIVE|DRAFT|EXPIRED|DISABLED|UNKNOWN), discount_amount, max_uses}, invite_action (SEND_BRIEFING_INVITE|VERIFY_INVITE_SENT|NO_INVITE_ACTION), invite_task{action, event_id, voucher_code, owner_queue(ACCOUNT_MANAGEMENT|EVENTS|NONE), contact_name, customer_id}.

---

## 4. Common misjudgments & exclusions (checklist)

1. **Using prior_unit_price instead of catalog tier.** The quote's `prior_unit_price_usd`/`prior_quote_quantity` is the OLD price at the OLD qty. Always recompute the tier from `confirmed_quantity` against `product.price_tiers`.
2. **EXW-only quotes including freight.** Indicative/module quotes with no destination are EXW_ONLY — `freight_excluded=true`, no freight options, `grand_total=exw_total`. Only quotes with a destination carry freight options.
3. **EXW total including freight.** `exw_total` is product-only (excludes freight/insurance/duty/customs/last-mile per POL-EXW-SCOPE). `grand_total = exw_total + freight_cost` per option, separately.
4. **Expanding module RFQs into component lines.** Module RFQs stay at module line level (POL-MODULE-GRANULARITY). `product.components` and `rfq.component_composition_distractors` are distractors — do not emit component SKUs.
5. **Treating distractor freight quotes as real options.** Exclude `destination` containing "Distractor", `id` with `DIS-`, or wrong shipment dimensions. But KEEP a stale ROAD option (it's a real mode the customer asked to compare) — just flag it stale/expired.
6. **Recommending a stale/expired freight option.** Stale (`status=="stale"`) or `valid_until < quote_date` options are never the recommended mode.
7. **Forgetting freight reconfirmation.** `freight_reconfirmation_required` is always true (POL-FREIGHT-RECONFIRM) for any freight-bearing quote.
8. **Filtering revenue-journals by customer_id.** That collection has NO `customer_id` field — the filter returns 0 (false negative). Use `opportunity_id` (or `invoice_id`/`phase_id`), list-all-and-match, or `/api/search`. Concluding "no journal exists" from a customer_id filter = wrong.
9. **Flagging an UNPAID milestone as missing a revenue journal.** Recognition is only required for PAID milestones. Unpaid → `NOT_REQUIRED_UNPAID`, never `MISSING`.
10. **Missing a PAID milestone that lacks a journal.** A paid milestone with no matching revenue-journal (by phase_id/invoice_id) → `MISSING_REVENUE_JOURNAL`/`REQUIRED_MISSING` and an accounting `RECORD_REVENUE` action. (Meridian P2 is the canonical case.)
11. **Due_date on paid milestones.** Output `due_date=null` for PAID milestones; only outstanding milestones carry the invoice due_date.
12. **New-client payment terms.** New NGO (not recurring, prospect, NEW_CLIENT_REVIEW, client_since null) → `PREPAY_100`, not net terms, even if they're an NGO. Grant-term restrictions reinforce prepay.
13. **WHO documentation flag.** Derive `who_documentation_required` from `family=="emergency_health_kit"`/IEHK name — it's not a product-record field. True for IEHK modules.
14. **offer_validity_days.** = 30 (POL-QUOTE-VALIDITY), not the freight valid_until.
15. **Narrative vs API name mismatch.** Prompt customer names are often paraphrased ("Health Horizon Aid" vs API "HealthHands Alliance"; "GreenHarvest Labs" vs API "Global Health Laboratories"). Use the API `name`. Match the entity by the ID given in the prompt.
16. **Conflating collection / accounting / event-invitation routing.** Collection = unpaid milestone (owner COLLECTIONS if overdue, ACCOUNT_MANAGEMENT if not-yet-due). Accounting = missing revenue journal for a PAID milestone (owner ACCOUNTING, debit DEFERRED_REVENUE / credit IMPLEMENTATION_SERVICES_REVENUE). Event-invitation = linked event/voucher (owner from event.follow_up_owner). Each is a separate task; an unpaid milestone does not create an accounting action, and a missing journal does not create a collection task.

---

## 5. Step-by-step execution recipe

### For a QUOTE task
1. Parse quote_id/rfq_id + confirmed quantity + quote_date + destination from prompt.
2. `GET /api/quotes/<id>` (or `/rfqs/<id>`); `GET /api/customers/<customer_id>`; `GET /api/products/<product_code>`; `GET /api/freight-quotes?quote_id=<id>`; `GET /api/policies`.
3. Select catalog tier by quantity; compute `exw_total = unit_price × qty`.
4. If destination present: select real freight options (exclude distractors); for each compute `grand_total = exw_total + freight_cost`; map risk + validity. Pick recommended_mode (§1.7). Set `freight_reconfirmation_required=true`.
5. If no destination (EXW_ONLY): `freight_excluded=true`, `grand_total=exw_total`, no freight options.
6. Determine `payment_terms` from customer segment + policies (§1.8). For module RFQ set `who_documentation_required` (§1.10) and `offer_validity_days=30`.
7. Fill the template exactly (field names, enums, nesting). Output JSON only.

### For a RECONCILIATION task
1. Parse opportunity_id + customer_id (+ as_of_date if given) + account contact name from prompt.
2. `GET /api/opportunities/<opp_id>`; `GET /api/customers/<customer_id>`; `GET /api/invoices?opportunity_id=<opp_id>`; `GET /api/payments?opportunity_id=<opp_id>`; **`GET /api/revenue-journals?opportunity_id=<opp_id>`**; `/api/search?q=<name>` for events/vouchers.
3. Map stage → WON/OPEN/LOST; verify `won_amount == Σ phase amounts`.
4. For each phase (ascending): map invoice_state/payment_state; set paid_amount/outstanding; set due_date=null if paid else invoice.due_date; set recognition_status by checking for a matching revenue-journal (§2.4).
5. Compute total_paid, outstanding_balance, overall recognition_status.
6. Route follow-ups: COLLECTION for unpaid milestones (MONITOR vs NOTICE by as_of_date vs due_date); ACCOUNTING for paid+missing-journal milestones (RECORD_REVENUE, DEFERRED_REVENUE→IMPLEMENTATION_SERVICES_REVENUE, ACCOUNTING); EVENT_INVITATION for the linked event+voucher (SEND vs VERIFY by redemptions/status).
7. Fill the template exactly. Output JSON only (no prose, no markdown fences).
