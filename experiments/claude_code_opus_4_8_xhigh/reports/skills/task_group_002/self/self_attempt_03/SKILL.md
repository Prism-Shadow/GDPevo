# SKILL: MedBridge Sales Ops — B2B Quote & Engagement Reconciliation

## What this is / when it applies
You get ONE task: a free-text prompt naming a customer plus a record id (a quote
`Q-...`, an RFQ `RFQ-...`, or an opportunity `OPP-...`), and an
`answer_template.json`. You must read live facts from the **MedBridge Sales Ops API**
and return ONLY a JSON object that fills the template exactly. No markdown, no prose,
no fields added or removed. Three task families exist (see below).

The current business / quote date is given in the prompt (train set uses
`2026-06-01`; CRM tasks may say "treat YYYY-MM-DD as the current business date").
Always use the date the prompt states as "today" for due/overdue/validity logic.

## The remote API
- Base URL: `<remote-env-url>` (or the env var the runner provides:
  `API_BASE_URL` / `BASE_URL` / `http://127.0.0.1:${PORT}`). Read-only JSON over HTTP;
  use `curl -s` or python urllib. There are NO local data files.
- Collections: customers, products, rfqs, quotes, freight-quotes, policies,
  opportunities, invoices, payments, revenue-journals, events, vouchers.
- Fetch one: `GET /api/<collection>/<id>` (e.g. `/api/quotes/Q-...`,
  `/api/customers/CUST-...`, `/api/opportunities/OPP-...`,
  `/api/products/<code>`).
- List + filter: `GET /api/<collection>?field=value` (server flattens nested keys,
  matches case-insensitively, numbers match 2-decimal form). Most useful:
  `GET /api/freight-quotes?quote_id=Q-...`, `GET /api/invoices?customer_id=CUST-...`,
  `GET /api/payments?customer_id=CUST-...`.
- **Full-text search is the safest "gather everything" call:**
  `GET /api/search?q=<text>` returns every record across all collections whose text
  matches. For a CRM reconciliation, search the opportunity id or customer id and you
  get the customer, opportunity, all invoices, payments, revenue-journals, event, and
  voucher in one response. Use this to avoid missing linked records.

### ID-resolution from the prompt
- The prompt usually states the key id explicitly (quote/RFQ/opportunity). If only a
  company name is given, `GET /api/search?q=<name>` and pick the matching record.
- The customer id comes from the quote/rfq/opportunity record's `customer_id`, not
  from the friendly company name in the prompt (the prompt's name may be a paraphrase;
  trust the record's `customer_id` and the customer record's `name`).
- ID prefixes in the dataset: `*-TR-*` = train, `*-TE-*` = test, `*-DIS-*` =
  distractor/decoy. Only use the records the prompt's id points to. Ignore unrelated
  ids. For freight, distractor freight records are explicitly marked (see below).

## Money & formatting conventions (all families)
- All money is USD, rounded to **2 decimals**. Output as a JSON number (e.g. `42480.0`
  / `42480.00`), never a string, never with `$`.
- Dates are ISO `YYYY-MM-DD`. Copy them verbatim from the records.
- Quantities, lead times, shelf life, max_uses, phase numbers are integers.
- `transit_days` is the freight record's `transit_days_text` (a string like
  `"4-6 days"`), NOT a number — match the template field's type.
- Enum/status fields must use the EXACT controlled values listed in the template, not
  the raw API strings. Map raw API values to the template enum (see mappings below).
- A field is `null` only when the template explicitly allows null and the fact does not
  apply (e.g. a collection task's `milestone_id`/`amount_due` when there is no unpaid
  milestone; a `due_date` that the record genuinely lacks).
- Reconcile totals: line/milestone totals must sum to the stated grand/won total when
  the template asks for a match boolean.

---

