## M&A Domain Concepts — Quick Reference

### Core Deal Structures

| Concept | Meaning |
|---------|---------|
| **APA** | Asset Purchase Agreement — buyer acquires specified assets and liabilities |
| **SPA** | Stock Purchase Agreement — buyer acquires target company shares |
| **Carveout** | Sale of a division or business unit from a larger entity (typically an APA) |
| **Headline Purchase Price** | The announced total deal value, used as the basis for percentage calculations unless a source states otherwise |

### Indemnity & Risk Allocation

| Concept | Meaning |
|---------|---------|
| **Indemnity Cap** | Maximum aggregate liability of the indemnifying party, expressed as % of purchase price or a dollar amount |
| **Indemnity Basket** | Threshold loss amount before indemnity claims can be made. Can be a "tipping basket" (once exceeded, recovery from dollar one) or a "deductible" (recovery only for amounts above the threshold) |
| **Survival Period** | Duration after closing during which representations and warranties survive and can support indemnity claims. Typically 12–24 months for general reps, longer for fundamental reps |
| **Materiality Scrape** | Provision that strips materiality qualifiers from representations for purposes of determining whether a breach occurred and/or calculating damages. Variants: full (breach + damages), breach-only, or none |
| **Knowledge Qualifier** | Limits representations to what the representing party "knows," often with a defined knowledge group. Buyer-side typically resists or narrows these |

### Closing Mechanics

| Concept | Meaning |
|---------|---------|
| **Escrow / Holdback** | Portion of the purchase price withheld at closing to secure indemnity obligations. Released after a specified period (often 12–18 months) |
| **Working Capital** | Current assets minus current liabilities at closing. Often subject to a post-closing true-up |
| **Closing Conditions** | Conditions that must be satisfied or waived before the transaction can close |
| **Consent Condition** | Requirement to obtain third-party consents (landlords, counterparties, regulators) before closing |
| **Financing Condition** | Condition that buyer must obtain committed financing. Seller-side typically resists or seeks reverse break fee |
| **Reverse Break Fee** | Fee payable by buyer to seller if the deal fails for buyer-side reasons (e.g., financing failure) |

### Regulatory

| Concept | Meaning |
|---------|---------|
| **HSR** | Hart-Scott-Rodino Antitrust Improvements Act — US premerger notification filing |
| **Hell or High Water** | Regulatory efforts covenant requiring the buyer to take any action (divestitures, behavioural remedies) short of bankruptcy to obtain clearance |
| **Regulatory Efforts Standard** | The level of effort required for antitrust clearance — ranges from "commercially reasonable efforts" to "hell or high water" |

### Transition & Separation (Carveout-Specific)

| Concept | Meaning |
|---------|---------|
| **TSA** | Transition Services Agreement — seller provides post-closing support services (IT, HR, finance) for a limited period |
| **Section 1060** | IRS provision requiring purchase price allocation among asset classes in an asset acquisition. Both buyer and seller must file consistent allocations |
| **Transfer Tax** | Sales/use tax, real property transfer tax, and similar taxes triggered by the asset transfer |
| **IP Assignment** | Transfer of intellectual property rights, including patents, trademarks, copyrights, trade secrets, and domain names |

### Employee Matters

| Concept | Meaning |
|---------|---------|
| **Service Credit** | Recognition of prior service with the seller for purposes of the buyer's benefit plans (vesting, PTO accrual, severance) |
| **PTO Liability** | Accrued but unused paid time off that the buyer assumes or the seller retains |
| **Retention Bonuses** | Stay-put or transaction bonuses to retain key employees through closing or transition |
| **Restrictive Covenants** | Non-compete and non-solicitation obligations on the seller post-closing |
| **D&O Tail** | Extended directors & officers liability insurance covering pre-closing acts for a tail period (typically 6 years) |

### Governance

| Concept | Meaning |
|---------|---------|
| **Governing Law** | Which jurisdiction's law governs the agreement (commonly Delaware for US deals) |
| **Forum** | Which court or arbitration venue has jurisdiction over disputes |
| **Playbook** | A party's internal negotiating guidelines setting preferred, fallback, and unacceptable positions on deal terms |
| **Policy Threshold** | Company policy limit that, when exceeded, requires escalation to a committee or business lead for approval |

### Calculation Conventions

| Domain | Convention |
|--------|-----------|
| Currency | Integer USD (no cents) |
| Percentages | Decimal number in percent points. Default: 2 decimal places. Holder percentages: 4 decimal places. Check template for per-field overrides |
| Months | Integer months |
| Dates | `YYYY-MM-DD` format |
| Dollar Basis | Headline purchase price unless a source explicitly states a different basis |
| Delta / Shortfall | `preferred - draft` or `fallback - draft` (always non-negative; the gap from draft to target) |

### Issue Classification

| Status | Meaning |
|--------|---------|
| `in_policy` | Draft term falls within playbook/policy limits — no action needed |
| `out_of_policy` | Draft term exceeds or falls below a policy threshold — requires escalation or revision |
| `missing_required_term` | A protective term that the playbook requires is absent from the current draft |
| `draft_exceeds_playbook` | Draft term is more aggressive than the playbook allows (typically seller overreach into buyer protections) |
| `draft_below_playbook` | Draft term is weaker than the playbook minimum (typically buyer draft falls short of buyer protections) |

### Recommended Actions

| Action | Meaning |
|--------|---------|
| `accept` | Accept the draft term as-is |
| `revise` | Propose changes to bring the term closer to preferred/fallback |
| `delete` | Remove the term entirely from the draft |
| `add` | Insert a new term that is currently missing |
| `escalate` | Escalate to business lead or committee for decision |
| `approve` | Approve the term (committee context) |
| `approve_with_conditions` | Approve subject to specified conditions being met |
| `reject` | Reject the term and require renegotiation |

### Risk Ratings

| Rating | Meaning |
|--------|---------|
| `LOW` | Immaterial or readily manageable issue |
| `MEDIUM` | Material issue requiring attention but not deal-threatening |
| `HIGH` | Deal-threatening or large-exposure issue requiring immediate escalation |

### Business Outcomes (for categorising issues)

| Outcome | Description |
|---------|-------------|
| `closing_certainty` | Affects likelihood of closing on schedule |
| `escrow_economics` | Affects post-closing economics via escrow/holdback |
| `indemnity_exposure` | Affects post-closing liability exposure |
| `restrictive_covenants` | Affects competitive restrictions on seller |
| `employee_transition` | Affects employee treatment and retention |
| `tax_allocation` | Affects tax liability allocation |
| `governing_law` | Affects dispute resolution venue and rules |
| `regulatory_efforts` | Affects antitrust clearance obligations |
