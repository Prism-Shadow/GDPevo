# Output Data Conventions

## Currency

All dollar amounts are integer USD. No cents, no commas, no currency symbols in numeric values. Round to the nearest dollar using standard rounding (0.5 rounds up).

## Percentages

The output template dictates precision:

- **Percent points** (rates, caps, escrow percentages): two decimal places (e.g., 14.00).
- **Holder fully-diluted percentages** (cap table): four decimal places (e.g., 0.1850).
- Always use the precision the template or schema specifies.

## Months

Integer months. Never fractional.

## Dates

ISO 8601 `YYYY-MM-DD` format.

## Dollar Calculations

All percentage-based dollar amounts use the headline purchase price from the deal record (`/api/deals/{deal_id}`) as the basis, unless a source record explicitly states a different basis.

Formula: `amount = headline_value * (percent / 100.0)`, rounded to integer.

## Delta Calculations

- **Excess** (draft exceeds playbook): `delta = draft_value - fallback_value`
- **Shortfall** (draft below playbook): `delta = fallback_value - draft_value`
- **Missing term**: compute `delta_to_fallback` from the playbook fallback and zero (or null as appropriate).

## Quantified Exposure

- `total_quantified_exposure_low_dollars`: sum of all risk-estimate low values for relevant issues.
- `total_quantified_exposure_high_dollars`: sum of all risk-estimate high values for relevant issues.
- `total_negotiation_delta_dollars`: sum of all delta_to_fallback_dollars across issues.

## Source IDs

Every identifier in output must come directly from workbench API responses. Use stable prefixes:

- Terms: `TERM_{project}_{nn}`
- Consents: `CNS_{project}_{nn}`
- Material contracts: `MAT_{project}_{nn}`
- Employees: `EMP_{project}_{nn}`
- Risk estimates: `RSK_{project}_{nn}`
- Diligence findings: `FND_{project}_{nn}`
- Documents: `DOC_{project}_{nn}`

Never invent IDs or use IDs from other projects.

## Enum Values

All status, rating, and action fields must use exactly the enum values the answer template defines. Do not substitute synonyms or invent new values.

## Null vs. Zero

- Use `null` (JSON null) for fields where the data is genuinely absent or not applicable.
- Use `0` (integer zero) for fields where the computed amount resolves to zero.
- Use `[]` (empty array) for required array fields with no entries.
