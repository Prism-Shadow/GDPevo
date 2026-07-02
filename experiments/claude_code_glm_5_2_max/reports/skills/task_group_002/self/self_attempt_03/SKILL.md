# MedBridge Sales Ops — Quote & Reconciliation SOP Skill

Transferable, executable standard-operating procedures for MedBridge Sales Ops CRM tasks. Distilled from hands-on reconciliation of the 5 official train tasks against the live remote API (no gold answers used). Applies to two task families: **QUOTE** (customer RFQ/quote → account-ready quote decision package) and **RECONCILIATION** (won opportunity → finance-ready engagement reconciliation).

The remote API is the single source of truth. Reconcile the prompt narrative against API records; **trust the API over narrative wording** when they conflict, but read the prompt carefully for *which* entity (quote id, opportunity id, customer id, product code) to reconcile.

---

## 1. Environment & API usage rules

Base URL is in `environment_access.md` (e.g. `<remote-env-url>`). All GET, all JSON. Pipe with `curl -s "..." | python3 -m json.tool`.

- `GET /health` → sanity (`{"ok": true, ...}`). `GET /api` → lists `collections` + `endpoints`.
- `GET /api/<collection>` → all records `{collection, count, records}`.
- `GET /api/<collection>?<key>=<value>` → filter (case-insensitive, matches nested keys, numeric tolerance 2dp). Multiple filters AND together.
- `GET /api/<collection>/<id>` → single record by id. **Detail-by-id is ONLY available for:** `customers`, `products`, `rfqs`, `quotes`, `freight-quotes`, `opportunities`. For `invoices`, `payments`, `revenue-journals`, `events`, `vouchers`, `policies` use listing/filter endpoints.
- `GET /api/search?q=<text>` → substring search across ALL collections (≤100 hits, each tagged `collection`+`id`). Great for finding a customer by name or a product by code when you only have a label.

### Collections
`customers, products, rfqs, quotes, freight-quotes, policies, opportunities, invoices, payments, revenue-journals, events, vouchers`.

### Reliable filter keys (verified)
- invoices / payments / events / vouchers / revenue-journals → filter by **`opportunity_id`** (most reliable; these collections all carry `opportunity_id`).
- invoices / payments / events / vouchers → also filter by `customer_id`.
- **revenue-journals may NOT usefully filter by `customer_id`** (it has no customer_id field) — **always filter revenue-journals by `opportunity_id`**. (Confirmed: `?opportunity_id=OPP-TR-HELIOS` returns the posted journal; `?customer_id=...` is unreliable.)
- freight-quotes → filter by `quote_id`.

### ID conventions (important for avoiding decoys)
- `TR` = train, `TE` = test (real task records). `DIS` = **distractor/decoy** records planted to trap you (e.g. `Q-DIS-PPE-1402`, `RFQ-DIS-004`, `OPP-DIS-RIVERBEND`, `FR-DIS-WC-OLD-AIR`, `RFQ-TE-...` is a real test RFQ — do **not** touch test records; only use them to confirm the data model).
- Money = USD, 2 decimals. Dates = ISO `YYYY-MM-DD`. Use stable IDs exactly as returned.
- `generated_at` on `/api` is the environment's "current business date" snapshot (here `2026-06-01T00:00:00Z`). If a reconciliation prompt says "treat <date> as current business date", use that date for due/overdue logic.

---

## 2. TASK FAMILY A — QUOTE (RFQ/quote → decision package)

Trigger: prompt references a **quote id** (`Q-...`) or **RFQ id** (`RFQ-...`), a product/module code, a quantity, a quote date, and asks for pricing + freight + terms.

