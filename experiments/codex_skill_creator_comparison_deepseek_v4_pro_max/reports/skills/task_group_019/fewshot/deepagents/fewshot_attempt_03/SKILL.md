---
name: licensing-review
description: "State licensing board batch review for contractor eligibility, restricted liquor license staff packages, and alcohol renewal manual-review queues. Use this skill when the task involves: (1) batch eligibility determinations (APPROVE/HOLD/DENY) for contractor or professional license applications, (2) preparing a restricted liquor license staff package with risk coverage, verification gaps, obligations, 90-day monitoring plan, and escalation triggers, (3) building a ranked manual-review queue for alcohol license renewals based on violation recency and severity, or (4) any prompt that mentions licensing examiners, contractor applications, liquor license transfers, or renewal screening."
---

# Licensing Review

## Workflow Decision Tree

Identify the task type from the prompt:

- **Contractor batch review**: prompt lists application IDs like `C-*`, references `contractor/applications`, `contractor/bonds`, `contractor/insurance`, `contractor/violations`, `contractor/license-history`, `contractor/inspections`, `contractor/correspondence`, and expects an `application_decisions` array with APPROVE/HOLD/DENY per application. See [contractor_review.md](references/contractor_review.md).

- **Liquor license staff package**: prompt has a single application ID like `L-*`, references `liquor/applications`, `liquor/settlements`, `liquor/privileges`, `liquor/incidents`, `liquor/site-evidence`, and expects `recommended_posture`, `covered_risk_codes`, `verification_gap_codes`, `standard_obligation_codes`, `location_specific_control_codes`, `first_90_day_plan`, `escalation_trigger_codes`. See [liquor_license_review.md](references/liquor_license_review.md).

- **Alcohol renewal queue**: prompt lists license IDs like `AL-*`, references `alcohol/licensees`, `alcohol/violations`, `renewal/rules`, and expects a ranked `queue` and `summary`. See [alcohol_renewal_queue.md](references/alcohol_renewal_queue.md).

## Common Rules for All Workflows

### Environment Setup

The task environment base URL is `http://task-env:9019`. Authentication for `POST /api/sql` uses header `X-Task-Token` with the value from the prompt or environment instructions. No other endpoints require authentication.

Available endpoints vary by workflow:

| Workflow | GET endpoints | SQL access |
|---|---|---|
| Contractor | `/api/policies`, `/api/contractor/*` | `POST /api/sql` |
| Liquor | `/api/policies`, `/api/liquor/*` | Usually `POST /api/sql` (check prompt) |
| Alcohol renewal | `/api/alcohol/*`, `/api/renewal/*` | `POST /api/sql` |

Always read policies first via `GET /api/policies`.

### Fetching Records

Fetch all relevant records before making determinations. Use all available `GET` endpoints for the workflow. Use `POST /api/sql` for additional queries when the prompt authorizes it.

### Output Format

Return only valid JSON matching the answer template provided in `input/payloads/answer_template.json`. Never include markdown, prose, citations, or keys not in the template. Order arrays as specified in the template (typically ascending by ID or code). Use empty arrays when no codes apply. Do not invent codes not in the template's allowed values.

### Date Handling

All dates use `YYYY-MM-DD`. When a review date is specified in the prompt, use it against financial coverage records (bonds, insurance). A bond or insurance policy is current if its effective dates cover the review date and it has not been cancelled.

### Policy Impact Assessment

Compare the application against the *current* policy baseline. An application is `policy_impacted: true` when a deficiency or material review flag exists under the current policy that would not have existed under a prior baseline. Check the policies endpoint for effective dates and threshold changes.