## FAMILY A — Quote + freight decision package
Trigger: prompt gives a quote id `Q-...` with a confirmed quantity, a destination
exists, and asks for EXW pricing PLUS air/sea/road freight options, totals, risk, a
recommended mode, validity/reconfirmation, and payment terms.
(Train 001 `Q-TR-WC-1187`; Train 004 `Q-TR-LD-5521`. Note the two families A use
slightly different templates — fill whatever fields the given template has.)

### SOP
1. `GET /api/quotes/<quote_id>` → read `customer_id`, `quote_date`,
   `primary_product_code`, `confirmed_quantity` (the confirmed/revised qty, NOT the
   `prior_quote_quantity`).
2. `GET /api/products/<product_code>` → pick the **price tier** whose
   `[min_qty, max_qty]` brackets `confirmed_quantity` (`max_qty: null` means open-ended
   top tier). From that tier take `unit_price_usd`, `lead_time_days`,
   `lead_time_weeks` if needed; take `shelf_life_months` from the product root.
   IGNORE `prior_unit_price_usd` on the quote — the catalog tier overrides prior price.
3. `exw_total_usd = unit_price_usd * confirmed_quantity` (2 decimals).
4. `GET /api/freight-quotes?quote_id=<quote_id>`. You will get the 3 real options plus
   decoys. **Keep exactly one option per mode (air, sea, road)** — the canonical record
   whose `destination` matches the shipment route and `id` follows `FR-<prod>-<MODE>`.
   **EXCLUDE** any record whose `destination` is `"Distractor route"`, whose `id`
   contains `DIS`, or whose shipment size (`shipment_cbm`/`shipment_weight_kg`) differs
   from the real options. There are usually 4-5 records; the 3 keepers share the same
   `shipment_cbm`/`shipment_weight_kg`.
5. For each kept option:
   - `freight_cost_usd` = `cost_usd`.
   - `transit_days` = `transit_days_text`.
   - `valid_until` = record `valid_until`.
   - `grand_total_usd = exw_total_usd + freight_cost_usd`.
   - **Validity / staleness vs the quote date:** a freight option is stale/invalid if
     its `status == "stale"` OR its `valid_until` < quote date. Mark accordingly:
     - Template-001 style: `risk_level` from `route_risk` (low→LOW, medium→MEDIUM,
       high→HIGH); `risk_flag` = `NONE` for low risk, and for medium/high derive from
       `risk_notes` (e.g. border/customs risk → `MEDIUM_BORDER_RISK`,
       high customs → `HIGH_CUSTOMS_RISK`). When the template pre-fills a flag string
       for a mode, match its convention.
     - Template-004 style: `validity_status` = `"valid"` if active and not expired,
       else `"expired"`/`"stale"`; `source_is_stale` = true iff `status=="stale"` or
       expired before quote date; `customs_border_risk` mirrors `route_risk`
       (low/medium/high, matching the casing the template implies).
6. `recommended_mode`: choose the **lowest grand-total option among those that are
   VALID on the quote date and not stale** (and that meet hard requirements such as
   cold-chain support if `cold_chain_required`). If the cheapest mode is stale/expired
   (e.g. ROAD in Train 004), it is disqualified and you recommend the cheapest of the
   remaining valid modes. In the train data SEA is typically the cheapest valid option
   and becomes the recommendation. Keep feasibility (cold-chain, shelf-life vs transit)
   separate from route-risk: a higher-risk-but-valid mode can still be quoted; only
   stale/expired/over-shelf-life options are disqualified from recommendation.
7. Policy flags:
   - `freight_reconfirmation_required` = `true` (policy POL-FREIGHT-RECONFIRM:
     freight rates always reconfirmed at order).
   - `all_freight_options_valid_on_quote_date` = `true` only if every KEPT option's
     `valid_until` >= quote date and none are `stale`; else `false`.
   - For the 004-style warning block: `road_quote_invalid_or_stale` = true iff the
     kept ROAD option is stale/expired; `freight_warning` = a short string describing
     it (e.g. that the road quote is stale/expired and must be re-sourced).
   - `customer_policy` / `policy_terms.quote_basis` = `EXW` (these are EXW + freight
     quotes; incoterm is "EXW plus freight options").
   - `payment_terms` — see PAYMENT TERMS rules below.
   - `recommended_mode` per step 6.

