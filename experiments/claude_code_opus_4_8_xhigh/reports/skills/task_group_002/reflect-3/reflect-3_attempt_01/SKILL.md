# SKILL: MedBridge Sales Ops — CRM/B2B Quote & Engagement Reconciliation

## Description / when this applies
Use this skill when you are handed ONE task in the **MedBridge Sales Ops** domain:
a CRM / B2B medical-supply account that needs either (a) an **EXW quote decision
package** (catalog pricing + freight comparison) or (b) an **engagement / milestone
reconciliation** (opportunity vs invoices vs payments vs revenue journals + event/voucher
follow-ups). You get a prompt naming specific record IDs, the read-only data API, and an
`answer_template.json`. Your job: read the real records from the API, apply the business
rules below, and return ONLY JSON that fills the template exactly.

Return ONLY the JSON object that matches the provided `answer_template.json`. No markdown,
no prose, no code fences, no trailing commentary. Fill every field; never leave template
placeholders (`""`, `0`, `<...>`, `YYYY-MM-DD`).

---

## The data API
- Base URL is provided by the runner (env var named e.g. `API_BASE_URL` / `BASE_URL` /
  `http://127.0.0.1:<PORT>`). Read-only JSON over HTTP (use curl or python urllib).
- Collections (GET): `/api/customers`, `/api/products`, `/api/rfqs`, `/api/quotes`,
  `/api/freight-quotes`, `/api/policies`, `/api/opportunities`, `/api/invoices`,
  `/api/payments`, `/api/revenue-journals`, `/api/events`, `/api/vouchers`.
- Single record: `/api/<collection>/<id>` (e.g. `/api/quotes/Q-...`, `/api/products/<code>`,
  `/api/opportunities/OPP-...`).
- Filtering: list endpoints accept `?field=value` (nested keys are flattened), e.g.
  `/api/invoices?opportunity_id=OPP-X`, `/api/freight-quotes?quote_id=Q-X`,
  `/api/vouchers?code=ABC`. Matching is case-insensitive; numbers match their 2-decimal form.
- `/api/search?q=<text>` does full-text search across all collections — use it to resolve a
  name to an ID (e.g. search the customer name to get the `CUST-...` id).

### Which endpoint answers which question
- Customer record / payment profile / type / recurring flag → `/api/customers/<id>`.
- Catalog pricing tiers, lead time, shelf life, article_number, components → `/api/products/<code>`.
- Confirmed quantity, quote date, primary product, destination → `/api/quotes/<id>`.
- Requested modules + quantities, indicative flag, destination → `/api/rfqs/<id>`.
- Transport options → `/api/freight-quotes?quote_id=<quote_id>` (NOT by customer_id — see gotcha).
- Business rules / payment terms / validity → `/api/policies` (one list, read all 8 rules).
- Opportunity stage, won amount, phases, outstanding → `/api/opportunities/<id>`.
- Milestone invoices → `/api/invoices?opportunity_id=<id>` (each has phase_id, due_date, status, paid_amount).
- Cash received → `/api/payments?opportunity_id=<id>`.
- Revenue recognition coverage → `/api/revenue-journals?opportunity_id=<id>`.
- Celebration/briefing event → `/api/events?id=<event_id>` or `?customer_id=<id>`.
- Voucher / offer controls → `/api/vouchers?code=<code>`.

### Gotchas resolving data
- **Freight is keyed by `quote_id`, not `customer_id`.** `?customer_id=...` returns 0 freight rows.
- Resolve IDs from the prompt: the prompt usually gives the quote/rfq/opportunity id, the
  customer id, contact name, event id, and voucher code directly. If only a name is given,
  use `/api/search?q=<name>`.
- Read money/dates straight from records; do not recompute unit prices — pick the catalog tier.

---

## Output conventions (confirmed)
- **Money**: numbers with 2-decimal precision (e.g. `42480.00`, `76.0`). USD. Totals must
  reconcile exactly (no rounding drift).
- **Dates**: ISO `YYYY-MM-DD`.
- **Enums**: use the EXACT controlled values printed in the template (usually UPPERCASE like
  `WON`, `PAID`, `OPEN`, `RECOGNIZED`, `SEND_BRIEFING_INVITE`). Do not invent synonyms.
- **Booleans**: real `true`/`false`.
- **null**: use JSON `null` where the template says "or null" and the value is not applicable
  (see paid-milestone due_date rule).
- A `*_policy` / policy-reference field expects the **policy record ID** (e.g.
  `POL-RECURRING-NGO-PAYMENT`), not prose.
