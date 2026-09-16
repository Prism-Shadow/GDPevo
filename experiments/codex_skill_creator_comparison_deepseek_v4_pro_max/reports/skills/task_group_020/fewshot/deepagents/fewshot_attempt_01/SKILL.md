---
name: ma-deal-workbench
description: Work with the M&A deal workbench API to produce structured deal-analysis deliverables for M&A transactions. Use when the task requires gathering deal records, draft terms, playbook rules, policy thresholds, and supporting data (consents, employees, regulatory, risk estimates, benchmarks, material contracts, diligence findings) from the workbench and producing a structured JSON deliverable that compares draft positions against playbook or policy requirements. Triggers on tasks involving SPA/APA issue registers, closing packages, committee escalation memos, transition reviews, deviation matrices, or any M&A deal-review output that references the workbench API.
---

# M&A Deal Workbench

Use the running M&A deal workbench to gather deal records, compare draft terms against playbook rules or policy thresholds, and produce structured JSON deliverables.

## Core Workflow

1. **Read the answer template** — The task provides an `answer_template.json` under `input/payloads/`. Parse it first. Every enum, field shape, and required output structure is defined there.
2. **Fetch the deal record** — `GET /api/deals/<deal_id>` gives headline purchase price, parties, structure, and signing date.
3. **Fetch the draft terms** — `GET /api/deals/<deal_id>/terms` gives every current draft term with `term_id`, `clause_ref`, `category`, and values.
4. **Fetch the governing rules** — `GET /api/playbooks/<playbook_id>/rules` for playbook positions or `GET /api/policies/<policy_id>/thresholds` for policy cutoffs.
5. **Fetch supporting records** — As the task requires: consents, employees, regulatory, risk estimates, benchmarks, material contracts, diligence findings, cap table, documents, notes.
6. **Compare draft against rules** — See [comparison_methodology.md](references/comparison_methodology.md) for classification.
7. **Compute numeric values** — See [output_conventions.md](references/output_conventions.md) for currency, percent, month, and delta rules.
8. **Produce JSON** — Return only the JSON object conforming to the answer template. No markdown fences, no prose outside the JSON.

## Reference Files

- [API endpoints and stable identifiers](references/api_endpoints.md) — Full endpoint catalog, request patterns, and ID conventions.
- [Comparison methodology](references/comparison_methodology.md) — How to classify each draft-vs.-rule mismatch, assign risk ratings, determine priority order, and select recommended actions.
- [Output conventions](references/output_conventions.md) — Currency rounding, percentage precision, null handling, enum compliance, sorting, and field completeness rules.

Load the relevant reference when the task calls for detailed guidance on a specific aspect. The API reference is useful at the start of every task; the comparison methodology is needed when classifying issues; output conventions are needed before final serialization.

## Key Principles

**Dollar amounts always derive from the headline purchase price** unless a source record explicitly states a different basis. Multiply `headline_value × percent / 100`.

**Every record ID from the workbench is stable.** Use them verbatim. Never invent or mangle identifiers. When a term is missing from the draft, `source_term_ids` is `[]`.

**Missing terms are issues.** When the playbook or policy requires a provision but no corresponding draft term exists, classify as `missing_required_term` with an empty `source_term_ids` array.

**Ignore distractor terms.** A term that falls within policy, is stale, or is not relevant to the task scope should not appear in the output.

**Match the template exactly.** Every field listed in the answer template's required output shape must appear in the output, even with `null` values. Every string field with enumerated choices must use only values from the template.