---

## FAMILY B — Module / RFQ, EXW-only (no freight)
Trigger: prompt gives an RFQ id `RFQ-...`, an indicative module quote, **no
destination** ("destination pending"), instruction to quote EXW only / exclude freight
and to keep module-level lines only. (Train 002 `RFQ-TR-IEHK-204`.)

### SOP
1. `GET /api/rfqs/<rfq_id>` → `customer_id`, `quote_date`, `currency`,
   `requested_modules` (each has `product_code` + `quantity`).
2. **One line item per requested module — do NOT expand into components.** The RFQ may
   list `component_composition_distractors` / a composition table; that is for medical
   review only. Policy POL-MODULE-GRANULARITY: quote at module line level unless the
   customer explicitly asks for component pricing.
3. For each module `GET /api/products/<code>`: take `article_number`, the matching
   price tier (modules typically have a single tier; pick the tier bracketing the
   quantity, usually `min_qty 1, max_qty null`), `unit_price`, `lead_time_days`,
   `shelf_life_months`. `line_total = unit_price * quantity`.
4. `grand_total` = sum of all `line_total`s (2 decimals).
5. Controls:
   - `quote_basis` = `EXW_ONLY`; `freight_excluded` = `true`
     (policy POL-INDICATIVE-EXW: no destination → EXW only, freight excluded).
   - `payment_terms` = `PREPAY_100` for a NEW NGO account (see payment rules).
   - `offer_validity_days` = `30` (policy POL-QUOTE-VALIDITY: catalog pricing valid 30
     calendar days from quote date).
   - `who_documentation_required` = `true` for IEHK/emergency-health-kit / WHO-style
     modules (the requested family is `emergency_health_kit`).

---

## FAMILY C — CRM milestone / engagement reconciliation
Trigger: prompt gives an opportunity id `OPP-...` + customer id, asks to reconcile
milestone invoices, payments, revenue recognition, and a linked event/voucher, and to
route follow-up tasks. (Train 003 `OPP-TR-HELIOS`; Train 005 `OPP-TR-MERIDIAN`.)
Two template variants exist (003 simpler; 005 richer with debit/credit accounts) — fill
whatever the given template declares.

### SOP
1. Gather everything: `GET /api/search?q=<OPP id>` (and/or `?q=<CUST id>`). This returns
   the customer, opportunity, all invoices, payments, revenue-journals, the event and
   the voucher. Cross-check with `GET /api/opportunities/<id>`.
   IMPORTANT: `revenue-journals` does NOT support a `customer_id` filter (returns 0).
   Get them from the search results or `GET /api/revenue-journals?opportunity_id=<id>`
   or fetch all and match by `opportunity_id`/`phase_id`/`invoice_id`.
2. Opportunity facts: `customer_name` from the customer record's `name`;
   `stage`: `closed_won`→`WON`, `proposal`/`negotiation`/open→`OPEN`, lost→`LOST`;
   `won_amount` = `won_amount_usd`.
3. Phase total: sum each phase's `amount_usd`. `opportunity_matches_milestones` /
   `opportunity_matches_phase_total` = (phase sum == won_amount).
4. `outstanding_balance` = sum of unpaid invoice `outstanding_amount_usd` (equals the
   opportunity `outstanding_amount_usd`). `total_paid_amount` = sum of paid amounts.
