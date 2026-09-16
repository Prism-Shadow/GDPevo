# Pharmacy Coverage Appeal and Assistance Intake

## Overview

Process a coverage-exception appeal and manufacturer assistance intake screen for a
pharmacy drug. The output matches the pharmacy appeals answer template with required
fields: `case_id`, `appeal_id`, `drug`, `appeal_path`, `expedited`, `appeal_deadline`,
`owner`, `documented_failures`, `undocumented_or_insufficient_failures`,
`criteria_results`, `required_packet_items`, `missing_packet_items`, `assistance`,
`next_action`, `basis_audit`.

## Workflow

### 1. Gather appeal and case context

Pull the appeal record and associated case from the environment. Identify:
- The appeal ID and case ID
- The drug (one of: Vraylar, Dupixent, Humira, Ozempic, Rinvoq, Skyrizi)
- The appeal path and whether expedited
- The denial that triggered the appeal

Use REST `GET /api/appeals` or SQL to retrieve appeal records. Cross-reference with
`GET /api/cases/{case_id}`.

### 2. Determine appeal path and deadline

| Scenario | appeal_path | expedited | Deadline Rule |
|----------|------------|-----------|---------------|
| Standard coverage appeal | `standard_internal` | `false` | 30 calendar days from filing |
| Urgent/expedited appeal | `expedited_internal` | `true` | 72 hours from filing |
| External review eligible | `external_review` | N/A | Per state/federal rules |
| Not eligible (no valid denial) | `not_eligible` | `false` | None |

Date arithmetic: For a standard internal appeal filed on date D, the deadline is
D + 30 calendar days. The `appeal_deadline` field must be ISO 8601 YYYY-MM-DD.

### 3. Classify medication failures

Review the member's medication history (formulary alternatives tried and failed).
Split into two lists:

- **documented_failures**: Medications with clear trial-and-failure evidence in the
  record (fill history, prescriber notes, pharmacy claims). Lowercase medication
  names, alphabetical order.
- **undocumented_or_insufficient_failures**: Medications mentioned or required by
  policy but lacking adequate documentation. Lowercase medication names,
  alphabetical order.

Pull drug trial records via SQL. Each trial typically has a document ID, medication
name, and trial outcome.

### 4. Evaluate drug criteria

Four required criterion keys:

| Criterion ID | What It Checks |
|-------------|----------------|
| `DRUG-AUTH` | Prior authorization on file |
| `DRUG-DENIAL` | Valid denial notice exists |
| `DRUG-RATIONALE` | Prescriber rationale supports medical necessity |
| `DRUG-FAILURES` | Required formulary failures documented |

Values: `met`, `not_met`, `partial`, `unclear`, `not_applicable`.

`DRUG-FAILURES` is `partial` when some but not all required failures are documented.

### 5. Build the packet analysis

**required_packet_items**: All items needed (payer appeal items first, then
assistance items). Order: payer appeal evidence before manufacturer assistance
requirements.

**missing_packet_items**: Items not yet submitted or insufficient. Order:
appeal evidence gaps before assistance information gaps.

Common packet item types:
- `denial_notice` - The adverse determination letter
- `member_authorization` - Signed member consent for appeal
- `prescriber_rationale` - Clinical justification from prescriber
- `formulary_failure_evidence` - Proof of failed alternatives
- `lurasidone_fill_record` - Specific fill history for a required alternative
- `pharmacy_claim_history` - Full pharmacy claims
- `diagnosis_confirmation` - Confirmed diagnosis documentation
- `expedited_risk_attestation` - For expedited appeals only
- `household_income_proof` - For manufacturer assistance programs only

### 6. Screen manufacturer assistance

Each drug maps to a specific assistance program:

| Drug | Program |
|------|---------|
| Vraylar | Vraylar Connect |
| Dupixent | Dupixent MyWay |
| Humira | Humira Complete |
| Other | `not_applicable` |

`assistance.status` is one of:
- `eligible_ready` - All documentation present, ready to submit
- `eligible_missing_information` - Eligible but missing required fields
- `not_eligible` - Does not meet program requirements
- `not_applicable` - No applicable program

`assistance.missing_fields` lists missing field IDs in alphabetical order.

### 7. Determine next action

| Conditions | next_action |
|-----------|-------------|
| Missing packet items or missing assistance fields | `request_more_information` |
| All evidence complete, non-expedited | `file_appeal` |
| Expedited appeal missing only income proof | `complete_expedited_appeal_and_request_income_proof` |
| Assistance ready, appeal complete | `submit_assistance_application` |
| Not eligible for appeal | `close_not_eligible` |

### 8. Construct the basis_audit

Use `payer_appeal_before_manufacturer_assistance`:
- `controlling_record_ids`: appeal record and supporting trial evidence that directly
  supports the result
- `exception_record_ids`: insufficient trial records and missing-field identifiers
- `precedence_record_order`: appeal record first, then trial evidence (documented
  before insufficient), then missing-field identifiers

## Key Patterns from Training

- When one formulary alternative is documented and another is not, `DRUG-FAILURES`
  is `partial`.
- Missing fields appear in both `missing_packet_items` and
  `assistance.missing_fields` when they affect both workflows.
- The `precedence_record_order` includes both formal environment record IDs and
  gap identifiers (like `household_income_proof`) when those gaps are
  determinative.
