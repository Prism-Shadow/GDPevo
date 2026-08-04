# M&A Deal Workbench Skill

Use this skill when the task involves an **M&A deal workbench API** — a read-only web service that provides deal records, draft terms, playbook rules, policy thresholds, benchmarks, risk estimates, cap tables, employee data, consents, regulatory filings, diligence findings, material contracts, and notes for simulated M&A transactions.

Apply the operating rules below to gather data, analyse deal terms, and produce structured JSON outputs for tasks such as seller- or buyer-side issue registers, economics and closing packages, committee escalation memos, transition reviews, and deviation matrices.

---

## 1. Environment Setup

The workbench lives at an environment-specific base URL. Look for it in:

- The task prompt, which uses the placeholder `<TASK_ENV_BASE_URL>`.
- A file named `environment_access.md` in the workspace, which provides the actual base URL (e.g., `http://task-env:9020/`).

**Replace `<TASK_ENV_BASE_URL>` with the value from `environment_access.md` in every API call.**

All endpoints return JSON. No authentication headers are required. A read-only SQL endpoint is available with a fixed token.

> Full endpoint reference: see `skill/api_endpoints.md`.

---

## 2. Data-Gathering Workflow

For any M&A workbench task, follow this sequence:

### Phase 1 — Core Records (always fetch)

1. **Deal record** — `GET /api/deals/{deal_id}` to get the deal summary, purchase price, structure, parties, and status.
2. **Draft terms** — `GET /api/deals/{deal_id}/terms` to get the current draft agreement terms.
3. **Applicable rules** — Identify the relevant playbook or policy from the task prompt (e.g., `PB_SELLER_X`, `PB_BUYER_X`, or a named policy), then fetch:
   - `GET /api/playbooks/{playbook_id}/rules` — for playbook-based comparison
   - `GET /api/policies/{policy_id}/thresholds` — for policy-threshold-based comparison

### Phase 2 — Supplementary Records (fetch as the task type demands)

| When the task involves… | Fetch these additional endpoints |
|--------------------------|----------------------------------|
| Financial / holder economics | `/api/deals/{deal_id}/cap-table` |
| Risk assessment | `/api/deals/{deal_id}/risk-estimates` |
| Closing conditions / consents | `/api/deals/{deal_id}/consents` |
| Employee treatment | `/api/deals/{deal_id}/employees` |
| Regulatory (HSR, antitrust) | `/api/deals/{deal_id}/regulatory` |
| Contract-level blockers | `/api/deals/{deal_id}/material-contracts` |
| Due diligence findings | `/api/deals/{deal_id}/diligence-findings` |
| Market context | `/api/deals/{deal_id}/benchmarks` |
| Negotiation history | `/api/deals/{deal_id}/notes` |
| Documents index | `/api/deals/{deal_id}/documents` |

### Phase 3 — Cross-Table Validation (use when needed)

When you need to verify relationships across records or the task asks for it, use the read-only SQL endpoint:

```
POST /api/query
Body: {"token": "deal-workbench-readonly", "sql": "<SELECT or WITH statement>"}
```

- Only `SELECT` and `WITH` (CTE) queries are allowed.
- Prefer direct API GET calls when a dedicated endpoint exists — they are faster and return pre-joined structures.
- Use SQL when you need joins, aggregations, or filters not available through the REST endpoints.

---

## 3. Task-Type Patterns

The workbench supports several recurring task patterns. Identify which pattern the current task matches and adapt accordingly.

### Pattern A — Issue Register (seller-side APA review)

**Goal:** Compare the buyer's draft against the seller's playbook and produce a structured issue register with priority ordering.

**Method:**
1. Fetch the deal record, draft terms, and seller playbook rules.
2. For every playbook rule, locate the corresponding draft term (by matching on term category).
3. Classify each term:
   - `in_policy` — draft matches or is within playbook bounds → no issue.
   - `out_of_policy` — draft exceeds playbook limits → issue.
   - `missing_required_term` — playbook requires a term that is absent from the draft → issue.
   - `draft_exceeds_playbook` — draft is more permissive than the playbook allows → issue.
   - `draft_below_playbook` — draft is weaker than the playbook minimum → issue (more common on buyer-side).
4. For each issue, populate: `source_term_ids`, `business_outcome`, `risk_rating`, `recommended_action`, and all applicable quantified fields (percentages, dollar amounts, months).
5. Sort issues into a `priority_order` list from highest to lowest negotiation priority.
6. Compute `summary_metrics`: issue counts, risk distribution, headline value, quantified exposure ranges.

**Key judgement calls:**
- Treat **absent seller-protective terms** as issues only when the surrounding deal data shows the term is genuinely needed (not every missing term is an issue).
- Dollar amounts derive from the **headline purchase price** unless a source explicitly states a different basis.
- Priority is driven by risk rating and dollar exposure, then by closing-criticality.

### Pattern B — Economics & Closing Package (buyer-side SPA)

**Goal:** Prepare a comprehensive closing package covering holder-level economics, indemnity mechanics, escrow terms, closing conditions, employee treatment, and readiness assessment.