5. Build a milestone per phase (order ascending by milestone/phase id). Map the phase to
   its invoice (by `phase_id`/`invoice_id`) and payments/journal:
   - `milestone_id`: use the stable phase id (e.g. `HEL-P1`) OR the template's required
     enum (Train 005 template requires `MS1|MS2|MS3` mapped in phase order P1→MS1,
     P2→MS2, P3→MS3). Use exactly what the template's enum says.
   - `phase_number` (003): integer phase order (1, 2, ...).
   - `invoice_total` / `amount` = invoice `amount_usd` (= phase amount).
   - `invoice_state` (005 enum PAID|OPEN|VOID|UNKNOWN): invoice `status` `paid`→PAID;
     `unpaid`/`overdue`/`draft`→OPEN; void→VOID; missing→UNKNOWN.
   - `payment_status`/`payment_state` (PAID|PARTIAL|UNPAID): compare paid vs amount —
     `paid_amount_usd >= amount`→PAID; `0 < paid < amount`→PARTIAL; `0`→UNPAID.
   - `amount_paid`/`paid_amount` = invoice `paid_amount_usd`;
     `amount_unpaid` = invoice `outstanding_amount_usd`.
   - `due_date` = invoice `due_date`. (Some templates want due_date `null` for fully
     paid milestones — follow the template's stated convention; otherwise copy the
     invoice due_date.)
   - **Revenue recognition status** (policy POL-REVREC: recognize only completed+paid
     milestones from Deferred Revenue → Implementation Services Revenue):
     - PAID milestone WITH a matching posted revenue-journal → `RECOGNIZED`.
     - PAID milestone with NO matching journal → `REQUIRED_MISSING` (003) /
       `MISSING_REVENUE_JOURNAL` (005). (This is the key Meridian MS2 case.)
     - UNPAID milestone → `NOT_REQUIRED_UNPAID`. Never recognize unpaid milestones.
6. Revenue-recognition summary (003): `recognized_milestones` = the paid+journaled
   milestone ids; `missing_required_milestones` = paid-but-unjournaled ids;
   `recognized_amount` = sum of recognized journal amounts;
   `recognition_status` = `COMPLETE_FOR_PAID_MILESTONES` if no paid milestone is missing
   a journal, else `MISSING_FOR_PAID_MILESTONES`, else `NOT_REQUIRED`.
7. Accounting / collection routing (005 `invoice_actions`):
   - If a PAID milestone is missing its journal → `primary_accounting_action` /
     `accounting_action.action` = `RECORD_REVENUE_MS<n>` (the missing milestone),
     `milestone_id` that milestone, `amount` its amount,
     `debit_account` = `DEFERRED_REVENUE`,
     `credit_account` = `IMPLEMENTATION_SERVICES_REVENUE`,
     `owner_queue` = `ACCOUNTING`. If every paid milestone is already journaled →
     `VERIFY_REVENUE_ONLY` (or `NO_ACCOUNTING_ACTION` when nothing paid), amount/
     milestone/accounts `NONE`/0 per template.
   - Collection: take the earliest UNPAID milestone. If its `due_date` >= as-of date →
     `MONITOR_UNPAID_NOT_DUE`, `owner_queue` = `ACCOUNT_MANAGEMENT`. If overdue
     (`due_date` < as-of) → `SEND_COLLECTION_NOTICE`, `owner_queue` = `COLLECTIONS`.
     If nothing unpaid → `NO_COLLECTION_ACTION`, milestone `NONE`, amount 0,
     due_date null. `contact_name` = opportunity `contact`.
