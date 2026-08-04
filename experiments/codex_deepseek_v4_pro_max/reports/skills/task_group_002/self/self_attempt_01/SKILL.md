## MedBridge Sales Ops API Integration Skill

### Overview
This skill defines the operating procedure for interacting with the MedBridge Sales Ops API to produce quote decision packages, account reconciliations, and finance-ready engagement summaries. All work follows a read-only GET-only API model returning structured JSON responses built from provided answer templates.

### Rules

#### 1. API Initialization
- Read the task environment base URL from the runner-provided variable (typically `<TASK_ENV_BASE_URL>` or equivalent mechanism).
- All endpoints are GET-only; POST, PUT, PATCH, and DELETE are not available.
- Start by calling `GET /api` to retrieve the live endpoint listing, then use `GET /api/search` to discover cross-entity linkages when relationships are not obvious from single-resource responses.

#### 2. Up-front Discovery
- Before assembling any answer, retrieve the full record for every entity mentioned in the prompt (customer, quote, RFQ, opportunity, product, freight, policy, invoice, payment, revenue journal, event, voucher).
- Do not assume related records exist; verify every ID and cross-reference field values from the source data.
- If an entity returns a 404, treat it as absent and build the response fields accordingly (e.g. null or omitted).

#### 3. Quotes and RFQs
- A quote is identified by `quote_id`; an RFQ is identified by `rfq_id`. Use `GET /api/quotes/{id}` or `GET /api/rfqs/{id}`.
- The customer record (`GET /api/customers/{id}`) drives payment terms and account-level policies.
- The product catalog (`GET /api/products/{code}`) supplies unit pricing via tiered quantity ranges, lead time, and shelf life. **Always select the catalog tier whose `min_quantity` ≤ confirmed_quantity ≤ `max_quantity`; if a quantity falls into multiple tiers, use the first matching tier returned by the API.**
- The quote basis is EXW (Ex Works) unless the prompt explicitly instructs otherwise.
- Compute EXW total as `confirmed_quantity × unit_price_usd` using the resolved catalog tier price.

#### 4. NGO / IEHK Module Quotes (Specialization)
- When the prompt requests a module-level IEHK quotation, quote **only the module product code** even if the API product response includes a `components` array with sub-items. Do not expand or quote component parts.
- When the RFQ supplies no destination for a transport estimate, set the quote basis to `EXW_ONLY` and mark freight as excluded.
- Payment terms for new NGO accounts default to `PREPAY_100`.
- Include `who_documentation_required: true` in the controls block for NGO medical-module quotes.
- Offer validity in days is derived from the product's shelf life (use the policy record or product field as the authority).

#### 5. Freight Analysis
- Fetch freight records from `GET /api/freight-quotes` or `GET /api/freight-quotes/{id}`.
- Compare all available modes (typically AIR, SEA, ROAD). Do not invent modes not present in the API response.
- For each freight option, evaluate:
  - **Validity**: compare `valid_until` against the quote date. A freight record is stale/invalid if the quote date falls after `valid_until`.
  - **Risk**: read `risk_level` and `risk_flag` fields. Elevated risk flags (e.g. `MEDIUM_BORDER_RISK`, `HIGH_BORDER_RISK`) should propagate to warnings.
  - **Grand total**: `exw_total + freight_cost_usd` for the option.
- The recommended mode is the **lowest-risk mode with valid freight on the quote date**. If multiple valid modes share the same risk level, prefer the lowest-cost valid option.
- Freight reconfirmation is required when: (a) a policy explicitly sets `freight_reconfirmation_required: true`, or (b) any freight record is stale/invalid on the quote date.

#### 6. Policy Lookup
- Retrieve policies via `GET /api/policies` or `GET /api/policies/{id}`. A policy is typically keyed by customer, product category, or quote type.
- Policy fields that override defaults include: payment terms, quote basis, freight reconfirmation requirement, offer validity window, and documentation requirements.
- When a policy conflicts with a product-level default, the policy takes precedence.

#### 7. Account Reconciliation (Opportunity + Milestones + Payments + Revenue)
- Retrieve the opportunity with `GET /api/opportunities/{id}`. Record its `stage`, `won_amount`, and customer linkage.
- Retrieve all milestone/invoice records for the opportunity via `GET /api/invoices` (filter by opportunity_id if supported; otherwise iterate the collection list endpoint).
- Retrieve all payments via `GET /api/payments` and match them to invoices by `invoice_id` or equivalent linkage field.
- Retrieve revenue recognition journals via `GET /api/revenue-journals` and match them to milestones.

