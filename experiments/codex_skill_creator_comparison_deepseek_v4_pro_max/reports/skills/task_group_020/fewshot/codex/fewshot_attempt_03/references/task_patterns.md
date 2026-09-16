# M&A Deal Workbench Task Patterns

Each task type has a specific data-gathering plan and output shape.

## Task Type 1: Seller Issue Register (train_001 pattern)

**Purpose**: Compare buyer draft against seller playbook and produce a prioritized issue register.

**Data to gather**:
1. Deal record (`/api/deals/<deal_id>`)
2. Draft terms (`/api/deals/<deal_id>/terms`)
3. Seller playbook rules (`/api/playbooks/<playbook_id>/rules`)
4. Risk estimates (`/api/deals/<deal_id>/risk-estimates`)
5. Employees (`/api/deals/<deal_id>/employees`)
6. Consents (`/api/deals/<deal_id>/consents`)
7. Regulatory (`/api/deals/<deal_id>/regulatory`)
8. Benchmarks (`/api/deals/<deal_id>/benchmarks`)
9. Notes (`/api/deals/<deal_id>/notes`)

**Issue classification**:
- For each playbook rule, find the corresponding draft term value.
- If the term is absent and the rule is required: `missing_required_term` with `add` action.
- If the term exceeds the playbook fallback in a seller-unfavorable direction: `draft_exceeds_playbook` with `revise` action.
- If the term is below the playbook fallback in a seller-unfavorable direction: `draft_below_playbook` with `add` action.
- Treat contextually: missing reverse break fee when buyer proposes financing condition = `draft_below_playbook`.

**Output fields**: issue_register array, priority_order array, summary_metrics object. See the answer template for the exact field schema.

## Task Type 2: Buyer Closing and Economics Package (train_002 pattern)

**Purpose**: Produce a comprehensive closing package covering economics, consents, covenants, regulatory, and readiness.

**Data to gather**:
1. Deal record (`/api/deals/<deal_id>`)
2. Draft terms (`/api/deals/<deal_id>/terms`)
3. Buyer playbook rules (`/api/playbooks/<playbook_id>/rules`)
4. Cap table (`/api/deals/<deal_id>/cap-table`)
5. Consents (`/api/deals/<deal_id>/consents`)
6. Material contracts (`/api/deals/<deal_id>/material-contracts`)
7. Regulatory (`/api/deals/<deal_id>/regulatory`)
8. Employees (`/api/deals/<deal_id>/employees`)
9. Diligence findings (`/api/deals/<deal_id>/diligence-findings`)

**Key calculations**:
- Holder allocation: `cash_amount = headline_value * upfront_cash_ratio * fully_diluted_pct`, stock similarly
- Total consideration = `cash_amount + stock_amount`
- Indemnity cap amounts from headline value * cap percent
- Escrow amounts from headline value * escrow percent
- Closing consent amount at risk: sum of consent amounts with `condition_type: closing_condition` and risk rating `HIGH`

## Task Type 3: Committee Escalation Memo (train_003 pattern)

**Purpose**: Identify terms requiring M&A Committee approval and prepare an escalation memo.

**Data to gather**:
1. Deal record (`/api/deals/<deal_id>`)
2. Draft terms (`/api/deals/<deal_id>/terms`)
3. Policy thresholds (`/api/policies/<policy_id>/thresholds`)
4. Risk estimates (`/api/deals/<deal_id>/risk-estimates`)
5. Benchmarks (`/api/deals/<deal_id>/benchmarks`)

**Escalation criteria**:
- A term is escalated when it exceeds a policy threshold.
- Exclude terms that are within policy (list in `excluded_in_policy_terms`).
- Exclude stale or distractor terms mentioned in the prompt.
- For each escalated term, provide: draft_metric, policy_metric, delta, benchmark (if available), exposure, recommendation, and required_conditions.

**Delta calculation**: `delta = draft_value - policy_threshold_value` (percent points, months, dollars, or counts).