**Method:**
1. Fetch the deal record, draft terms, buyer playbook rules, cap table, consents, employees, material contracts, regulatory status, and diligence findings.
2. **Economics section:** From the cap table, compute per-holder allocation — fully diluted percentage, as-converted shares, cash amount, stock amount, total consideration. Use headline purchase price as the basis.
3. **Indemnity package:** Compare draft cap %, survival months, and materiality-scrape treatment against buyer playbook. Compute preferred and fallback positions. Assign risk rating.
4. **Escrow:** Determine basis (purchase_price, upfront_cash, or identified_findings), required percentage, dollar amount, release months, and release trigger.
5. **Closing conditions:** Enumerate required consents, HSR/regulatory status, material-contract conditions. For each blocker, note whether it must be satisfied before closing and its risk rating.
6. **Employee treatment:** Document service-credit recognition, PTO liability treatment, retention arrangements, and restrictive-covenant posture.
7. **Readiness assessment:** Classify the overall deal as ready, conditionally ready, or blocked. Identify specific blockers.

**Calculation specifics for Pattern B:**
- Holder percentages to **four decimal places**.
- Other percentages to **one decimal place** unless the template says otherwise.
- Dollar amounts: integer USD.

### Pattern C — Committee Escalation Package

**Goal:** Identify only the draft terms that are out of policy or require committee approval, excluding everything else.

**Method:**
1. Fetch the deal record, draft terms, and the applicable **policy thresholds** (not playbook rules — policies are company-internal approval gates, not negotiating positions).
2. Compare each draft term against its corresponding policy threshold.
3. **Filter strictly:** Include only terms that are out of policy or restricted for committee approval. Exclude:
   - Terms that are in-policy (within allowed thresholds).
   - Stale or superseded terms.
   - Non-committee "distractor" terms that are immaterial.
4. For each escalated term, provide:
   - The policy comparison (threshold vs. actual).
   - Quantified amounts (dollar exposure, percentage delta).
   - Benchmark support if available (from `/api/deals/{deal_id}/benchmarks`).
   - The legal or business deviation.
   - A recommendation and any required conditions for approval.
5. Aggregate a committee summary with total quantified exposure and routing fields.

### Pattern D — Transition & Separation Review (seller-side carveout APA)

**Goal:** Review the carveout APA's transition and separation terms, focusing on operational continuity and risk allocation for the separated business.

**Method:**
1. Fetch the deal record, draft terms, and seller playbook rules.
2. Focus on these transition domains:
   - **IP transition** — patent, trademark, copyright, trade-secret, and domain assignments. Check for redirect/transition protections.
   - **Transition services (TSA)** — scope of services, fee structure, duration, and termination rights.
   - **Section 1060 allocation** — purchase price allocation among asset classes. Check that the draft requires mutually agreed allocations.
   - **Transfer tax** — which party bears sales/use tax, real property transfer tax, and similar taxes.
   - **Employee continuity** — service credit, PTO, benefit plan transition, and any retention obligations.
   - **Closing deadline** — outside date, extension rights, and drop-dead protections.
   - **Governing law and forum** — jurisdiction, venue, and any waiver of jury trial.
3. Treat **draft silence** (missing required terms) as issues when the seller position requires an affirmative provision.
4. Produce both an issue list and a redline list. Redlines are specific drafting changes tied to issues.

### Pattern E — Deviation Matrix (buyer-side SPA)

**Goal:** Produce a structured matrix showing every deviation between the draft and the buyer's playbook positions, with final recommended positions and closing-blocker analysis.

**Method:**
1. Fetch the deal record, draft terms, buyer playbook rules, regulatory records, consents, material contracts, diligence findings, benchmarks, risk estimates, documents, and notes.
2. Cover these standard buyer-position topics:
   - **Indemnity cap and basket** — cap percentage, basket type, basket amount.
   - **Survival and knowledge qualifiers** — survival period, knowledge definition, knowledge group.
   - **Materiality scrape** — full, breach-only, or none.
   - **Escrow / holdback / release** — escrow percentage, agent, release trigger, release months.
   - **Consent closing condition** — which consents must be obtained before closing.
   - **HSR condition** — whether HSR clearance is a closing condition and the efforts standard.
   - **Material contracts** — which material contracts require counterparty consent and whether those are closing conditions.
3. For each topic, compute the draft value, preferred value, fallback value, and the shortfall from draft to each target.
4. Classify the **final position** using template-provided enums.
5. List all **closing blockers** with their type, risk rating, amount at risk, and required action.
6. Compute **risk totals**: headline purchase price, issue counts by status and risk, blocker count, exposure amounts, and the highest-modeled-exposure category.

---

## 4. Calculation and Formatting Rules

### Currency
- Always **integer USD** — no decimal places, no cents.
- Round to the nearest integer dollar.

### Percentages
- Expressed as **decimal numbers in percent points** (e.g., 10.50 means 10.50%).
- **Default precision: 2 decimal places** unless the output template specifies otherwise.
- **Holder percentages (cap table): 4 decimal places.**
- **Some tasks specify 1 decimal place or whole percent points** — always check the template.

