# Pharmacy Appeal Packet Items

Full catalog of packet items used in pharmacy coverage appeal and manufacturer assistance intake dispositions.

## Complete Item List

These are the nine possible items that may appear in required_packet_items or missing_packet_items:

| Item ID | Category | Description |
|---------|----------|-------------|
| denial_notice | payer_appeal | The coverage denial notice from the payer |
| member_authorization | payer_appeal | Signed member authorization for appeal |
| prescriber_rationale | payer_appeal | Prescriber clinical rationale for the requested drug |
| formulary_failure_evidence | payer_appeal | Documentation of failed formulary alternatives |
| pharmacy_claim_history | payer_appeal | Pharmacy claim history showing prior fills |
| diagnosis_confirmation | payer_appeal | Confirmation of the qualifying diagnosis |
| expedited_risk_attestation | payer_appeal | Attestation of medical risk requiring expedited review |
| household_income_proof | assistance | Household income documentation for manufacturer assistance |
| lurasidone_fill_record | payer_appeal | Specific fill record for lurasidone (formulary alternative) |

## Item Categories for Ordering

### Payer Appeal Items (listed first in required_packet_items)
These support the coverage appeal itself:
- denial_notice
- member_authorization
- prescriber_rationale
- formulary_failure_evidence
- pharmacy_claim_history
- diagnosis_confirmation
- expedited_risk_attestation
- lurasidone_fill_record

### Assistance Items (listed after appeal items in required_packet_items)
These support the manufacturer assistance application:
- household_income_proof

## Ordering Rules

**required_packet_items:** Payer appeal items before assistance items. Within each category, use the order shown in the category list above.

**missing_packet_items:** Appeal evidence gaps before assistance information gaps. Within each gap type, use the order shown in the relevant category list above.

## Determination Logic

### Which items are required?
Start with the base set determined by the appeal type and drug:
- Every appeal needs: denial_notice, member_authorization, prescriber_rationale
- If formulary failure is required by policy: formulary_failure_evidence, pharmacy_claim_history
- If specific alternatives are named in criteria: include their fill records (e.g., lurasidone_fill_record)
- If expedited: expedited_risk_attestation
- If diagnosis confirmation is needed: diagnosis_confirmation
- If manufacturer assistance is being screened and income-based: household_income_proof

### Which items are missing?
For each required item, check whether evidence of that item exists in the environment data:
- denial_notice: check appeals table for denial_date presence
- member_authorization: check for signed authorization document
- prescriber_rationale: check case_criteria for DRUG-RATIONALE result
- formulary_failure_evidence: check drug_trials for documented failures
- pharmacy_claim_history: check for claim records
- diagnosis_confirmation: check document_facts for diagnosis facts
- expedited_risk_attestation: check appeals.expedited_attestation
- household_income_proof: check assistance_screen.missing_fields
- lurasidone_fill_record: check drug_trials for lurasidone records with documented=1