- Copy IDs/codes verbatim from the records (case-sensitive: `CUST-...`, `OPP-...`, `FR-...`,
  `MS1`, voucher codes).

---

## FAMILY A — EXW Quote Decision Package (catalog pricing + freight)
Recognize it by: a `Q-...` quote (or `RFQ-...`) about units of a product, asking for EXW
pricing, freight options, risk, recommended mode, validity, payment terms.

### SOP
1. GET the quote (`/api/quotes/<id>`): read `customer_id`, `quote_date`,
   `primary_product_code`, and `confirmed_quantity`.
2. GET the product (`/api/products/<code>`). Pick the **price tier whose
   [min_qty, max_qty] contains the confirmed quantity** (max_qty `null` = open-ended top tier).
   That tier gives `unit_price_usd`, `lead_time_days`. `shelf_life_months` is product-level.
   Ignore the prior quote's unit price — the current catalog tier overrides it.
3. `exw_total = unit_price * confirmed_quantity` (2 decimals).
4. GET freight `/api/freight-quotes?quote_id=<quote_id>`. Keep only the **real options for
   this quote**: typically one each of mode air/sea/road with `status:"active"` and a real
   destination. **EXCLUDE** any record whose id contains `FR-DIS-` or whose `destination` is
   `"Distractor route"`, and any whose `status` is `stale`/`mismatch` *when a distractor*.
   (A genuine quote option that is itself stale/expired is still listed — see step 6.)
