# API and Evidence Map

## Orientation
- Use `GET /api/manifest` first to confirm the available modules.
- Use `GET /api/summary` next to confirm counts and case coverage.

## Core Records
- `GET /api/employees`: use profile context only; do not treat it as authoritative when a ledger or assignment record conflicts.
- `GET /api/cases` and `GET /api/cases/{case_id}`: use for closeout context, ownership, status, policy refs, and case summary.
- `GET /api/policies` and `GET /api/policies/{policy_id}`: use for source-precedence and readiness rules.
- `GET /api/payroll-ledgers`: use for leave assignments, salary assignments, statuses, and accrual readiness.
- `GET /api/recruitment`: use for candidates, offer register, cost ledger, notice packets, and payroll precheck records.
- `GET /api/documents`: use for required files, required tags, folder readiness, and stored tags.
- `GET /api/messages`: use for notice quality, defects, channel, and draft-vs-final signal.
- `GET /api/audit` and `GET /api/audit/{audit_id}`: use for the exact supporting event, detail text, and exclusion decisions.

## Evidence Rules
- Prefer approved or submitted records over drafts, superseded rows, and stale profile summaries.
- For leave tasks, let the current approved or submitted assignment control the effective policy and balance.
- For payroll tasks, let the current submitted salary assignment control base salary and accrual readiness.
- For case-folder tasks, require every listed file and tag before calling the folder ready.
- For notice tasks, treat missing required content in the message or audit detail as a defect.
- For recruitment tasks, use the committee decision plus the accepted offer register, then sum all cost ledger amounts.

## Audit Scoping
- Use the audit event that directly supports the requested control.
- Put unrelated or adjacent events in the excluded list when the template asks for them.
- Keep `audit_scope` aligned with the evidence set the prompt requests.

## Output Discipline
- Copy enum values exactly from the supplied answer template.
- Keep ID arrays to identifiers only.
- Return JSON only.
