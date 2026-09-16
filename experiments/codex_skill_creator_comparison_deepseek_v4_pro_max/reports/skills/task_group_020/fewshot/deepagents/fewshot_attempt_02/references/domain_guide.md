# M&A Domain Concepts and Methodology

## Task Types

The workbench supports five main transaction-practice task types:

| Task | Client side | Agreement type | Output shape |
|---|---|---|---|
| Seller-side APA issue register | Seller | Asset purchase | Issue register with priority order, summary metrics, quantified deltas |
| Buyer-side SPA closing package | Buyer | Stock purchase | Economics with holder allocation, indemnity, escrow, NWC, consents, covenants, regulatory, closing readiness |
| Committee escalation memo | Either | Any | Escalated out-of-policy terms with policy comparison, benchmarks, exposure, recommendations, aggregate summary |
| Carveout transition review | Seller | Carveout APA | Transition issues, required redlines, operational risk, quantified exposures |
| Deviation matrix / SPA position matrix | Buyer | Stock purchase | Position matrix per issue, closing blockers, risk totals |

## M&A Terminology

### Indemnity

- **Cap**: Maximum seller liability for general rep breaches, expressed as a percent of purchase price. Seller playbooks seek lower caps; buyer playbooks seek higher.
- **Basket**: Threshold before indemnity claims accrue. Can be deductible (buyer absorbs first dollar) or first-dollar / tipping. Seller playbooks prefer deductible baskets.
- **Survival period**: How long representations survive post-closing. Typically 12-24 months for general reps; fundamental reps survive longer (indefinite or statute of limitations).
- **Materiality scrape**: Removes materiality qualifiers for damages calculation. Variants: `FULL_BREACH_AND_DAMAGES`, `BREACH_ONLY`, `NONE`.

### Escrow

- Held back from purchase price to secure indemnity obligations.
- Typical: 8-15% of purchase price, released at survival expiration (12-18 months).
- Buyer seeks higher percentage, longer release; seller seeks lower, shorter.

### Closing Mechanics

- **Financing condition**: Allows buyer to walk if financing fails. Sellers resist this.
- **Reverse break fee**: Fee buyer pays if it breaches and deal fails. Sellers want 3-6% of deal value.
- **Outside date**: Drop-dead date after which either party can walk. Include regulatory extension periods.
- **Hell or high water**: Buyer must accept any regulatory remedy to close. Sellers want this; buyers resist.
- **HSR**: Hart-Scott-Rodino premerger notification. Required for deals exceeding size-of-transaction threshold. A closing condition is standard.

### Restrictive Covenants

- **Non-compete**: Restricts seller from competing in acquired business for a period (typically 12-24 months). Scope limited to acquired business.
- **Non-solicit**: Restricts soliciting employees or customers. Exclusions for general solicitation and former employees.

### Transition Services (TSA)

- Post-closing services seller provides to buyer (billing, HR, IT, dispatch).
- Duration: typically 6-12 months. Fees: at-cost, cost-plus, fixed. Include clean termination rights.

### Tax

- **Section 1060 allocation**: Purchase price allocation under IRC. Mutual agreement preferred.
- **Transfer taxes**: Split 50/50 or allocated to one party. Include bulk sale costs.

### Employment

- **Service credit**: Recognition of prior service years for benefit plans.
- **PTO liability**: Accrued paid time off that buyer must honor.
- **WARN Act**: Worker Adjustment and Retraining Notification Act risk.

### Governing Law and Forum

- Delaware law and Delaware Court of Chancery / federal court are the market standard for M&A disputes. Lack of a governing law/forum clause is always an issue.

## Playbook Interpretation

### Preferred vs Fallback

Each playbook rule typically provides:
- A **preferred** position (best outcome for the client)
- A **fallback** position (minimum acceptable)

When comparing the draft:
- Draft at or better than preferred → `in_policy` (no issue)
- Draft between preferred and fallback → may be `draft_below_playbook` depending on direction
- Draft worse than fallback → `draft_exceeds_playbook` or `draft_below_playbook`
- Term absent from draft when required → `missing_required_term`

Direction matters: for seller playbooks, "exceeds" means the buyer extracted more than the fallback allows (higher caps, longer survival, more escrow). For buyer playbooks, "below" means less protection than the fallback provides.

### Issue Status Classification

`in_policy`: draft meets or exceeds the client's playbook position; accept as-is.
`out_of_policy`: draft contradicts a clear playbook rule; revise.
`missing_required_term`: no term present but playbook/policy requires one; add.
`draft_exceeds_playbook`: draft demands more than seller playbook fallback; revise down.
`draft_below_playbook`: draft provides less than buyer playbook fallback; revise up.

