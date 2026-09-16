---
name: licensing-review
description: State licensing board review workflows for contractor applications, restricted liquor license staff packages, and alcohol renewal queues. Use when evaluating licensing eligibility, building manual review queues, or preparing structured staff packages from a licensing task environment API. Covers contractor batch review (applications, bonds, insurance, violations, inspections, correspondence, license history), restricted liquor license review (applications, settlements, privileges, incidents, site evidence), and alcohol renewal screening (licensees, violations, renewal rules). Trigger when the prompt asks to review, evaluate, or screen licensing applications or renewals against a task environment API.
---

# Licensing Review

## Overview

This skill supports three licensing review workflows against a shared task-environment API:

1. **Contractor batch eligibility review** — Evaluate contractor applications against bonds, insurance, endorsements, experience, violations, inspections, and correspondence.
2. **Restricted liquor license staff package** — Prepare a structured review package for a liquor license application covering risk coverage, verification gaps, obligations, a 90-day monitoring plan, and escalation triggers.
3. **Alcohol renewal manual review queue** — Build a ranked queue of licensees for manual renewal screening, matching violations by license identity, filtering by boundary date, and assigning risk tiers and next-step labels.

Every task includes an `answer_template.json` that defines the exact output schema, allowed enum values, and ordering constraints. The template is the live schema for that task — use it as the structural contract for all output.

## General Workflow

1. Read the prompt to identify the domain and target applications or licenses.
2. Read the task's `input/payloads/answer_template.json` to lock in the exact output schema and allowed value sets.
3. Fetch the current policy baseline from `GET /api/policies`. Policies define financial minimums, endorsement requirements, experience thresholds, and other standards that may differ from a prior baseline.
4. Fetch domain-specific records using the endpoints listed in the prompt and cataloged below.
5. Apply the business rules in the relevant domain reference file to map raw data into structured decisions.
6. Produce JSON output that strictly conforms to the answer template. Use empty arrays when no codes apply. Sort list fields as specified by the template.

## API Endpoints and SQL Access

See [references/api_endpoints.md](references/api_endpoints.md) for the full endpoint catalog, including the SQL access pattern.

## Domain-Specific Guidance

- **Contractor batch review**: [references/contractor_review.md](references/contractor_review.md) — bond/insurance validation, endorsement checks, experience verification, violation severity classification, inspection analysis, correspondence tracking, risk tiering, and policy impact determination.
- **Restricted liquor license review**: [references/liquor_review.md](references/liquor_review.md) — same-premises basis, risk coverage assessment, verification gap identification, standard vs. location-specific obligation separation, 90-day plan construction, and escalation trigger selection.
- **Alcohol renewal queue**: [references/alcohol_renewal.md](references/alcohol_renewal.md) — licensee-to-violation matching by license number and address, boundary-date filtering, match confidence classification, ranking by recency and severity, next-step label assignment, and summary aggregation.

## Policy Evaluation

See [references/policy_evaluation.md](references/policy_evaluation.md) for the cross-domain method: how to read the policy baseline, compare current requirements against a prior baseline, and determine whether a policy change creates a deficiency that would not have applied under the prior standard.
