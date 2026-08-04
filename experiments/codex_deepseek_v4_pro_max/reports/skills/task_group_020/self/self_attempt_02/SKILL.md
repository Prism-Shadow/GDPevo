--- 
name: m-and-a-deal-workbench
description: >
  Navigate and analyze an M&A deal workbench REST API to gather deal records,
  draft terms, playbook rules, policy thresholds, benchmarks, risk estimates,
  cap tables, employee records, consents, regulatory status, material contracts,
  diligence findings, and notes. Compare draft terms against playbooks and
  policies, identify gaps and deviations, quantify exposures, and produce
  structured JSON work products such as issue registers, closing-and-economics
  packages, committee escalation memos, transition reviews, and deviation matrices.
  Use this skill whenever a task involves reviewing an M&A deal, preparing a
  negotiation position, escalating terms to a committee, or building a structured
  deal analysis from the deal workbench API.
---

# M&A Deal Workbench Skill

## Purpose
This skill enables systematic review of M&A transactions against a REST API
workbench. The workbench exposes deal records, draft term sheets, seller/buyer
playbooks, committee policy thresholds, benchmarks, risk estimates, cap tables,
employee rosters, third-party consents, regulatory assessments, material
contracts, diligence findings, and free-text notes. The agent's job is to gather
all relevant data, compare the draft positions to the applicable playbook or
policy, flag gaps and deviations, compute quantified impacts, and return a
single JSON object that conforms exactly to the answer template provided with
the task.

## Environment and API Access

### Base URL
The task prompt provides the workbench base URL as `<TASK_ENV_BASE_URL>` or
sets the environment variable `GDPEVO_ENV_BASE_URL`. All API calls use this
base. Do not hard-code a URL; always derive it from the environment or prompt.

### GET Endpoints
Every allowed GET route is documented in `environment_access.md`. The canonical
routes include:

| Route | Returns |
|-------|---------|
| `/api/deals` | List of deal records |
| `/api/deals/{deal_id}` | Deal header (project name, counterparty, signing date, purchase price, side) |
| `/api/deals/{deal_id}/terms` | Current draft terms with term IDs, clause text, and values |
| `/api/deals/{deal_id}/benchmarks` | Market benchmarks (e.g. indemnity cap percentiles, survival period medians) |
| `/api/deals/{deal_id}/risk-estimates` | Modeled risk exposure per issue with low/high ranges |
| `/api/deals/{deal_id}/cap-table` | Capitalization table (holders, security classes, fully-diluted percentages) |
| `/api/deals/{deal_id}/consents` | Required third-party consents with contract names and statuses |
| `/api/deals/{deal_id}/employees` | Employee roster with service dates, PTO balances, warn-risk flags |
| `/api/deals/{deal_id}/material-contracts` | Material contracts with annual revenue and consent triggers |
| `/api/deals/{deal_id}/regulatory` | HSR status, threshold basis, required approvals |
| `/api/deals/{deal_id}/diligence-findings` | Diligence findings with IDs, amounts at risk, resolution status |
| `/api/deals/{deal_id}/notes` | Free-text negotiation notes |
| `/api/deals/{deal_id}/documents` | Document metadata |
| `/api/playbooks` | List of playbook IDs |
| `/api/playbooks/{playbook_id}/rules` | Playbook rules with preferred/fallback positions per issue category |
| `/api/policies` | List of policy IDs |
| `/api/policies/{policy_id}/thresholds` | Committee approval thresholds and limits |
| `/api/search` | Search endpoint |

### Read-Only SQL (POST /api/query)
When available, send `POST /api/query` with:
```json
{"token": "deal-workbench-readonly", "sql": "<SELECT or WITH query>"}
```
Use this for cross-table joins, aggregation, or filtering that is inefficient
over individual GET calls. The schema is discoverable from the GET responses;
infer table and column names from the JSON key structure of the workbench
records.

