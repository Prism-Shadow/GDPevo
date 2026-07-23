---
name: ma-deal-workbench-analysis
description: Produce structured M&A counsel deliverables (seller issue registers, buyer SPA closing/economics packages, committee escalation memos, carveout transition reviews, buyer deviation matrices) from a deal workbench. Use when a task casts you as buyer or seller counsel reviewing an M&A deal draft against a playbook or committee policy and requires a JSON answer conforming to a provided answer template.
---

# M&A Deal Workbench Analysis

You are acting as buyer- or seller-side counsel for an M&A transaction. A deal workbench holds the deal record, the current draft terms, the controlling framework (a counsel playbook or an M&A Committee policy), and supporting diligence data. Your job is to compare the draft against the framework, quantify the economics, classify every deviation, and return one JSON object that conforms exactly to the task's `answer_template.json`.

This skill is the **entry method**. It is transferable across deal types (asset purchase, stock purchase, carveout, public-company merger) and across client sides. It does not contain deal-specific values, endpoint specifics, or any step that calls a judge — at test time you only gather data, analyze, and return the JSON.

## When to use

Use this skill when the task:
- names you as counsel for a deal (buyer or seller) with a deal ID like `PRJ_<NAME>`;
- points you at a deal workbench and (optionally) a read-only SQL endpoint;
- gives you an `answer_template.json` whose top-level shape is one of: an issue register, an economics/closing package, an escalation memo, a transition review, or a position/deviation matrix;
- asks you to compare draft terms to a playbook or policy and return "only JSON".

## The method (do these in order)

### 1. Read the deal record and fix the deal identity
Fetch the deal record first. From it, capture and reuse exactly:
- `deal_id`, `client_name`, `client_side` (buyer or seller), `counterparty_name`, `target_name`, `project_name`;
- `transaction_type` (asset purchase / stock purchase / carveout APA / public-company merger);
- the **headline value** and its components (`upfront_cash`, `stock_value`, `milestone_value`) — this is the base for most dollar math;
- the controlling framework id: `playbook_id` (e.g. a `PB_*` playbook) or `policy_id` (e.g. a `POL_*` committee policy). A deal has one or the other.
- `signing_date`, `meeting_date` (use verbatim, `YYYY-MM-DD`).

**Do not assume records from similarly named projects apply.** Always key off the exact `deal_id` given in the prompt.

### 2. Pull the full data set
Gather every object the workbench exposes for that deal (use the routes documented in the environment access file; for cross-table verification use the read-only SQL endpoint). The objects you will need, in rough priority:

- `draft_terms` — the current draft provisions (each has `term_id`, `category`, `clause_ref`, `basis`, `numeric_value`, `unit`, `draft_value`, `staleness_flag`).
- the framework: `playbook_rules` (preferred/fallback positions, `limit_value`, `risk_default`) OR `policy_thresholds` (policy standard, `threshold_value`/`threshold_unit`, `restricted_flag`, `approval_required`).
- `risk_estimates` — deal-level exposure ranges by category (closing certainty, indemnity leakage, transition disruption), each with `exposure_low`/`exposure_high` and a stable `estimate_id`.
- `benchmarks` — market medians/upper quartiles for fee %, indemnity cap %, survival months.
- `consents` and `material_contracts` — third-party consents and contracts, with `required_for_closing`, `consent_required`, `amount_at_risk`, `annual_revenue`, `risk_rating`.
- `employees` — counts, PTO liability, `service_credit_required`, `warn_risk`.
- `regulatory` — `hsr_required`, `hell_or_high_water_required`, `regulatory_approval`, `threshold_basis`.
- `diligence_findings` — quantified findings (customer concentration, privacy/security, working capital) with stable `finding_id`s.
- `cap_table` — holders, `security_class`, `fully_diluted_pct`, `as_converted_shares`.
- `notes` and `documents` — context (negotiation posture, counterparty rationale).

See `reference/workbench_data_model.md` for the field map.

### 3. Determine what the deliverable must contain
Read the prompt's business task and the template's `required_*_fields` / `required_output_shape` together. The template tells you the exact top-level fields, the allowed enums, the stable ID lists, and the per-object fields. **The template's enum values and literal default lists are usually the expected values** (e.g. a `removed_triggers: ["intervening_event"]` default, or `included_exposure_components: ["closing_certainty","indemnity_leakage"]`) — treat template literals as strong hints, not placeholders.

Identify the issue/term set the prompt asks for:
- Draft terms that deviate from the framework.
- **Absent protective terms the deal data shows are needed** (the prompt tells you to treat draft silence as an issue when the seller/buyer position requires an affirmative provision). Need is shown by the data: a carveout → transition services / IP transition / Section 1060 allocation / transfer-tax split / outside-date extension; required-for-closing consents → consent closing conditions; `hsr_required` → HSR covenant; employee `service_credit_required`/selection rights → employee continuity.
- **Exclude** stale terms (`staleness_flag: "stale"`), in-policy terms, and non-committee/distractor terms when the prompt says to.