#### 8. Revenue Recognition Rules
- For each milestone, determine recognition status:
  - **RECOGNIZED**: a revenue journal entry exists for this paid milestone.
  - **MISSING_REVENUE_JOURNAL** / **REQUIRED_MISSING**: the milestone is fully or partially paid but no revenue journal entry exists.
  - **NOT_REQUIRED_UNPAID**: the milestone has zero payments applied.
  - **UNKNOWN**: insufficient data to determine status.
- Aggregate recognition status across all milestones:
  - **COMPLETE_FOR_PAID_MILESTONES**: every paid milestone has a matching revenue journal.
  - **MISSING_FOR_PAID_MILESTONES**: at least one paid milestone lacks a revenue journal.
  - **NOT_REQUIRED**: no milestones are paid.

#### 9. Accounting Actions
- When a paid milestone lacks a revenue journal, generate a `RECORD_REVENUE_MS{n}` action naming the specific milestone, with debit to `DEFERRED_REVENUE` and credit to `IMPLEMENTATION_SERVICES_REVENUE`. Queue it to `ACCOUNTING`.
- When all paid milestones have journals, the action is `VERIFY_REVENUE_ONLY` (queue to `ACCOUNTING`).
- When no milestones are paid, use `NO_ACCOUNTING_ACTION`.

#### 10. Collection Actions
- **SEND_COLLECTION_NOTICE**: an invoice has `amount_unpaid > 0` and its `due_date` is on or before the current business date.
- **MONITOR_UNPAID_NOT_DUE**: an invoice has `amount_unpaid > 0` but its `due_date` is in the future.
- **NO_COLLECTION_ACTION**: all invoices are fully paid.
- Collection tasks are queued to `ACCOUNT_MANAGEMENT` or `COLLECTIONS` and must include the primary contact name from the prompt.

#### 11. Events and Vouchers
- Retrieve event records via `GET /api/events/{id}`. Determine whether the event is `SCHEDULED`, `ACTIVE`, `COMPLETED`, or `CANCELLED`.
- Retrieve voucher records via `GET /api/vouchers/{code}`. Determine whether the voucher is `ACTIVE`, `DRAFT`, `EXPIRED`, or `DISABLED`.
- An invite should be sent (`SEND_BRIEFING_INVITE`, `SEND_EVENT_INVITATION`) only when the event is `SCHEDULED` or `ACTIVE` and the linked voucher is `ACTIVE`. Otherwise use `VERIFY_INVITE_SENT` or `NO_INVITE_ACTION`.
- Invite tasks are queued to `ACCOUNT_MANAGEMENT` or `EVENTS` with the contact name and customer ID.

#### 12. Contact Matching
- The prompt will provide a contact name. Verify the contact is linked to the customer and/or opportunity via the API contact/people endpoints or embedded contact arrays. Propagate this name into all follow-up tasks.
- If the contact is not found in API records, still use the name from the prompt as the designated point of contact.

#### 13. Money and Date Conventions
- All monetary values use USD with exactly two decimal places.
- All dates use ISO 8601 format (`YYYY-MM-DD`).
- All record IDs are string types; do not convert numeric-looking IDs to integers.
- Enum values must use exactly the casing and spelling defined in the answer template.

#### 14. Output Format
- Return only valid JSON. Do not wrap in markdown code fences, do not include explanatory text, do not add trailing commas.
- Match the structure of the answer template exactly: every key present in the template must appear in the output. Do not add extra keys.
- If a value cannot be determined, use the type-appropriate zero/null/empty value defined in the template (e.g. `0.0` for numbers, `""` for strings, `false` for booleans, `[]` for arrays).

#### 15. Error Handling
- If the API base URL is unreachable, report the failure with a single JSON object `{ "error": "API_UNREACHABLE", "detail": "<url>" }`.
- If a required entity (customer, quote, opportunity) returns 404, return minimal JSON with `null`/`""`/`0.0` for every field and include a top-level `"integrity_warning"` key set to `"ENTITY_NOT_FOUND"`.
- If a non-critical entity (freight, policy, event) is unavailable, omit its data from the response rather than failing the whole task.

#### 16. Workflow Summary
1. Parse the prompt: identify entity IDs (quote, RFQ, opportunity, customer, product, event, voucher) and the target answer template.
2. Read the target answer template to know exactly which fields are required.
3. Fetch every referenced entity from the API.
4. Cross-validate relationships (e.g. opportunity ↔ customer, quote ↔ product, invoice ↔ opportunity).
5. Compute derived values (totals, validity checks, risk assessments, recognition statuses).
6. Generate follow-up actions where the template calls for them.
7. Assemble the final JSON strictly matching the template structure.
8. Output only the JSON with no surrounding text.