### 2.1 Fetch the canonical records
1. Quote: `GET /api/quotes/<quote_id>` (or RFQ: `GET /api/rfqs/<rfq_id>`).
2. Customer: `GET /api/customers/<customer_id>` (from quote/rfq `customer_id`).
3. Product: `GET /api/products/<product_code>` (from `primary_product_code` / `requested_modules[].product_code`).
4. Freight quotes: `GET /api/freight-quotes?quote_id=<quote_id>` (only when incoterm includes freight).
5. Policies: `GET /api/policies` (read all 8; match by `applies_to` / `policy_area`).

### 2.2 Catalog tier selection (THE core pricing rule)
Products carry `price_tiers[]` sorted by `min_qty` (with `max_qty` possibly `null` for the top tier). **Select the tier whose `min_qty <= confirmed_quantity <= max_qty`** (treat `null` max as +∞).

- Use the **matched tier's `unit_price_usd`** and `lead_time_days`. **Never use `prior_unit_price_usd`** from the quote line item — that is a distractor reflecting the old quantity's tier. The quote `source_notes` typically confirms *"catalog tier overrides prior unit price."*
- `shelf_life_months` comes from the **product** (not the tier).
- `lead_time_days` comes from the **tier** (some tiers shorten lead time at higher qty — e.g. WC-KIT-A: 35 days for tier 1-2, 28 days for tier 3+).
- Example: WC-KIT-A qty 360 → tier 300-499 @ $118.00 (NOT the old $124.00). LD-REAGENT-44 qty 1000 → tier 900-1199 @ $76.00 (NOT old $79.50).
- EXW total = `confirmed_quantity × tier.unit_price_usd` (2 dp).

### 2.3 EXW vs freight-inclusive (quote basis)
- Quote `incoterm == "EXW plus freight options"` (or `"EXW plus advisory freight options"`) → present EXW pricing **and** freight options; `quote_basis = "EXW"`. Grand total per option = `EXW total + freight_cost_usd`.
- RFQ `incoterm_requested == "EXW"` with **no destination** (e.g. "Destination pending donor allocation") → **EXW only, freight excluded** (policy `POL-INDICATIVE-EXW`, terms_code `EXW_ONLY_EXCLUDE_FREIGHT`). Set `quote_basis = "EXW_ONLY"`, `freight_excluded = true`. Do NOT invent freight.
- EXW commercial scope (policy `POL-EXW-SCOPE`): EXW **excludes** freight, insurance, import duty, customs clearance, and last-mile handling unless explicitly added as separate options. So an EXW-only quote must NOT include any freight cost in its total.

