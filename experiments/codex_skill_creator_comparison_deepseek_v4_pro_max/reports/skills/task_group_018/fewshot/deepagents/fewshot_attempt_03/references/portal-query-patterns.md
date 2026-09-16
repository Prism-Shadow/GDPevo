# Portal Query Patterns

## General Principles

The Court Operations Portal is a REST API at the base URL provided in the task prompt. All endpoints are GET-only. Responses are JSON.

Query the portal for every case, citation, or petition mentioned in the task. Cross-reference portal data with local materials to resolve conflicts and fill answer template fields.

## Query by Docket Type

### Criminal Sentencing Closeout (Redwood County, Union County patterns)

For each target case number, query in this order:

1. `GET /api/cases?case_number=<case>` — defendant identity, status, counsel of record, disposition metadata. Use the portal's DOB and party name as the authority when hearing notes are silent and no audit memo conflicts.

2. `GET /api/charges?case_number=<case>` — each count's offense code, statute, plea, and charge disposition. Use to confirm the conviction count and detect amendments (e.g., a controlled-substance count amended to misdemeanor theft).

3. `GET /api/docket-entries?case_number=<case>` — entry history and signed-order status. A case with no signed sentencing order cannot be disposed, regardless of what a draft worksheet shows.

4. `GET /api/fee-schedules?jurisdiction=<jurisdiction_code>` — current fee amounts for court costs, drug assessments, crime lab fees, and any jurisdiction-specific assessments. The jurisdiction code is usually available from the portal cases response or the finance queue extract (e.g., `AR-RC` for Redwood County, AR).

5. `GET /api/payment-policies?jurisdiction=<jurisdiction_code>` — not always needed for pure criminal closeouts, but check when the task references payment-policy decisions.

6. `GET /api/search?q=<defendant_name>` — use when identity is in question (DOB mismatch, name spelling discrepancy).

### Traffic Violation Closeout (Oregon 22nd JD pattern)

For each citation number:

1. `GET /api/citations?citation_number=<citation>` — citation record, defendant, violation code, officer, event date. Use to verify the citation exists and matches the hearing notes.

2. `GET /api/fee-schedules?jurisdiction=<jurisdiction_code>` — the current fine tier for the violation. The schedule provides the standard fine and any county surcharge. Do not use stale schedules or statutory-maximum notes when a current tiered schedule exists.

3. `GET /api/payment-policies?jurisdiction=<jurisdiction_code>` — installment plan rules: whether extended payment plans are allowed, minimum/maximum monthly amounts, down-payment requirements, account-fee treatment.

4. `GET /api/forms?form_id=<form_id>` — the local payment-plan form metadata. Verify the form ID and field labels from the portal against any local form excerpt.

5. `GET /api/search?q=<citation or defendant>` — cross-check for stale references or conflicting records.

### Post-Sentencing Field Packet (Gloucester County VA pattern)

For the target case and petition:

1. `GET /api/cases?case_number=<case>` — defendant identity, conviction date, offense, sentence terms, counsel, case status.

2. `GET /api/charges?case_number=<case>` — charge details, plea, disposition for each count.

3. `GET /api/docket-entries?case_number=<case>` — verify the sentencing order was entered.

4. `GET /api/forms?form_id=VA_CC1375` — CC-1375 probation referral form metadata and required fields.

5. `GET /api/forms?form_id=VA_CC1379` — CC-1379 license suspension and installment order form metadata and required fields.

6. `GET /api/payment-policies?jurisdiction=<jurisdiction_code>` — installment rules, policy band (min/max monthly), account-fee treatment, payment application order.

7. `GET /api/financial-petitions?petition_id=<petition>` — petition details, requested amounts, budget information, clerk notes.

### Post-Disposition Financial and Supervision Packet (Gloucester County multi-case pattern)

Follow the same pattern as the single-case Gloucester packet, but repeat for each case/petition pair. Additionally:

1. `GET /api/jurisdictions?name=Gloucester` if the jurisdiction code is not obvious from the materials.

2. For each case: cases, charges, docket-entries queries.

3. For each petition: financial-petitions query.

4. Shared queries: forms (CC-1375, CC-1379), payment-policies.

5. Cross-reference: use search when multiple cases share a jurisdiction and policy.

## Handling Missing or Ambiguous Portal Data

If a portal endpoint returns an empty result or an error:

- Note the gap and rely on the local materials for that field.
- If the field is required by the template and still unfillable, use the `"TBD from case file"` placeholder.
- Do not fabricate portal data or assume values not present in any source.

If the portal returns data that conflicts with the hearing notes, the hearing notes win (see reconciliation hierarchy).

## Jurisdiction Codes

Common patterns from the training evidence:

- Redwood County, AR: `AR-RC`
- Oregon 22nd Judicial District, Jefferson County: `OR22-JEFF`
- Gloucester County, VA: derive from the portal cases or jurisdiction response
- Union County, AR: derive from the portal cases or jurisdiction response

When the jurisdiction code is not explicit in local materials, query `/api/jurisdictions` or extract it from the portal case/citation response.
