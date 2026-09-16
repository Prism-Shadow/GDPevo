---
name: peopleops-console-controls
description: Solve PeopleOps Console verification tasks that ask for final JSON from employee, case, leave, payroll, recruitment, document, message, policy, or audit records. Use when the prompt mentions PeopleOps Console, onboarding closeout, remote-work exception review, leave source precedence, payroll assignment readiness, recruitment reconciliation, folder readiness, formal notice quality, or normalized business labels from an answer template.
---

# PeopleOps Console Controls

## Overview

Use this skill to resolve PeopleOps verification tasks from the staged environment and return JSON that matches the provided answer template exactly.

## Workflow

1. Read the prompt, the answer template, and the target entity IDs.
2. Collect evidence from the smallest authoritative record set.
3. Apply source precedence and exclusion rules.
4. Populate only the template keys.
5. Return JSON only.

## Evidence Collection

- Prefer the structured API when `TASK_ENV_BASE_URL` or `environment_access.md` is available.
- Use [`scripts/collect_peopleops_evidence.py`](scripts/collect_peopleops_evidence.py) to pull the manifest, summary, and relevant records for the requested IDs.
- Use the browser UI only when the prompt requires it or an API field is missing.

### Pick the right source set

- Leave precedence: employee record, leave ledger or assignment history, policy document, case detail, audit event.
- Payroll readiness: payroll ledger, policy document, case detail, audit event.
- Recruitment reconciliation: recruitment workspace, offer register, cost ledger, notice packets, messages, case detail, audit.
- Folder and notice checks: case detail, documents, messages, audit, policy document.

## Decision Rules

- Treat approved or submitted current-period assignments as authoritative.
- Ignore draft, superseded, voided, obsolete, or placeholder records unless the prompt asks for exclusions.
- Use the profile summary only when no authoritative assignment exists.
- Use submitted salary assignments for payroll source decisions.
- Ignore draft payroll prechecks and draft salary assignments.
- Treat folder readiness as true only when every required file and required tag is present.
- Treat notice quality as defective when the notice packet, message body, or audit event reports a missing required element.
- Sum all ledger line items for recruitment cost totals.
- For recruitment tasks, accept only the selected candidate with an accepted offer; keep waitlisted and rejected candidate IDs separate.
- For audit fields, include only events that support the requested scope and list unrelated adjacent events in the excluded array when the prompt asks for exclusions.
- Derive dates from monthly periods as `YYYY-MM-01` only when the source record does not provide a more specific effective date.

## Normalized Labels

- Use the exact enum strings from the current template for source, scope, gate, control, and remediation fields.
- Map approval sufficiency to `approval_sufficient_when_records_clean` only when the record set is clean.
- Map any folder or notice defect to `approval_not_sufficient_when_folder_or_notice_defective`.
- Map final closeout to `approve_closeout`, `hold_for_folder_and_notice_defects`, or `ready_with_monitoring` according to the template.
- Populate `excluded_*` arrays with IDs of drafts, superseded records, stale summaries, placeholder records, or adjacent audit events that must not drive the decision.

## Output

- Return one JSON object.
- Match the answer template keys exactly.
- Do not include markdown, prose, or partial reasoning.