### Authentication
No authentication headers are required beyond the `deal-workbench-readonly` token
for the SQL endpoint. All GET endpoints are unauthenticated.

## Data-Gathering Protocol

Follow this sequence on every task. Skipping a relevant data source causes
incomplete analysis.

1. **Deal header** — `GET /api/deals/{deal_id}`. Extract the project name,
   client/counterparty names, headline purchase price (the basis for all
   dollar calculations), signing date, and client side (buyer or seller).

2. **Draft terms** — `GET /api/deals/{deal_id}/terms`. Capture every term's
   `term_id`, category, clause text, and numeric values (percent, months,
   dollars).

3. **Playbook or policy** — If the prompt names a playbook (e.g. `PB_SELLER_A`,
   `PB_BUYER_A`), fetch `GET /api/playbooks/{id}/rules`. If it names a policy
   (e.g. for committee escalation), fetch `GET /api/policies/{id}/thresholds`.
   A task may require both.

4. **Supporting records** — Fetch every endpoint listed in the prompt or answer
   template that is relevant to the analysis categories. At minimum, consider:
   - Benchmarks
   - Risk estimates
   - Cap table (if holder-level allocation or equity economics are needed)
   - Consents
   - Employees (if continuity, PTO, or service credit are needed)
   - Material contracts (if consent conditions or revenue thresholds apply)
   - Regulatory (if HSR, hell-or-high-water, or industry approvals apply)
   - Diligence findings (if quantified risk or special indemnities apply)
   - Notes (for negotiation context)

5. **Cross-check with SQL** — Run `POST /api/query` to join tables when the
   GET hierarchy is not sufficient. Example: count employees by warn-risk status,
   sum PTO liabilities, or find terms that reference specific findings.

## Analysis Framework

### Comparing Draft to Playbook
For every term category the playbook addresses:

- Extract the draft value from the terms endpoint.
- Extract the playbook preferred and fallback values.
- If the term is entirely absent from the draft but the playbook requires it,
  classify as `missing_required_term`.
- If the draft value is more favorable to the counterparty than the playbook
  fallback, classify as `draft_below_playbook` (seller-side) or
  `draft_exceeds_playbook` (buyer-side: the draft gives away more than the
  playbook allows).
- If the draft value falls between preferred and fallback, classify as
  `in_policy` (it is within the negotiable range).
- If the draft value is better for the client than the playbook preferred,
  classify as `in_policy`.

### Comparing Draft to Policy Thresholds
For committee escalation tasks:

- Compare each draft term against the policy threshold.
- A term is escalated (out of policy) when its numeric value exceeds or falls
  short of the threshold in a direction unfavorable to the client.
- Exclude terms that are in-policy, stale, or irrelevant to the committee's
  mandate.

### Identifying Missing Terms
A term is missing when:
- The playbook or policy requires an affirmative provision (e.g. escrow,
  non-compete, HSR closing condition, Section 1060 allocation, D&O tail,
  transition services), and
- The draft terms contain no entry for that category, or the relevant clause
  is silent on the required protection.

When a term is missing, set `source_term_ids` to an empty array and
`issue_status` to `missing_required_term`.

### Quantification Rules
- **Dollars**: Always integer. Calculate from the deal's headline purchase
  price unless a specific record states a different basis. When computing a
  percentage of purchase price, round to the nearest integer dollar.
- **Percent points**: Decimal number to two decimal places (e.g. `12.50`)
  unless the answer template explicitly specifies one or four decimal places.
  Percent points are the numeric difference; do not convert to basis points.
- **Months**: Integer months (e.g. `18` not `18.0`).
- **Dates**: `YYYY-MM-DD` format when the template requires dates.
- **Delta calculations**: `draft_value - fallback_value` for shortfall; prefer
  signed integers where the template says `delta_` or `shortfall_`.

### Risk Rating Assignment
Use these heuristics when the workbench does not provide an explicit risk rating:

