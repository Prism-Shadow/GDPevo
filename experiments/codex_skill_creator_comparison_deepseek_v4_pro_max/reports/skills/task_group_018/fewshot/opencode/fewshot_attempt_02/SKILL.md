---
name: court-clerk
description: Prepare court clerk closeout packages, sentencing packets, post-disposition financial and supervision packets, traffic violation closeouts, and disposition register entries. Use this skill whenever the user asks to reconcile court hearing notes, audit memos, finance queue extracts, petition summaries, or sentencing intake sheets with a Court Operations Portal API and produce structured JSON answers. Do not attempt court reconciliation work without consulting this skill — the domain rules and resolution hierarchy are non-obvious.
---

# Court Clerk Closeout Package Preparation

This skill covers the end-to-end workflow for preparing structured court clerk
closeout packages from mixed local materials and a Court Operations Portal API.

## Prerequisites

The target workspace is expected to have:

- A Court Operations Portal at a base URL communicated in the task prompt.
  The portal exposes these endpoints via GET:
  /api/jurisdictions, /api/cases, /api/charges, /api/docket-entries,
  /api/citations, /api/fee-schedules, /api/payment-policies, /api/forms,
  /api/financial-petitions, /api/search.
- Local payloads (hearing notes, audit memos, finance extracts, petition
  summaries, form excerpts, sentencing intake sheets, worksheets) in an
  input/payloads/ directory.
- An answer template at input/payloads/answer_template.json that defines the
  output schema, enums, ordering rules, and field-level constraints.

## Workflow

Execute these phases in order. All decisions flow from the resolution hierarchy
in references/resolution-rules.md.

### Phase 1 — Orient

1. **Read the answer template first.** It defines the exact output shape,
   required top-level keys, enums, sort order, currency precision, and date
   format. Every field you produce must honor its constraints. If the template
   uses an enum, your output must use only the literal enum values listed; never
   substitute prose descriptions.

2. **Read every local payload.** Understand what each document contributes and
   where it may conflict with others:
   - Hearing/bench notes: authoritative for what happened in open court
   - Audit/clerk memos: flag specific conflicts to resolve
   - Finance queue extracts: carry-forward values that may be stale
   - Sentencing intake sheets: control the conviction and sentence posture
   - Petition summaries: financial counter data and budget information
   - Form excerpts: field-entry guidance and placeholder rules
   - Worksheets/spreadsheets: draft figures needing verification

3. **Query the portal for the target jurisdiction and every target case
   identifier.** Use /api/search for quick lookups and the specific endpoints
   (/api/cases, /api/charges, /api/docket-entries) for detail. Also query
   fee schedules, payment policies, and forms as needed.

### Phase 2 — Resolve

For each target matter, reconcile the local materials against the portal.

1. **Resolve identity questions.** The CMS portal record is authoritative for
   defendant name, DOB, and counsel type. When the portal shows a different
   spelling or birth date from a queued finance record, use the portal value.
   When the portal DOB field is genuinely blank and no local payload supplies
   it, use the placeholder "TBD from case file" and flag it for verification.

2. **Resolve counsel classification.** The portal counsel_type field is
   authoritative. Appointed private counsel paid by the county is
   appointed_private, not public_defender. The public defender user fee
   applies only when counsel_type is public_defender.

3. **Resolve disposition and status.** The hearing notes are authoritative for
   what happened in open court — plea, finding, sentence, and the judge's
   on-the-record characterizations. When the judge says a sentence is
   "top-of-range" and not a departure, that overrides any legacy departure label
   in a worksheet. When no final signed order exists, the case is not disposed;
   hold it out of the register.

4. **Resolve charge information.** The hearing notes control what count was
   actually adjudicated (e.g., an amended charge replaces the original). The
   portal charge record supplies the precise offense code, statute, and
   severity. When a charge was amended away from a controlled-substance count to
   a non-drug count, the lab/drug assessment does not apply.

5. **Resolve fee amounts.** Always use the **current** fee schedule from the
   portal, not stale amounts from older worksheets or 2023 references. Check the
   effective_date and end_date fields on fee schedule records — a record
   with a past end_date is archival only. Fees that are not supported by the
   current schedule or a court order should be excluded.

6. **Document every conflict** in the audit findings section of the output.
   Record the case number, the issue type, the conflicted value, the corrected
   value, and the resolution source.

Consult references/resolution-rules.md for the full evidence hierarchy and
examples.

### Phase 3 — Build

1. **Follow the answer template exactly.** Populate every required key in the
   order the template specifies. Use enum values verbatim.

2. **Compute financials.** Sum fines, court costs, assessments, and user fees
   per case, then aggregate across cases. Only cases with a "post" fee status
   contribute to register totals. Held or excluded cases contribute zero.

3. **Handle excluded items.** List every charge or fee that appeared in local
   materials but should not be posted. For each, state which matters it applies
   to and the reason code. The detailed exclusion rules are in
   references/exclusion-rules.md.

4. **Handle placeholders.** When a form field is required but no source supplies
   the value (e.g., driver license number, SSN, probation officer name, address,
   phone), use the literal string "TBD from case file". Never invent
   identifiers or contact details. The placeholder rules are in
   references/placeholder-rules.md.

5. **Payment plan arithmetic** — see references/payment-plan-math.md for the
   formulas.

6. **Sort every list** as directed by the template (typically by case number or
   citation number ascending). Sort excluded items and placeholder fields as
   directed.

7. **Format output.** All currency values must be numbers with two decimal
   places. All dates must be ISO YYYY-MM-DD. Date-times use
   YYYY-MM-DDTHH:MM:SS. Return the complete JSON object; do not wrap it in
   markdown.

### Phase 4 — Verify

Before delivering the answer:

- Every required top-level key from the template is present.
- Every enum value matches the template's allowed values literally.
- Sort order matches the template's ordering rules for every array.
- Currency values are numeric with two decimal places.
- Dates are ISO format.
- No invented identifiers or contact details appear; all unreachable values are
  "TBD from case file".
- Register totals sum correctly from the individual case fee entries (held cases
  contribute zero).
- Audit findings are documented at the right granularity: one finding per
  distinct issue per case.

## Reference Files

- [references/resolution-rules.md](references/resolution-rules.md) — evidence hierarchy and conflict resolution
- [references/exclusion-rules.md](references/exclusion-rules.md) — when to exclude fees and charges
- [references/placeholder-rules.md](references/placeholder-rules.md) — placeholder handling for missing data
- [references/payment-plan-math.md](references/payment-plan-math.md) — installment arithmetic
- [references/portal-endpoints.md](references/portal-endpoints.md) — API query patterns
