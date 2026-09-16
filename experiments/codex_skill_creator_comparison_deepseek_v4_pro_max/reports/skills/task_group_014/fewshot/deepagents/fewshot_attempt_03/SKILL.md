---
name: northstar-payer-ops
description: "Northstar Health Plan payer operations environment for utilization management, appeals, payment integrity, peer-to-peer review, and margin analysis. Use this skill when working with the Northstar shared payer-operations API at the task-provided base URL. Covers: (1) UM nurse prior-authorization determinations with criteria review, document classification, and authorization issuance, (2) pharmacy coverage-exception appeals with drug-trial evaluation, packet-gap analysis, and manufacturer-assistance screening, (3) payment integrity claim repricing against current benchmarks with line-level correction, (4) peer-to-peer coordinator summaries after completed P2P discussions including adverse-determination deadlines, and (5) UM-finance therapy margin queue analysis with threshold and charge-sensitivity flagging. Every task produces a structured JSON answer with a basis_audit trail."
license: MIT
compatibility: designed for deepagents-code
---

# Northstar Payer Operations

Shared payer-operations environment for Northstar Health Plan. The environment is read-only and provides business APIs plus a SQL query endpoint. All tasks consume environment records and return structured JSON.

## Quick start

Every task shares the same environment access pattern. Use the base URL and credentials provided in the task prompt or `task_context.json` payload:

```
Base URL:         <TASK_ENV_BASE_URL>
SQL endpoint:     POST {base_url}/sql/query
Auth header:      Authorization: Bearer pa-review-token-014
```

**Primary access method: SQL.** Use `POST /sql/query` for most data retrieval. The business REST endpoints are available for direct lookups by ID. See [schema.md](references/schema.md) for the full 19-table schema.

Run SQL queries with the bundled script:

```bash
python3 skill/scripts/query.py "<SQL>" --base-url <BASE_URL> --token pa-review-token-014
```

Or directly with curl:

```bash
curl -s -X POST <BASE_URL>/sql/query \
  -H "Authorization: Bearer pa-review-token-014" \
  -H "Content-Type: application/json" \
  -d '{"sql": "<SQL>"}'
```

## Core workflow

1. **Discover the target**: Identify the case, claim, appeal, or queue ID from the prompt. Cross-reference against `task_context.json` when present.

2. **Query the environment**: Pull all relevant records. Start broad (the target record joined with its dependents), then narrow with WHERE clauses.

3. **Evaluate against criteria**: When a policy applies, match `policy_criteria` against `case_criteria` results and supporting `document_facts`. Check `is_current` on documents to separate active evidence from stale.

4. **Apply the source-precedence rule**: Every task has a `source_precedence` rule that controls how conflicting or overlapping records are resolved. See [precedence.md](references/precedence.md).

5. **Build the answer**: Fill the template fields from `answer_template.json`. Currency values rounded to 2 decimal places. Ratios to 4 decimal places. Null for absent modifiers, not empty string. ISO 8601 dates. Lists ordered as specified by the template.

6. **Construct the basis audit**: Every answer ends with a `basis_audit` containing the source-precedence rule, the ordered record precedence trail, the controlling record IDs, and exception/gap record IDs. See [precedence.md](references/precedence.md).

## Task domains

The environment supports five task domains, each with specific data models and evaluation patterns. Detailed workflows are in [workflows.md](references/workflows.md).

| Domain | Typical Entry | Key Tables | Precedence Rule |
|---|---|---|---|
| UM nurse prior-auth | case_id | cases, request_lines, documents, document_facts, policy_criteria, case_criteria, members, plans, authorizations | current_clinical_records_over_stale_export |
| Pharmacy appeals | appeal_id | appeals, cases, drug_trials, assistance_screen, documents, policy_criteria | payer_appeal_before_manufacturer_assistance |
| Payment integrity | claim_id | claims, claim_lines, payment_benchmarks, plans | effective_benchmark_by_plan_modifier_and_date |
| Peer-to-peer | p2p_event_id | p2p_events, cases, request_lines, documents, policy_criteria | new_patient_specific_p2p_information |
| Margin queue | queue_id | service_margin | margin_threshold_then_charge_sensitivity |

## Policies

Five active policies cover the task domains. See [policies.md](references/policies.md) for policy-to-criterion mappings.

| Policy ID | Name | Domains |
|---|---|---|
| POL-PT-LUMBAR-2026 | Lumbar Physical Therapy Medical Necessity | UM nurse prior-auth |
| POL-DRUG-EXC-2026 | Specialty Drug Coverage Exception Appeal | Pharmacy appeals |
| POL-PET-MPI-2026 | PET Myocardial Perfusion Imaging Medical Necessity | P2P |
| POL-CLAIM-RATE-2026 | Outpatient Imaging and Surgery Payment Benchmark | Payment integrity |
| POL-ST-PEDS-2026 | Pediatric Speech Therapy Prior Authorization | (not used in train tasks) |

## Numeric conventions

- **Currency** (USD): JSON number rounded to 2 decimal places.
- **Ratios** (e.g. revenue_to_cost_ratio): JSON number rounded to 4 decimal places.
- **Units** (e.g. approved_units, visits): integer.
- **Null modifier**: Use `null`, not empty string.
- **Dates**: ISO 8601 `YYYY-MM-DD`. Months as `YYYY-MM`.

## Reference files

- [schema.md](references/schema.md) — Full database schema with all 19 tables, columns, types, and keys.
- [precedence.md](references/precedence.md) — Source-precedence rules and the basis_audit construction pattern.
- [policies.md](references/policies.md) — Policy framework with criteria-key to criterion-ID mappings.
- [workflows.md](references/workflows.md) — Step-by-step workflows for each of the five task domains.