- **HIGH**: The issue creates a material financial exposure (>= 1% of purchase
  price), a closing blocker, or a permanent loss of a core protection (e.g. no
  escrow, no non-compete, missing HSR condition).
- **MEDIUM**: The issue creates quantifiable exposure below the HIGH threshold,
  or a moderate gap between draft and fallback that can be negotiated.
- **LOW**: The gap is small, the exposure is de minimis, or the playbook
  preferred is already met.

### Priority Ordering
Order issues from highest to lowest negotiation priority by:
1. Closing blockers first
2. Highest dollar exposure next
3. HIGH risk before MEDIUM before LOW
4. Within the same tier, use the order implied by the answer template's
   `stable_issue_ids` or `possible_issue_ids` list.

## Output Rules

### Strict JSON Only
Return **only** valid JSON. No markdown fences, no explanatory prose, no
trailing text. The entire response must parse as a single JSON object.

### Answer Template Conformance
Every field, nested object, and array element prescribed by the answer template
must be present. Optional fields (those with `null` default in the template)
should be included with `null` when not applicable. Enum fields must use one
of the allowed values exactly as spelled in the template.

### Stable Identifiers
Use the exact `issue_id`, `term_id`, `redline_id`, `consent_id`, `contract_id`,
`finding_id`, `employee_id`, and `playbook_id` strings returned by the workbench
API. When the template provides a `possible_issue_ids` or `stable_issue_ids`
list, choose from that list — never invent new identifiers.

### Language
All string values must be in English unless the template explicitly permits
otherwise.

## Common Issue Categories and Default Positions

### Indemnity Package
- **Cap**: Percentage of purchase price. Seller prefers lower; buyer prefers
  higher. Compute cap amounts as `cap_pct * headline_purchase_price`.
- **Basket**: Dollar threshold before indemnity claims can be brought. Seller
  prefers higher (deductible); buyer prefers lower (first-dollar). May be a
  tipping basket (claims over threshold recover from dollar one) or
  deductible.
- **Survival period**: Months after closing during which reps survive. Seller
  prefers shorter; buyer prefers longer. Fundamentals (tax, organization,
  authority) typically survive longer or indefinitely.
- **Materiality scrape**: Whether materiality qualifiers are ignored for
  damages calculation. Options: full breach and damages, breach only, or none.

### Escrow / Holdback
- **Amount**: Percentage of purchase price held back. Buyer wants higher
  (more security); seller wants lower.
- **Release**: Months until release. General reps survival expiration is the
  typical trigger. May have tiers (e.g. partial release at 12 months, full at
  18).
- **Agent**: Who holds escrow. If the draft is silent on the escrow agent,
  flag as missing.

### Restrictive Covenants
- **Non-compete**: Duration in years, geographic scope, covered activities.
  Buyer requires; seller's key holders and executives must be bound.
- **Non-solicit**: Customers and employees. Usually mirrors non-compete term.
- A missing non-compete/non-solicit is a HIGH risk item for the buyer.

### Employees
- **Service credit**: Whether acquiring entity honors prior service for
  vesting, PTO accrual, and benefits eligibility.
- **PTO liability**: Total accrued and unused PTO. Can be a purchase price
  reduction item.
- **WARN Act / retention**: Count of employees at risk; retention bonus
  requirements.
- **Employee continuity**: Whether offer letters are required, at what
  compensation levels.

### Transition Services
- **TSA scope**: Which services the seller provides post-close (IT, HR,
  finance, facilities).
- **TSA fees**: Cost model -- at cost, cost-plus, or fixed fee.
- **TSA duration**: Months of transition support.
- **Service credit**: Whether the buyer gets a credit against fees for
  stranded costs.

### Tax Allocation
- **Section 1060 / purchase price allocation**: Who controls the allocation
  (buyer, seller, or mutually agreed). Missing allocation language means the
  buyer may unilaterally file, disadvantaging the seller.
- **Transfer taxes**: Who pays. Split, seller pays, or buyer pays.

