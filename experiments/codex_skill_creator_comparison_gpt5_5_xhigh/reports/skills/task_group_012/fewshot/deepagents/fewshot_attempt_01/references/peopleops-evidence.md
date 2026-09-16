# PeopleOps Evidence Rules

## API surface

- `/api/manifest`: module map and file counts.
- `/api/summary`: case/status overview.
- `/api/cases` and `/api/cases/{case_id}`: case context and linked employee or opening IDs.
- `/api/employees`: employee profile summary.
- `/api/policies` and `/api/policies/{policy_id}`: policy language.
- `/api/payroll-ledgers`: leave and payroll assignment records.
- `/api/recruitment`: opening, candidates, offer register, cost ledger, notice packets, and precheck records.
- `/api/documents`: folder files, required files, tags, and readiness.
- `/api/messages`: notice packets and defect lists.
- `/api/audit` and `/api/audit/{audit_id}`: authoritative QA findings and scope anchors.

## Source selection

- Leave: use the latest approved or submitted assignment for the period; ignore draft, voided, obsolete, or stale profile-summary values.
- Payroll: use the current submitted salary assignment; ignore draft planning assignments and superseded rows.
- Recruiting: use the selected candidate with an accepted offer; draft prechecks do not satisfy the handoff gate.
- Folder and notice cases: folder readiness requires every required file and tag; a notice is defective when the required elements are missing.
- Audit: use the event whose detail directly states the conclusion; exclude adjacent events outside the requested scope.

## Scope discipline

- Use only evidence that belongs to the requested module.
- When a bundle contains related events from other modules, keep them out of the decision unless the prompt explicitly asks for them.
- If the prompt asks for supporting or excluded audit event IDs, include only direct supporting events and list the rest as excluded.

## Template discipline

- Fill only the keys in the provided template.
- Copy enum values exactly as written.
- Preserve types exactly.
- For ID arrays, return IDs only. Do not add names, labels, or prose.

## Recommended flow

1. Identify the target case, employee, opening, or candidate from the prompt.
2. Pull the smallest evidence bundle that covers the requested decision.
3. Determine the authoritative record and list the excluded records.
4. Map the findings to the template fields.
5. Emit JSON only.