### Recommended Actions

`delete`: remove a term entirely (e.g. buyer financing condition from seller draft).
`revise`: modify existing term to align with playbook.
`add`: insert a missing term required by playbook.
`accept`: term is in policy; no change needed.
`escalate`: send to committee or business lead.
`approve`: committee approves the term.
`approve_with_conditions`: committee approves with specific conditions.
`reject`: committee rejects the term.

## Policy Threshold Comparison

Policy records define numeric boundaries. A term is escalated for committee review when:

- A fee percentage exceeds the threshold
- Survival months exceed allowed limits
- Additional carveouts beyond the approved group are added
- Required triggers (e.g. intervening event) are missing from fiduciary-out provisions
- Match rights exceed allowed business days

Exclude distractor terms: stale terms, terms already in policy, or terms not subject to committee oversight. Only include current draft terms that breach a policy threshold.

## Dollar Calculation Methodology

### Default Basis

Calculate percentages against the headline purchase price (`headline_value` from the deal record) unless a record explicitly states a different basis. Never use the purchase price from a different deal.

```
amount = round(percent / 100 * headline_value)
delta = draft_amount - fallback_amount (or preferred_amount depending on template)
```

### Rounding

- Currency: round to nearest integer dollar
- Percentages: round to one or two decimal places in percent points (as template specifies)
- Time: integer months or days

### Holder Allocation

For stock purchase deals with a cap table:
```
cash_amount = fully_diluted_pct * upfront_cash (rounded to integer)
stock_amount = fully_diluted_pct * stock_value (rounded to integer)
total_consideration = cash_amount + stock_amount
```

Fully diluted percentages are given to 4 decimal places.

## Priority Ordering Conventions

Priority rank from highest to lowest:

1. Closing certainty: financing conditions, reverse break fees, HSR conditions, consent conditions
2. Escrow economics: escrow percentage, release mechanics
3. Indemnity exposure: caps, baskets, survival periods
4. Employee transition: continuity, service credit, PTO
5. Transition services: scope, duration, fees
6. Restrictive covenants: non-competes, non-solicits
7. Tax allocation: Section 1060, transfer taxes
8. Governing law and forum

Within the same tier, issues with higher dollar impact rank above lower-impact issues.

## Risk Rating Methodology

### HIGH
- Terms directly affecting closing certainty (financing condition, reverse break fee, regulatory, material consent conditions)
- Large economic gaps: escrow/indemnity cap shortfall exceeding $5M or 3% of headline value
- Missing critical terms: no escrow in a buyer-side deal, no HSR condition when required
- Employee continuity gaps affecting entire workforces
- Operational disruption with quantified exposure over $2M

### MEDIUM
- Survival period gaps
- Missing non-blocking terms: tax allocation, governing law, baskets
- Restrictive covenant scope issues
- Transition service fee-model disagreements
- Benchmarked terms at or near upper quartile

### LOW
- Administrative consents that are notice-only
- Non-blocking contractual notices
- Governing law variations within established forums

## Common Output Conventions

- Use stable IDs from workbench records exactly; never invent IDs
- Source term IDs arrays are empty (`[]`) when the term is missing from the draft
- Closing blocker IDs can be consent IDs, synthetic regulatory IDs (e.g. `REG_PRJ_EXAMPLE_HSR`), or material contract IDs
- Committee escalation terms reference policy IDs, not playbook IDs
- Transition reviews use `redline_action` alongside `recommended_action`
- Negative deltas (seller advantage) still use positive integers in the delta fields when the template interprets them as absolute gaps
- When the template expects `final_position` enums, use the exact values from the template's allowed list

## Data Gathering Sequence

1. **Deal record**: Get headline value, parties, status, dates
2. **Terms**: Get current draft provisions
3. **Playbook or Policy**: Get the governing rules
4. **Employees**: Gather headcounts, PTO, service credit, WARN risk
5. **Consents**: Identify closing conditions vs notices
6. **Material contracts**: Identify consent-requiring contracts and revenue at risk
7. **Regulatory**: Check HSR requirement, approval type
8. **Risk estimates**: Get quantified exposure ranges
9. **Benchmarks**: Get market comparables for positions
10. **Diligence findings**: Get special indemnity sources, NWC adjustment basis
11. **Notes**: Check for negotiation history
12. **Cap table**: For stock deals only, get holder allocations
13. **Documents**: Verify document references

Parallelize API calls where possible. The endpoints are independent.