### 4. Classify each issue/term
Compare each draft term to the framework rule of the same `category`. Use these statuses (direction is from your client's perspective):

- **in_policy** — draft matches the preferred or fallback position.
- **draft_exceeds_playbook** — draft is more *counterparty-favorable* than the framework's ceiling. Seller examples: indemnity cap above fallback, survival longer than fallback, escrow larger/longer than fallback, a buyer financing condition present. Buyer examples: a seller-friendly carveout the buyer would not grant.
- **draft_below_playbook** — draft is *less protective* than the framework's floor. Seller examples: reverse break-up fee of 0% below the required %. Buyer examples: indemnity cap below fallback, survival shorter than preferred, no materiality scrape, consents excluding material contracts.
- **missing_required_term** — a required protective term is absent (draft silent) and the deal data shows it is needed.
- **out_of_policy** — a non-threshold deviation (e.g. a structural buyer termination right, a fiduciary-out missing a required trigger).

Risk rating usually equals the framework rule's `risk_default` (playbook) or the severity of the policy breach. Recommended action: `add` for missing terms, `revise` for existing-but-deviating terms, `delete` to strike an unwanted provision, `accept` when the draft sits at an acceptable fallback, `escalate` when the framework's required action says to escalate or the risk is high.

See `reference/classification_and_quantification.md` for side-specific direction and worked patterns.

### 5. Quantify every dollar and percentage
- Base dollar amounts on the deal's **headline value** unless the term or framework rule states a different basis (`enterprise value`, `equity value`, `purchase price`). For public-company mergers the equity value is the headline value; for asset/stock purchases the purchase price is the headline value.
- Use the workbench's **stored** values verbatim — do not recompute. Notably, `cap_table.fully_diluted_pct` is a stored field; use the stored percentage and allocate consideration by it (stored × headline), not by recomputing from shares.
- For each numeric term compute: draft amount, preferred amount, fallback amount, and the **delta/shortfall** to fallback and to preferred. Delta to fallback = draft − fallback when the draft exceeds; shortfall = fallback − draft when the draft is below.
- Aggregate exposures from `risk_estimates`: sum the lows and highs of the components the template says to include (typically closing certainty + indemnity leakage; transition disruption is usually excluded for non-carveouts).
- Consent/contract exposure: sum `amount_at_risk` over consents `required_for_closing: yes`; sum `annual_revenue` over material contracts with `consent_required: yes`.
- Employee totals: sum `count` and `pto_liability` across groups.
- Integer dollars everywhere. Percent points to the precision the template states (one or two decimals). Months and counts are integers. Dates `YYYY-MM-DD`.

### 6. Assemble aggregates and routing
Build the summary/aggregate section the template requires: issue counts by status and risk, aggregate quantified exposure (low/high), total negotiation delta, required closing consent count and amount at risk, material-contract revenue conditioned, employee/PTO totals, and any committee routing fields (overall recommendation, committee action, negotiation priority order). Risk counts must be consistent with the per-issue risk ratings you assigned; status counts must be consistent with the per-issue statuses.

### 7. Format the output
- Return **one JSON object** conforming to the template. Include every required top-level field and every required per-object field; omit narrative.
- Use **stable IDs from the workbench** for all `*_ids` fields (`term_id`, `consent_id`, `contract_id`, `employee_id`, `finding_id`, `estimate_id`, `benchmark_id`). Use empty arrays for missing-term `source_term_ids`.
- Use only the template's allowed enum values, exactly as written.
- Sort collections the way the template instructs: by `issue_id`/`redline_id` ascending unless a `priority_order` is requested elsewhere (then order that field by negotiation priority, highest first).
- Include the framework metadata the template asks for (e.g. `schema_name`/`version` when the template's first fields are those — some templates gate on their presence).
- For buyer-side packages, a field named `*_required` typically expects the buyer's **preferred** position (e.g. full materiality scrape), not the fallback.
- `non_blocking_notices`-style fields include **both** notice-only consents and notice-only material contracts.

### 8. Verify before returning
- Re-derive every dollar figure from the headline value and confirm it is an integer.
- Confirm risk/status counts equal the counts in your issue list.
- Confirm every ID you reference exists in the workbench data you pulled.
- Cross-check one or two aggregates with the read-only SQL endpoint (e.g. `SELECT sum(amount_at_risk) FROM consents WHERE deal_id=... AND required_for_closing='yes'`).
- Confirm the issue/term set matches the prompt's scope — no stale, in-policy, or distractor terms included where the prompt said to exclude them.

## References
- `reference/workbench_data_model.md` — field map for all 14 workbench objects.
- `reference/classification_and_quantification.md` — side-specific status direction, common deal-type issue sets, and quantification patterns.