## Task Type 4: Seller Transition Review (train_004 pattern)

**Purpose**: Review carveout APA transition and separation terms from seller perspective.

**Data to gather**:
1. Deal record (`/api/deals/<deal_id>`)
2. Draft terms (`/api/deals/<deal_id>/terms`)
3. Seller playbook rules (use playbook ID from prompt or infer from client side)
4. Consents (`/api/deals/<deal_id>/consents`)
5. Material contracts (`/api/deals/<deal_id>/material-contracts`)
6. Employees (`/api/deals/<deal_id>/employees`)
7. Regulatory (`/api/deals/<deal_id>/regulatory`)
8. Risk estimates (`/api/deals/<deal_id>/risk-estimates`)
9. Documents (`/api/deals/<deal_id>/documents`)

**Transition-specific guidance**:
- IP/domain transition: check for transitional trademark license, domain redirect (301/302), minimum license days (180), redirect months (12).
- TSA scope/duration/fees: check duration months against preferred/fallback, fee model (at minimum cost-plus stranded overhead), clean termination right.
- Employee continuity: check for defined transfer process, service credit recognition, accrued PTO allocation, comparable terms requirement.
- Customer consent condition: limit to required closing consents only, exclude notice-only, require material adverse impact standard.
- Outside date: require seller regulatory extension when HSR is required, typical initial 120 days + 30-day extension.
- Governing law: default to Delaware, Delaware Court of Chancery or Delaware federal court, apply to ancillary documents.

**Output structure**: `transition_issues` array, `required_redlines` array (one redline per issue), `operational_risk` summary.

## Task Type 5: Buyer Deviation Matrix (train_005 pattern)

**Purpose**: Produce buyer-side SPA deviation matrix and closing blocker analysis.

**Data to gather**:
1. Deal record (`/api/deals/<deal_id>`)
2. Draft terms (`/api/deals/<deal_id>/terms`)
3. Buyer playbook rules (`/api/playbooks/<playbook_id>/rules`)
4. Consents (`/api/deals/<deal_id>/consents`)
5. Material contracts (`/api/deals/<deal_id>/material-contracts`)
6. Regulatory (`/api/deals/<deal_id>/regulatory`)
7. Diligence findings (`/api/deals/<deal_id>/diligence-findings`)
8. Benchmarks (`/api/deals/<deal_id>/benchmarks`)
9. Risk estimates (`/api/deals/<deal_id>/risk-estimates`)
10. Documents (`/api/deals/<deal_id>/documents`)

**Position matrix structure**: Each issue in the matrix has:
- `issue_id`: From the template's stable issue IDs
- `source_term_ids`: Matching term IDs from terms endpoint
- `status`: `in_policy`, `draft_below_playbook`, `draft_exceeds_playbook`, `missing_required_term`
- `final_position`: A short snake_case summary of the buyer's position
- `priority_rank`: Integer rank from 1 (highest priority) to N
- Dollar amounts computed from headline_value

**Closing blockers**: Extract from consent records (required consents), regulatory records (HSR clearance), and material contracts (contracts requiring consents). Each blocker requires an action: `obtain_consent`, `obtain_clearance`, or `add_closing_condition`.

**Risk totals**: Sum modeled exposures across issues. Use both low and high estimates from risk estimates. The highest_modeled_exposure_category is the category with the largest high-end exposure.

## Field Value Conventions

- **Currency**: Always integer USD. Round using standard rounding (0.5 rounds up).
- **Percent points**: Decimal numbers to the precision specified in the answer template (usually 1 or 2 decimal places). For holder percentages, use 4 decimal places.
- **Months/Days**: Integers.
- **Dates**: ISO 8601 format (`YYYY-MM-DD`).
- **Nulls**: Use `null` (not `0` or `"none"`) when a field is not applicable.
- **Empty arrays**: Use `[]` when there are no source IDs or when a term is missing.
- **Booleans**: Use `true`/`false` (not strings).