### 2.4 Freight option selection & distractor exclusion
A quote may have **more** freight-quote records than the modes you should present. Exclude distractors; keep real-route quotes (even if stale — flag, don't drop).

**EXCLUDE a freight-quote record when ANY of these is true:**
- `destination` contains the word **"Distractor"** (e.g. "Distractor route") — the canonical decoy signal.
- It is clearly a benchmark for a *different* shipment size (`shipment_cbm`/`shipment_weight_kg` inconsistent with the real options and the product's per-unit cbm/weight × qty). Real-route freight quotes for the same quote share identical `shipment_cbm`/`shipment_weight_kg`.
- The `id` starts with `FR-DIS-` (distractor prefix).

**KEEP** real-route freight quotes (id `FR-<prod>-AIR/SEA/ROAD`, destination = the real quote destination). Even if a real-route quote is **stale/expired**, **include it** in the options array but flag it (see 2.6). Dropping a real but stale mode loses information the account manager asked for.

Example: Q-TR-WC-1187 has 5 freight quotes — keep `FR-WC-AIR/SEA/ROAD` (dest Nairobi/Mombasa-Nairobi, cbm 24.0), drop `FR-DIS-WC-OLD-AIR` + `FR-DIS-WC-HEAVY-SEA` (dest "Distractor route"). Q-TR-LD-5521 has 4 — keep `FR-LD-AIR/SEA/ROAD` (dest Kigali), drop `FR-DIS-LD-OLD-SEA`.

### 2.5 Cold-chain freight filter
If `product.cold_chain_required == true`, only present/recommend freight options whose `cold_chain_support == true` (drop cold-chain-incompatible options from the option set). If all real options support cold chain (typical), this is a no-op but still verify.

### 2.6 Per-option fields & risk/validity mapping
For each kept freight option:
- `freight_id` = record id. `mode` = uppercase of `mode` (`AIR`/`SEA`/`ROAD`).
- `freight_cost_usd` = `cost_usd`. `transit_days` = `transit_days_text` (e.g. "4-6 days"). `valid_until` = `valid_until`.
- `grand_total_usd` = `exw_total_usd + freight_cost_usd` (2 dp).
- **Risk level** (template field `risk_level`): map `route_risk` → `LOW`/`MEDIUM`/`HIGH` (uppercase).
- **Risk flag** (template field `risk_flag`): derive from `risk_notes`/`route_risk`:
  - low → `NONE`
  - medium + border/customs language → `MEDIUM_BORDER_RISK` (train 001 ROAD default; train notes "Border risk medium on northern corridor").
  - high customs → `HIGH_CUSTOMS_RISK`; shelf-life concern → `SHELF_LIFE_REVIEW`. (When the template does not pin an enum, use a concise UPPER_SNAKE flag that names the concern from `risk_notes`.)
- **Validity vs quote date** (key concept: freight validity ≠ quote date):
  - `quote_date` is the commercial quote date (pricing valid 30 days per `POL-QUOTE-VALIDITY`).
  - A freight option is **valid on the quote date** iff `status == "active"` AND `valid_until >= quote_date`.
  - If `status == "stale"` OR `valid_until < quote_date` → the option is stale/expired on the quote date. In templates with `source_is_stale`/`validity_status` (e.g. train 004): `source_is_stale = true`, `validity_status = "STALE"` (or `"EXPIRED"`). In templates with only validity booleans, surface this via the warning/flag fields.

### 2.7 Recommended transport mode (deterministic rule)
**Recommended mode = the lowest-cost freight option among those that are (a) active, (b) valid on the quote date (`valid_until >= quote_date`), (c) `route_risk == "low"`, and (d) cold-chain-compatible if the product requires cold chain.** Tie-break by shorter transit.

- Train 001 (WC-KIT-A, non-cold-chain): low-risk & valid = AIR ($16,200) + SEA ($3,880). Lowest cost → **SEA**.
- Train 004 (LD-REAGENT-44, cold-chain): low-risk & valid & cold-chain = AIR only (SEA is medium risk, ROAD is high risk + stale). → **AIR**.

Caveat / exception: if the prompt or destination signals genuine **emergency** urgency (e.g. "emergency warehouse" with an explicit time-critical note) AND no low-risk cheap mode fits the deadline, escalate to AIR. But absent an explicit deadline constraint, the cost-minimising low-risk rule above is the default — do NOT default to AIR just because it is fastest.

### 2.8 Freight reconfirmation
`freight_reconfirmation_required = true` whenever freight options are presented (policy `POL-FREIGHT-RECONFIRM`: "Freight rates need reconfirmation at final order and are valid only through the freight quote `valid_until` date"). For EXW-only quotes (no freight) this flag is not applicable / omitted.

### 2.9 "All freight options valid on quote date" flag
`all_freight_options_valid_on_quote_date` (train 001) = `true` iff **every kept (non-excluded) freight option** has `valid_until >= quote_date` and `status == "active"`. Excluded distractors do NOT count. (Train 001: all 3 kept valid → true. A train-004-style quote with a stale ROAD would be false, surfaced instead via `road_quote_invalid_or_stale` + `source_is_stale` + a `freight_warning` string.)

### 2.10 Payment terms & customer policy (map by customer type)
Match the customer's `segment`/`payment_profile`/`is_recurring` to a policy:

| Customer signal | Applicable policy | `payment_terms` |
|---|---|---|
| New NGO, `is_recurring=false`, `status=prospect`, `payment_profile=NEW_CLIENT_REVIEW`, `client_since=null` | `POL-NEW-CLIENT-PAYMENT` | `PREPAY_100` |
| Recurring NGO, `is_recurring=true`, `payment_profile=NET_30_AFTER_PO` | `POL-RECURRING-NGO-PAYMENT` | `NET_30_AFTER_PO` |
| Recurring Commercial, `payment_profile=NET_30_AFTER_PO` | (framework agreement) | `NET_30_AFTER_PO` |

- `customer_policy` field (train 001) = the governing policy's `terms_code` (same value as `payment_terms` for these accounts; if a template clearly separates them, use the policy `terms_code` for `customer_policy` and the actual terms for `payment_terms`).
- Always verify the customer's `grant_terms`/`notes` don't override (e.g. restricted donor review on a new client reinforces PREPAY_100).

### 2.11 Module-level granularity (RFQ module quotes)
For RFQs with `request_type` containing `module` (e.g. `indicative_module_quote`):
- Quote **one line per requested module** using `requested_modules[]` order. **Do NOT expand into component SKUs** (policy `POL-MODULE-GRANULARITY`, terms_code `MODULE_LINES`). The RFQ `narrative` usually says "do not split into component SKUs", and `component_composition_distractors[]` lists explicit traps (e.g. "Paracetamol tabs listed under basic module") — ignore them.
- Each module product typically has a **single price tier** (`min_qty:1, max_qty:null`). `unit_price` = that tier's price; `line_total` = `quantity × unit_price`.
- `article_number` comes from the product record.
- `grand_total` = sum of line_totals.
- `offer_validity_days` = 30 (policy `POL-QUOTE-VALIDITY`: catalog pricing valid 30 days).

### 2.12 WHO documentation flag
`who_documentation_required` (when the template has this field, e.g. train 002 quote_controls): set `true` for **WHO-standard kit families** — products whose code/family indicate WHO Interagency Emergency Health Kits (e.g. `IEHK-*`, `emergency_health_kit` family). Set `false` for non-WHO-standard catalog products (wound-care kits, lab reagents, etc.). The IEHK modules are WHO-standard → `true`.

### 2.13 Quote decision-package field map (by template variant)
Templates vary; fill exactly the field names declared. Common variants:
- **Revision-with-freight (train 001 style):** `quote_summary{quote_id, customer_id, quote_date, product_code, confirmed_quantity, unit_price_usd, lead_time_days, shelf_life_months, quote_basis="EXW", exw_total_usd}`, `freight_options[]` (3: AIR/SEA/ROAD with `freight_id, mode, freight_cost_usd, transit_days, valid_until, risk_level, risk_flag, grand_total_usd`), `policy_flags{recommended_mode, freight_reconfirmation_required, all_freight_options_valid_on_quote_date, customer_policy, payment_terms}`.
- **Module EXW-only (train 002 style):** `quote_header{rfq_id, customer_id, quote_date, currency="USD", quote_basis="EXW_ONLY"}`, `line_items[]` (one per module: `product_code, article_number, quantity, unit_price, lead_time_days, shelf_life_months, line_total`), `quote_controls{grand_total, freight_excluded=true, payment_terms="PREPAY_100", offer_validity_days=30, who_documentation_required}`.
- **Revision-with-freight + catalog_tier (train 004 style):** `pricing{quote_id, customer_id, quote_date, product_code, confirmed_quantity, catalog_tier{min_quantity, max_quantity, unit_price_usd, lead_time_days, shelf_life_months}, exw_total_usd, payment_terms}`, `transport_decisions{freight_options[] (with validity_status, source_is_stale, customs_border_risk), recommended_mode, freight_reconfirmation_required}`, `client_warnings{road_quote_invalid_or_stale, freight_warning, policy_terms{quote_basis, payment_terms, freight_reconfirmation_required}}`.

---

## 3. TASK FAMILY B — RECONCILIATION (won opportunity → finance-ready)

Trigger: prompt references an **opportunity id** (`OPP-...`) and **customer id** (`CUST-...`), a named account contact, milestone invoices, payments, revenue recognition, and a linked event/voucher.

### 3.1 Fetch the canonical records
1. `GET /api/opportunities/<opportunity_id>` — has `stage`, `won_amount_usd`, `outstanding_amount_usd`, `phases[]` (each with `phase_id`, `amount_usd`, `completion_date`, `invoice_id`), `contact`.
2. `GET /api/customers/<customer_id>` — `name`, `contacts[]`, `payment_profile`, `segment`.
3. `GET /api/invoices?opportunity_id=<opp>` — one invoice per phase (`phase_id`, `amount_usd`, `status`, `paid_amount_usd`, `outstanding_amount_usd`, `due_date`, `issue_date`).
4. `GET /api/payments?opportunity_id=<opp>` — posted payments (`invoice_id`, `amount_usd`, `status`, `payment_date`).
5. `GET /api/revenue-journals?opportunity_id=<opp>` — **filter by opportunity_id, NOT customer_id.** Each journal has `phase_id`, `invoice_id`, `amount_usd`, `status` (posted), `debit_account`, `credit_account`, `posted_date`.
6. `GET /api/events?opportunity_id=<opp>` (or `?customer_id=`) — `event_id`, `event_date`, `status`, `voucher_code`, `primary_contact`, `follow_up_owner`.
7. `GET /api/vouchers?customer_id=<cust>` or `GET /api/search?q=<voucher_code>` — `code`, `status`, `discount_percent`, `max_redemptions`, `valid_until`, `event_id`.

### 3.2 Phase / milestone matching
- `phase_total_amount` = sum of `phases[].amount_usd`.
- `opportunity_matches_milestones` / `opportunity_matches_phase_total` = (`phase_total_amount == won_amount_usd`).
- Map phases to milestone identifiers per the template:
  - Train 003 template: `milestone_id` is a free string + `phase_number` (1-based) → use the API `phase_id` (e.g. `HEL-P1`, `HEL-P2`) as `milestone_id`, and the phase's ordinal as `phase_number`.
  - Train 005 template: `milestone_id` is the enum `MS1|MS2|MS3` ordered ascending → map the Nth phase to `MS<N>` (phase 1 → MS1, phase 2 → MS2, …). Order ascending by milestone_id.

### 3.3 Invoice & payment state mapping (per milestone)
For each phase/milestone, join its invoice (`invoice_id`) and any posted payment:
- **invoice_state** (train 005 enum `PAID|OPEN|VOID|UNKNOWN`): map invoice `status` → `paid`→`PAID`, `unpaid`→`OPEN`, `void`→`VOID`, else `UNKNOWN`.
- **payment_status / payment_state** (enum `PAID|PARTIAL|UNPAID` [003] / `PAID|PARTIAL|UNPAID|UNKNOWN` [005]):
  - `paid_amount_usd == amount_usd` (>0) → `PAID`
  - `0 < paid_amount_usd < amount_usd` → `PARTIAL`
  - `paid_amount_usd == 0` → `UNPAID`
- `invoice_total` / `amount` = invoice `amount_usd`.
- `amount_paid` / `paid_amount` = invoice `paid_amount_usd`.
- `amount_unpaid` = invoice `outstanding_amount_usd` (or `amount - paid_amount`).
- **`due_date` rule (critical):** a **fully-PAID milestone has `due_date = null`** (the obligation is closed; no further due timing). Only **unpaid/partial** milestones carry `due_date` = the invoice `due_date`. (Training signal: both Helios P1 and Meridian P1/P2 are paid → null; unpaid P2/P3 carry their invoice due_date.)

### 3.4 Revenue-recognition state mapping (per milestone)
Join each phase to its revenue-journal (match `phase_id`). Recognised iff a journal exists with `status == "posted"`.

- Train 003 enum `revenue_recognition_status`: `RECOGNIZED` | `REQUIRED_MISSING` | `NOT_REQUIRED_UNPAID`.
  - paid + posted journal → `RECOGNIZED`
  - paid + **no** journal → `REQUIRED_MISSING`
  - unpaid/partial → `NOT_REQUIRED_UNPAID`
- Train 005 enum `recognition_status`: `RECOGNIZED` | `MISSING_REVENUE_JOURNAL` | `NOT_REQUIRED_UNPAID` | `UNKNOWN`.
  - paid + posted journal → `RECOGNIZED`
  - paid + **no** journal → `MISSING_REVENUE_JOURNAL`
  - unpaid/partial → `NOT_REQUIRED_UNPAID`
- **The enum names differ between templates — always use the exact enum declared in THAT task's `answer_template.json`.** Same concept, different label (`REQUIRED_MISSING` vs `MISSING_REVENUE_JOURNAL`).

### 3.5 Revenue-recognition rollup (train 003 `revenue_recognition` block)
- `recognition_status`:
  - `COMPLETE_FOR_PAID_MILESTONES` — every paid milestone has a posted journal.
  - `MISSING_FOR_PAID_MILESTONES` — ≥1 paid milestone lacks a posted journal.
  - `NOT_REQUIRED` — no paid milestones exist.
- `recognized_milestones[]` = milestone_ids with a posted journal.
- `missing_required_milestones[]` = paid milestone_ids lacking a posted journal.
- `recognized_amount` = sum of posted journal `amount_usd`.

### 3.6 Outstanding balance & totals
- `outstanding_balance` = opportunity `outstanding_amount_usd` **and** must equal sum of unpaid invoices' `outstanding_amount_usd`. Verify they agree; if they differ, prefer the invoice-sum (the API opportunity field is a snapshot).
- `total_paid_amount` (train 005) = sum of posted payments (or sum of invoices' `paid_amount_usd`).

### 3.7 Accounting action routing (train 005 `invoice_actions.accounting_action`)
Policy `POL-REVREC`: *"When a milestone is complete and paid, create or verify revenue recognition from deferred revenue to income."*

- If a paid milestone lacks a posted revenue journal → **`RECORD_REVENUE_<MS>`** (e.g. `RECORD_REVENUE_MS2`):
  - `milestone_id` = that MS, `amount` = invoice `amount_usd`,
  - `debit_account = DEFERRED_REVENUE`, `credit_account = IMPLEMENTATION_SERVICES_REVENUE` (this is the journal posting pattern: Dr Deferred Revenue / Cr Implementation Services Revenue),
  - `owner_queue = ACCOUNTING`.
- If all paid milestones have posted journals → **`VERIFY_REVENUE_ONLY`**: `milestone_id = NONE`, `amount` = recognised amount (or 0), `debit_account = NONE`, `credit_account = NONE`, `owner_queue = ACCOUNTING`.
- If no paid milestones → **`NO_ACCOUNTING_ACTION`**: all NONE.
- `primary_accounting_action` (top-level) mirrors `accounting_action.action`.

### 3.8 Collection action routing (train 005 `invoice_actions.collection_task`)
Only route collection for **unpaid or partial** milestones.
- Compute against the **current business date** (`as_of_date`, from the prompt or `generated_at`).
- If unpaid milestone `due_date > as_of_date` (not yet due) → **`MONITOR_UNPAID_NOT_DUE`**, `owner_queue = ACCOUNT_MANAGEMENT`.
- If `due_date <= as_of_date` (due/overdue) → **`SEND_COLLECTION_NOTICE`**, `owner_queue = COLLECTIONS`.
- If no unpaid/partial milestones → **`NO_COLLECTION_ACTION`**, all NONE.
- `collection_task`: `milestone_id`, `amount` = outstanding amount, `due_date` = invoice due_date, `contact_name` = account contact.
- `collection_action` (top-level) mirrors `collection_task.action`.

### 3.9 Event & voucher linkage (train 005 `event_actions` / train 003 `event` + `follow_up_tasks`)
Find the event linked to the opportunity (`events?opportunity_id=`); the event carries `voucher_code`; fetch the voucher.
- `event_id`, `event_date` from the event.
- `event_status` enum `SCHEDULED|ACTIVE|COMPLETED|CANCELLED|UNKNOWN`: map event `status` → `scheduled`→`SCHEDULED`, `active`→`ACTIVE`, `confirmed`→`ACTIVE`, `completed`→`COMPLETED`, `cancelled`→`CANCELLED`, else `UNKNOWN`.
- `voucher`: `voucher_code`, `voucher_status` (map voucher `status` → `ACTIVE|DRAFT|EXPIRED|DISABLED|UNKNOWN`), `discount_amount` = the voucher's **`discount_percent`** value (the API stores percent, not a fixed USD amount; use the percent as the number), `max_uses` = `max_redemptions`.
- **invite_action** enum `SEND_BRIEFING_INVITE|VERIFY_INVITE_SENT|NO_INVITE_ACTION`:
  - Event future & invite not yet sent (status scheduled/confirmed, `redemptions_used == 0`) → `SEND_BRIEFING_INVITE`.
  - Invite appears sent (status active, `redemptions_used > 0`, or a sent marker) → `VERIFY_INVITE_SENT`.
  - Event completed/cancelled → `NO_INVITE_ACTION`.
- **invite_task.owner_queue = EVENTS** (event invitations route to the EVENTS queue — distinct from accounting → ACCOUNTING and collection → ACCOUNT_MANAGEMENT/COLLECTIONS). `contact_name` = event `primary_contact` (== opportunity contact), `customer_id` = customer.

### 3.10 Train 003 `follow_up_tasks[]` (simpler template, two task types)
Enum `task_type: COLLECTION|EVENT_INVITATION`, `next_action: COLLECT_UNPAID_MILESTONE|SEND_EVENT_INVITATION`.
- One **COLLECTION** task per unpaid/partial milestone: `next_action=COLLECT_UNPAID_MILESTONE`, `milestone_id`=phase_id, `amount_due`=outstanding, `due_date`=invoice due_date, `event_id=null`, `voucher_code=null`.
- One **EVENT_INVITATION** task for the linked event: `next_action=SEND_EVENT_INVITATION`, `event_id`, `voucher_code`, `milestone_id=null`, `amount_due=null`, `due_date`=event_date.
- `linked_customer_id`, `linked_opportunity_id`, `contact_name` = the named account contact on every task. (Train 003 template has no `owner_queue` field — omit.)
- Note: train 003's enum has no MONITOR option, so an unpaid-but-not-yet-due milestone still produces a `COLLECT_UNPAID_MILESTONE` collection task (the outstanding receivable is the signal, not the due-date nuance). Use the rich MONITOR/NOTICE split only where the template declares it (train 005).

### 3.11 Contact linkage
The prompt names the account contact (e.g. "Mara Okafor", "Daniel Rees"). That contact appears in `customer.contacts[]` and as `opportunity.contact` / `event.primary_contact`. Link: `contact.name`, `linked_customer_id`/`customer_id` = the customer id, `linked_opportunity_id`/`opportunity_id` = the opportunity id.

### 3.12 Stage mapping
`opportunity.stage` → template `stage`/`opportunity_stage`: `closed_won`→`WON`, `open`/`proposal`/`negotiation`/`qualification`→`OPEN`, `closed_lost`→`LOST`. (Train: both `closed_won` → `WON`.)

---

## 4. Common misjudgments & exclusions checklist

1. **Using `prior_unit_price_usd` instead of the catalog tier.** Always recompute the tier from `confirmed_quantity`. The prior price is a distractor.
2. **Including freight in an EXW-only total.** EXW excludes freight/insurance/duty/customs/last-mile (`POL-EXW-SCOPE`). EXW-only quotes must have `freight_excluded=true` and no freight in the grand total.
3. **Expanding module RFQs into component lines.** Keep module-level granularity (`POL-MODULE-GRANULARITY`); `component_composition_distractors[]` are traps.
4. **Including distractor freight quotes.** Drop any with `destination` containing "Distractor", `FR-DIS-` ids, or wrong shipment dims. But **keep** real-route stale/expired quotes, flagged.
5. **Treating a stale real-route freight as valid.** Flag it (`source_is_stale=true`, `validity_status=STALE`, `road_quote_invalid_or_stale=true`) — don't silently treat it as a clean option.
6. **Setting `due_date` on a paid milestone.** Paid ⇒ `due_date = null`. Only unpaid/partial carry the invoice due date.
7. **Filtering revenue-journals by `customer_id`.** They have no such field — use `opportunity_id`.
8. **Wrong revenue-recognition enum.** Use each template's declared labels (`REQUIRED_MISSING` vs `MISSING_REVENUE_JOURNAL`). Paid+no-journal = the "missing" state; unpaid = `NOT_REQUIRED_UNPAID`; paid+posted = `RECOGNIZED`.
9. **Missing the missing-journal accounting action.** A paid milestone without a posted revenue journal requires `RECORD_REVENUE_<MS>` (Dr Deferred Revenue / Cr Implementation Services Revenue), routed to ACCOUNTING — not "verify".
10. **Over-collection.** An unpaid milestone not yet due (as of `as_of_date`) → `MONITOR_UNPAID_NOT_DUE` (ACCOUNT_MANAGEMENT), not `SEND_COLLECTION_NOTICE` (COLLECTIONS). Use due-date vs as_of_date.
11. **Wrong invite owner.** Briefing invitations route to **EVENTS**, not ACCOUNT_MANAGEMENT (even though the event `follow_up_owner` may read "Account Management" — that is the relationship owner, not the invite-sending queue).
12. **Mis-mapping payment terms.** New NGO ⇒ `PREPAY_100`; recurring NGO/commercial ⇒ `NET_30_AFTER_PO`. Check `is_recurring`/`payment_profile`/`client_since`.
13. **Defaulting recommended mode to AIR.** Use the lowest-cost low-risk valid option; AIR only when it's the sole qualifying option (e.g. cold-chain with no low-risk sea/road) or an explicit emergency deadline demands it.
14. **Confusing quote-date validity with freight-validity.** Catalog pricing valid 30 days from quote date; freight `valid_until` may expire sooner — surface freight staleness separately.
15. **Ignoring the WHO doc flag.** WHO-standard kit families (IEHK-*) need `who_documentation_required=true`.
16. **Using raw phase_id where the template wants `MS1|MS2|MS3`.** Match the template's milestone_id convention exactly (003: free string phase_id; 005: enum MS1/MS2/MS3 ascending).

---

## 5. Execution checklist (apply to every task)

1. Read the prompt; identify family (QUOTE vs RECONCILIATION) and the exact ids (quote/rfq/opportunity/customer/product/event/voucher).
2. Read `answer_template.json` — note every field name and **controlled enum** value declared. Output must match it exactly (field names, nesting, enum strings). Return only valid JSON (no markdown, no prose).
3. Fetch canonical records (§2.1 or §3.1). Use `opportunity_id` filters for the reconciliation side collections; `quote_id` for freight; detail-by-id only for the 6 supported collections.
4. Reconcile prompt narrative vs API; trust API for facts, prompt for *which* entity.
5. Compute: catalog tier/EXW total (quote) OR phase-match/outstanding/recognised amounts (recon).
6. Apply routing rules: payment terms, recommended mode, accounting action, collection action, invite action, owner queues.
7. Apply exclusions/flags: distractor freight, stale freight, paid→null due_date, missing-journal flag.
8. Emit JSON matching the template; money 2 dp; ISO dates; stable ids; enums exactly as declared.