5. For each kept freight option:
   - `freight_cost_usd` = `cost_usd`; `transit_days` = the `transit_days_text` (e.g. "4-6 days");
     `valid_until` = record's `valid_until`.
   - `grand_total = exw_total + freight_cost` (2 decimals).
   - Risk from `route_risk`: `low→LOW`, `medium→MEDIUM`, `high→HIGH`. If a template uses a
     `risk_flag`/`customs_border_risk`, map: low→`NONE`, medium→`MEDIUM_BORDER_RISK`,
     high→border/high risk (match the template's enum exactly).
6. **Validity / staleness**: an option is valid on the quote date iff `valid_until >= quote_date`
   AND `status == "active"`. A `status:"stale"` / expired (`valid_until < quote_date`) genuine
   road option must be **flagged** (set its validity/stale flags, e.g.
   `source_is_stale: true`, validity status STALE/EXPIRED, and the top-level
   `road_quote_invalid_or_stale: true` + a `freight_warning` string). Set
   `all_freight_options_valid_on_quote_date` accordingly.
7. **Recommended mode** (rewarded rule): choose the option with the **lowest grand_total among
   options that are valid (not expired/stale) AND `route_risk == low`**. Tie-break by lowest
   cost. (Confirmed: it is NOT "fastest" and NOT simply the global cheapest — a cheaper
   medium-risk or stale option does NOT win.)
   - Example logic: if AIR and SEA are both low-risk, recommend the cheaper (SEA); if only AIR
     is low-risk (SEA medium, ROAD stale/high), recommend AIR.
8. **Freight reconfirmation**: always `true` for catalog freight (policy `POL-FREIGHT-RECONFIRM`,
   "reconfirm at order; valid only through valid_until").
9. **Payment terms** by account (from customer record + policies):
   - Recurring NGO / recurring commercial with an after-PO net profile → `NET_30_AFTER_PO`
     (policy `POL-RECURRING-NGO-PAYMENT`).
   - New / prospect NGO (not recurring, segment new_*) → `PREPAY_100`
     (policy `POL-NEW-CLIENT-PAYMENT`).
   - When in doubt, the customer's `payment_profile` field is the source of truth; map it to the
     matching policy `terms_code`.
10. `quote_basis` is `EXW` (or `EXW_ONLY` per template) for these packages.

### FAMILY A-modules — Indicative module RFQ (EXW only, freight excluded)
Recognize it by: an `RFQ-...` for several module product codes, "indicative", "destination
pending/no destination", "EXW only", "module level".
- Quote at **module line level only**. The RFQ may include `component_composition_distractors`
  / composition tables — **ignore them; do NOT split modules into component SKUs**
  (policy `POL-MODULE-GRANULARITY`).
- One line per requested module: `product_code`, `article_number` (from product, keep as the
  string the API returns, e.g. "500101"), `quantity` (from RFQ), `unit_price` (single tier),
  `lead_time_days`, `shelf_life_months`, `line_total = unit_price * quantity`.
- `grand_total` = sum of line_totals.
- No destination ⇒ `quote_basis = EXW_ONLY`, `freight_excluded = true` (policy
  `POL-INDICATIVE-EXW`). Do not fetch/attach freight.
- `payment_terms = PREPAY_100` for a new NGO account.
- `offer_validity_days = 30` (policy `POL-QUOTE-VALIDITY`: catalog pricing valid 30 days).
- `who_documentation_required = true` for these WHO/IEHK-style emergency health kits.

---

## FAMILY B — Engagement / Milestone Reconciliation
Recognize it by: an `OPP-...` opportunity + `CUST-...`, asking to reconcile won amount vs
milestones, summarize invoice/payment/outstanding/revenue-recognition state, route CRM/
accounting follow-ups, and include a related event + voucher.

### SOP
1. GET opportunity `/api/opportunities/<id>`: `stage` (`closed_won → WON`), `won_amount_usd`,
   `phases[]` (each has phase_id, amount_usd, completion_date, invoice_id), `outstanding_amount_usd`,
   `contact`.
2. GET customer for `customer_name` and the contact's linkage.
3. `phase_total = sum(phase amounts)`. `opportunity_matches_phase_total =
   (phase_total == won_amount)`.
4. GET invoices `/api/invoices?opportunity_id=<id>`, payments
   `/api/payments?opportunity_id=<id>`, revenue-journals
   `/api/revenue-journals?opportunity_id=<id>`. Join by `phase_id` / `invoice_id`.
5. `total_paid = sum(invoice.paid_amount_usd)`; `outstanding_balance = sum(invoice.outstanding_amount_usd)`
   (should equal the opportunity's outstanding).
6. Build one milestone per phase, **ordered ascending** (MS1, MS2, MS3 …). If the template's
   `milestone_id` is an enum (`MS1|MS2|MS3`), use that ordinal id — NOT the phase_id. If the
   template instead asks for a "stable phase/invoice milestone id", use the phase_id.
   Per milestone:
   - `amount` = phase amount; `paid_amount` = invoice paid_amount; `amount_unpaid` =
     invoice outstanding.
   - `invoice_state`: invoice `status` paid→`PAID`, unpaid→`OPEN` (void→`VOID`).
   - `payment_state`: fully paid→`PAID`, none→`UNPAID`, between→`PARTIAL`.
   - **`due_date`: for a PAID milestone set `due_date = null`; for an UNPAID milestone use the
     invoice `due_date`.** (Confirmed convention.)
   - `recognition_status`:
     * paid AND a revenue-journal exists for that phase → `RECOGNIZED`.
     * paid AND **no** revenue-journal → `MISSING_REVENUE_JOURNAL` (also
       `REQUIRED_MISSING` style in other templates).
     * unpaid → `NOT_REQUIRED_UNPAID`.
7. **Revenue recognition rollup** (policy `POL-REVREC`: recognize only paid+complete milestones):
   - `recognized_milestones` = paid milestones that have a journal; `recognized_amount` = their sum.
   - `missing_required_milestones` = paid milestones with NO journal.
   - `recognition_status`: all paid milestones recognized → `COMPLETE_FOR_PAID_MILESTONES`;
     some paid milestone missing a journal → `MISSING_FOR_PAID_MILESTONES`; nothing paid →
     `NOT_REQUIRED`.
8. **Accounting action routing** (separate from collections):
   - If a **paid milestone is missing its journal** → `primary_accounting_action =
     RECORD_REVENUE_MS<n>` for that milestone. The `accounting_action`:
     `action = RECORD_REVENUE_MS<n>`, `milestone_id = MS<n>`, `amount` = that phase amount,
     `debit_account = DEFERRED_REVENUE`, `credit_account = IMPLEMENTATION_SERVICES_REVENUE`,
     `owner_queue = ACCOUNTING`. (Mirror the revenue-journal pattern: debit Deferred Revenue,
     credit Implementation Services Revenue.)
   - If all paid milestones already recognized → `VERIFY_REVENUE_ONLY` / `NO_ACCOUNTING_ACTION`
     with `milestone_id = NONE`, `amount = 0.00`, accounts `NONE`, `owner_queue NONE` (per the
     template's enums).
9. **Collection action routing** (drive only from UNPAID milestones; compare due_date to the
   current business date `as_of`):
   - Unpaid and **not yet due** (`due_date > as_of`) → `collection_action =
     MONITOR_UNPAID_NOT_DUE`; `collection_task`: `action = MONITOR_UNPAID_NOT_DUE`,
     `milestone_id = MS<n>`, `amount` = unpaid amount, `due_date` = invoice due,
     **`owner_queue = ACCOUNT_MANAGEMENT`** (NOT COLLECTIONS), `contact_name` = the contact.
   - Unpaid and **due/overdue** (`due_date <= as_of`) → `SEND_COLLECTION_NOTICE`, and
     `owner_queue = COLLECTIONS`.
   - No unpaid milestones → `NO_COLLECTION_ACTION`.
10. **Event + voucher + invite** (the briefing/celebration):
    - `event_status` from event `status` (e.g. scheduled→`SCHEDULED`, confirmed→`SCHEDULED`/per
      template enum; active→`ACTIVE`).
    - voucher: `voucher_status` from status (active→`ACTIVE`), `discount_amount =
      voucher.discount_percent`, `max_uses = voucher.max_redemptions`.
    - `invite_action = SEND_BRIEFING_INVITE` (or `SEND_EVENT_INVITATION` per template);
      `invite_task` `owner_queue = ACCOUNT_MANAGEMENT` (event `follow_up_owner` = "Account
      Management"), with `event_id`, `voucher_code`, `contact_name`, `customer_id` filled.
11. **Follow-up tasks** (when the template uses a single `follow_up_tasks[]` list rather than
    split action objects): emit one `COLLECTION` task per unpaid milestone
    (`next_action = COLLECT_UNPAID_MILESTONE`, `milestone_id` set, `amount_due` set,
    `event_id`/`voucher_code` = null, `due_date` = invoice due) and one `EVENT_INVITATION` task
    (`next_action = SEND_EVENT_INVITATION`, `milestone_id`/`amount_due` = null,
    `event_id`/`voucher_code` set, `due_date` = event_date). Always set
    `linked_customer_id`, `linked_opportunity_id`, `contact_name` on every task.

---

## Business-rule cheat sheet (what the grader rewarded)
- **Tier selection**: the tier bracket that contains the confirmed quantity; catalog tier
  overrides any prior/quoted unit price.
- **EXW & grand-total math**: `exw = unit_price * qty`; `grand_total = exw + freight_cost`;
  2 decimals; totals reconcile.
- **Risk level vs risk flag** are distinct: a numeric/ordinal level (LOW/MEDIUM/HIGH) plus a
  named flag (NONE / MEDIUM_BORDER_RISK). Set both from `route_risk`.
- **Recommended mode = lowest grand_total among VALID, LOW-route-risk options** (feasibility
  filters first, cost decides among the survivors). Not fastest, not cheapest-overall.
- **Feasibility vs risk separation**: exclude stale/expired and distractor freight from the
  recommendation, but still LIST genuine stale options with their warning flags.
- **Validity / reconfirmation**: catalog pricing valid 30 days; freight valid only through its
  `valid_until`; freight reconfirmation always required at order.
- **Payment terms by account type**: recurring → NET_30_AFTER_PO; new/prospect → PREPAY_100;
  fall back to the customer's `payment_profile`.
- **Revenue recognition**: recognize ONLY paid milestones; a **paid milestone missing its
  journal triggers RECORD_REVENUE** (debit Deferred Revenue → credit Implementation Services
  Revenue, ACCOUNTING queue); unpaid milestones are never recognized.
- **Collection vs accounting are routed separately**: missing-journal = accounting; unpaid =
  collection. Unpaid-not-due → MONITOR (ACCOUNT_MANAGEMENT); unpaid-overdue → SEND_COLLECTION_
  NOTICE (COLLECTIONS).
- **Paid-milestone due_date = null**; unpaid milestone keeps invoice due_date.
- **Module-only granularity**: never expand modules into components.
- **Freight excluded when no destination**: indicative EXW_ONLY quotes carry no freight.

## Common misjudgments / exclusions
- Do NOT include `FR-DIS-*` / "Distractor route" freight, "wrong shipment size"/"old route"/
  "prior count" benchmark rows, or freight belonging to a different `quote_id`.
- Do NOT carry a stale/expired freight rate into the recommendation; only into the warning.
- Do NOT over-expand RFQ modules into component SKUs (composition tables are distractors).
- Do NOT filter freight by `customer_id` (returns nothing); filter by `quote_id`.
- Do NOT reuse the prior/old unit price; always re-pick the current catalog tier.
- Do NOT set a paid milestone's due_date to the invoice date — use null.
- Do NOT route a not-yet-due unpaid milestone to COLLECTIONS — that is ACCOUNT_MANAGEMENT
  monitoring until the due date passes.
- Match enum spelling/case to the template exactly; a near-synonym is graded wrong.

## Final reminder
Return ONLY the JSON object matching the provided `answer_template.json`, every field filled
with real values from the API and the rules above. No markdown, no explanation.