8. Event + voucher: read the event record (`event_id`, `event_date`, `status`,
   `primary_contact`, `voucher_code`, `follow_up_owner`) and the voucher
   (`code`, `status`, `discount_percent`, `max_redemptions`, `valid_until`).
   - `event_status` enum SCHEDULED|ACTIVE|COMPLETED|CANCELLED|UNKNOWN: raw `scheduled`→
     SCHEDULED, `confirmed`→SCHEDULED, `live`→ACTIVE, `completed`→COMPLETED,
     `tentative`→SCHEDULED, `cancelled`→CANCELLED.
   - `voucher_status` enum ACTIVE|DRAFT|EXPIRED|DISABLED|UNKNOWN: raw `active`→ACTIVE
     (all train vouchers are active). Treat expired `valid_until` per template intent if
     a status enum demands it, but trust the record `status` first.
   - `voucher_discount` / `discount_amount` = the voucher's `discount_percent` numeric
     value (e.g. 100 or 50 — the template field name says "amount" but the value is the
     percent number stored on the voucher). `max_uses` = `max_redemptions`.
   - Invite action: event not yet held / scheduled → `SEND_BRIEFING_INVITE` /
     `SEND_EVENT_INVITATION`; already sent/held → `VERIFY_INVITE_SENT` /
     `NO_INVITE_ACTION`. `owner_queue` = `ACCOUNT_MANAGEMENT` (events' `follow_up_owner`
     is "Account Management"). `contact_name` = event `primary_contact`.
9. Follow-up tasks (003 `follow_up_tasks` array): emit a `COLLECTION` task for the
   unpaid milestone (`next_action` = `COLLECT_UNPAID_MILESTONE`, `milestone_id` and
   `amount_due` set, `event_id`/`voucher_code` null, `due_date` = that invoice's
   due_date) AND an `EVENT_INVITATION` task (`next_action` = `SEND_EVENT_INVITATION`,
   `event_id`/`voucher_code` set, `milestone_id`/`amount_due` null,
   `due_date` = event_date). `linked_customer_id`/`linked_opportunity_id`/`contact_name`
   come from the records (contact from opportunity `contact`).

---

## PAYMENT TERMS rules (Families A & B)
Derived from the customer record + policies:
- **New NGO** (`is_recurring: false`, `segment: new_ngo`/`status: prospect`,
  `payment_profile: NEW_CLIENT_REVIEW`) → `PREPAY_100`
  (POL-NEW-CLIENT-PAYMENT: new NGOs prepay 100% before production).
- **Recurring NGO** (`customer_type: NGO`, `is_recurring: true`,
  `payment_profile: NET_30_AFTER_PO`) → `NET_30_AFTER_PO`
  (POL-RECURRING-NGO-PAYMENT) — unless grant terms restrict it.
- **Recurring Commercial** (e.g. CUST-GHL, `payment_profile: NET_30_AFTER_PO`) →
  `NET_30_AFTER_PO`.
- When in doubt, prefer the customer's own `payment_profile` field; the policies above
  explain/confirm it. Output the controlled terms code, not prose.

## Common misjudgments / exclusion rules
- Use the **confirmed/revised** quantity, not `prior_quote_quantity`; use the **catalog
  tier** price, not `prior_unit_price_usd`.
- Pick the correct price tier by quantity bracket; `max_qty: null` is the open top tier.
- Freight: keep exactly one record per mode; drop `"Distractor route"` /`DIS`/
  wrong-shipment-size / stale decoys. Don't sum freight into EXW total — EXW excludes
  freight; only `grand_total` adds freight.
- A stale/expired freight mode is still listed (with its real cost) but is flagged stale
  and is NOT eligible to be the `recommended_mode`.
- Family B: never expand modules into components; never add freight (no destination).
- CRM: recognize revenue ONLY for milestones that are BOTH complete and paid AND have a
  posted journal; a paid milestone without a journal is the "missing" action, not
  "recognized". Never recognize unpaid milestones.
- CRM collection: distinguish not-yet-due (monitor / Account Management) from overdue
  (send notice / Collections) using the as-of date vs invoice `due_date`.
- `revenue-journals` ignores `customer_id` filtering — use search or `opportunity_id`.
- Map every raw status string to the template's controlled enum; never output a raw
  value the template's enum doesn't list.

## Final reminder
Return ONLY the JSON object matching the provided `answer_template.json` — same keys,
same structure, correct types, controlled enum values, money at 2 decimals, ISO dates.
No markdown, no commentary, no extra or missing fields.