### Months
- Always **integer months**.

### Dates
- Format as **`YYYY-MM-DD`**.

### Dollar Basis
- Derive all dollar amounts from the **headline purchase price** found in the deal record.
- Only use a different basis when a source record **explicitly** states one.

### Delta / Shortfall Calculation
- `delta_to_fallback` = `fallback_value − draft_value` (for amounts where higher is better for the client).
- If the draft already exceeds the fallback, the delta is `0` (the gap is the amount needed to reach the target).
- For percentages, the same logic applies in percent-point terms.

### Rounding
- Apply rounding **after** multiplication, not before.
- Example: `round(headline_price × cap_pct / 100)` → integer dollars.

---

## 5. Output Construction Rules

### Always
- Return **only valid JSON** — no explanatory prose, markdown fences, or narrative outside the JSON object.
- Conform **exactly** to the structure defined in the task's `answer_template.json` or the output schema in the prompt.
- Use **stable identifiers** from the template (issue IDs, redline IDs, term IDs, etc.) — do not invent new ones.
- Populate **every required field** in the template, even if the value is `null`, `0`, `[]`, or `false`.
- Follow the template's **ordering** instructions (sort by issue_id, by priority, by counsel workflow, etc.).

### Enums
- Use only values from the template's `allowed_enums` or enum lists.
- If a template provides `possible_issue_ids`, `stable_redline_ids`, or similar lists, restrict values to exactly those strings.

### Source Tracing
- Every issue must cite its **source term IDs** (from the draft terms API response).
- For missing required terms, use an **empty array** `[]` for `source_term_ids`.
- When citing supporting records (e.g., a consent, a contract, a diligence finding), use the stable IDs from the API response.

### Null Handling
- A field is `null` when it is **genuinely not applicable** to the issue.
- A field is `0` when it is applicable but the computed value is zero.
- Do not omit required fields — use `null` when the template allows it.

---

## 6. Analysis Heuristics

### Comparing Draft to Playbook
- Read every rule in the playbook/policy response.
- For each rule, scan the draft terms for a matching term (by category, label, or description).
- If no match exists and the rule is protective of the client's side → classify as `missing_required_term`.
- If a match exists, compare the numeric values (percentages, months, dollars) and classification flags (e.g., basket type, materiality-scrape variant).
- The **direction of comparison** depends on client side:
  - **Seller-side:** draft terms that are more buyer-favourable than the seller playbook allows → issue.
  - **Buyer-side:** draft terms that are less buyer-protective than the buyer playbook requires → issue.

### Risk Assessment
- Use `risk-estimates` API data as the primary source for risk quantification.
- Cross-reference with `diligence-findings` for specific exposures (privacy breaches, IP gaps, environmental liabilities).
- A `HIGH` risk rating is warranted when:
  - The dollar exposure exceeds 10% of the headline purchase price, or
  - The issue is a closing blocker (must be resolved before the deal can close), or
  - The playbook marks the term as non-negotiable and the draft is far from it.
- Use `MEDIUM` for material but manageable issues.
- Use `LOW` for immaterial or routine items.

### Priority Ordering
- Sort from highest to lowest priority:
  1. Closing blockers (deal cannot close without resolution).
  2. HIGH-risk issues with large dollar exposure.
  3. HIGH-risk issues with smaller dollar exposure.
  4. MEDIUM-risk issues.
  5. LOW-risk issues.
- Within the same risk tier, sort by dollar exposure descending.

### Committee Escalation Filtering
- **Only** terms that breach a policy threshold are escalated.
- A term that is within policy limits (even if aggressive) is **not** escalated.
- A term that is absent from the draft but required by policy is escalated as `missing_required_term`.
- Benchmark data supports escalation by showing whether the draft position is a market outlier.

---

## 7. Common Pitfalls

- **Using the wrong base URL:** Always replace `<TASK_ENV_BASE_URL>` with the actual value from `environment_access.md`. The workbench will not respond on localhost or any other assumed URL.
- **Computing percentages as fractions:** 10% is `10.00` (not `0.10`). The workbench and templates use percent points throughout.
- **Mixing up playbooks and policies:** Playbooks are negotiating guidelines (preferred/fallback positions). Policies are internal approval thresholds (allowed/not-allowed bounds). Use the right one for the task.
- **Over-including issues:** Not every playbook rule that differs from the draft is an issue. Filter for materiality — if the delta is de minimis and the risk is low, the term may be `in_policy` for practical purposes.
- **Omitting required template fields:** The JSON schema expects every top-level and nested field to be present, even with `null` values. Missing fields cause validation failures.
- **Including narrative outside JSON:** The output must be pure JSON. No "Here is the result:" or markdown code fences.
- **Assuming cross-project data:** Records for one deal do not apply to another unless the task explicitly says so. Each deal is self-contained.

---

## Supporting Files

- `skill/api_endpoints.md` — Complete API endpoint reference with request/response shapes.
- `skill/domain_concepts.md` — M&A domain terminology, calculation conventions, enums, and classification rules.
