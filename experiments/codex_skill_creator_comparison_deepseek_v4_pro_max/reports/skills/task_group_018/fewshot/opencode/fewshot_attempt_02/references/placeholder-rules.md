# Placeholder Handling for Missing Data

When a required form field cannot be completed from the available materials
(local payloads + portal records), use the literal placeholder string
`"TBD from case file"`. Never invent identifiers, addresses, phone numbers,
contact details, or office assignments.

## When to Use Placeholders

Use `"TBD from case file"` for these categories:

- **Missing identifiers**: SSN, driver license number, external party ID
  (when genuinely absent from all sources).
- **Missing contact information**: mailing address, residence address,
  phone number, email.
- **Missing office details**: probation officer name, probation office
  location (when the sentencing intake or case file does not supply them).
- **Missing party details**: attorney name, judge name (when the template
  requires it but no source supplies it).

## When NOT to Use Placeholders

- The portal record supplies the value — use it.
- A local payload (sentencing intake, petition summary, hearing note)
  supplies the value — use it after confirming against the portal.
- The DOB is available from the portal or a confirmed local source — use it.
- The defendant name is available from the portal or hearing notes — use it.

## DOB-Specific Rule

When the DOB is genuinely blank in both the portal and all local materials,
use `"TBD from case file"` and flag it as a missing-identity audit item.
This is distinct from a conflict between two known DOBs — in that case,
resolve to the portal value.

## Placeholder Field Tracking

When the answer template includes a placeholder_fields or placeholder_cases
section, populate it with an entry for each field that received the
placeholder, sorted as directed (typically by case number then field name).
Each entry should include:

- The field path (e.g. `"cc1375.probation_officer"`, `"defendant.ssn"`)
- The placeholder value (`"TBD from case file"`)
- The reason code (missing_identifier, missing_contact, missing_office_detail,
  missing_party_detail)

## Form-Level Placeholder Rules

When a portal form record has a placeholder_instruction field, follow it
literally. Common instructions:

- "Unknown SSN, address, phone, and license number must be TBD from case file."
- "Do not invent driver license number; use TBD from case file."
- "Use case file value for unknown identifiers; do not resolve with assumptions."
- "Leave unavailable address or phone as blank/TBD per citation file."