### Governing Law and Forum
- **Governing law**: State (usually Delaware for US deals).
- **Forum**: Court selection. Delaware Court of Chancery is typical for
  Delaware law. Federal vs. state court. Exclusive vs. non-exclusive
  jurisdiction.

### Regulatory
- **HSR (Hart-Scott-Rodino)**: Whether filing is required based on transaction
  size. If required, the agreement must include an HSR clearance closing
  condition.
- **Hell-or-high-water**: Degree of effort required to obtain regulatory
  approval. Seller typically wants a strong covenant; buyer may resist.
- **Other approvals**: Industry-specific (FCC, FAA, banking, healthcare).

### Consents and Material Contracts
- **Closing condition consents**: Third-party consents required before closing.
  Must be classified as closing condition, notice-only, or post-closing
  covenant.
- **Amount at risk**: Revenue or value tied to contracts requiring consent.
- **Material contract revenue**: Annual revenue from contracts that trigger
  on change of control.

### Financing and Deal Certainty
- **Financing condition**: Whether closing is conditioned on buyer obtaining
  financing. Seller wants none (or a reverse break fee).
- **Reverse break fee**: Fee buyer pays seller if deal fails for financing
  reasons. Usually a percentage of purchase price.

### Working Capital
- **Adjustment mechanic**: Dollar-for-dollar outside a collar, fixed-price
  no adjustment, or other.
- **Collar**: The +/- range around the target within which no adjustment occurs.

### D&O Tail
- **Tail policy**: Whether seller's D&O insurance is extended post-close.
- **Period**: Years of tail coverage.
- **Cost allocation**: Who pays the tail premium.

### Fiduciary Out and MAE
- **Fiduciary out**: Seller's ability to terminate for a superior proposal.
  Tied to match rights and intervening event triggers.
- **MAE carveouts**: Exceptions to the material adverse effect definition
  (e.g. pandemics, war, market conditions). Buyer wants fewer carveouts.

## Example Workflow for a Typical Task

1. Read the prompt carefully. Identify the deal ID, client side (buyer/seller),
   the applicable playbook or policy, and the answer template path.

2. Read `environment_access.md` to confirm the base URL and available routes.

3. Fetch the deal header to confirm the project and purchase price.

4. Fetch the draft terms and the playbook rules (or policy thresholds).

5. Fetch all supporting records that are relevant to the categories named in
   the answer template.

6. Use SQL to cross-check or aggregate when the GET hierarchy is insufficient
   (e.g. join employees to findings, sum PTO across departments, count
   consent types).

7. Build the analysis:
   - Compare each draft term to the playbook/policy.
   - Identify missing required terms.
   - Quantify dollar deltas, percent-point gaps, month shortfalls.
   - Assign risk ratings.
   - Derive priority order.

8. Populate the answer template fully, using stable IDs from the workbench,
   null for inapplicable fields, and exact enum values.

9. Return only the JSON.

## Common Pitfalls

- **Using the wrong basis for dollar calculations**: Always derive from
  headline purchase price unless a record explicitly states a different basis
  (e.g. upfront cash, equity value, or a finding-specific amount).
- **Mixing up buyer and seller perspectives**: A cap that is "too low" for a
  buyer is "good" for a seller. Always orient analysis to the client side
  stated in the prompt.
- **Treating absent terms as in-policy**: Silence in the draft on a required
  playbook/policy term is `missing_required_term`, not `in_policy`.
- **Including extraneous terms**: Only include issues the template asks for.
  If the template has a fixed `possible_issue_ids` list, do not add issues
  outside that list.
- **Incorrect enum values**: Use exact strings from the template's
  `allowed_enums` or inline enum comments. Case and underscores matter.
- **Omitting null fields**: Every field in the template must appear in the
  output, even if its value is `null`.
- **Numeric type errors**: Dollars must be integers, not floats. Percent
  points must be numbers (not strings). Months must be integers.
- **Adding markdown fences**: The response is raw JSON only. No ```json fences.
