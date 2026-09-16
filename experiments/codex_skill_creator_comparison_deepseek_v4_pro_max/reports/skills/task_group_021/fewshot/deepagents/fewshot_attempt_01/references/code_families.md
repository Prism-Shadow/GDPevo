# Opaque Control Code Families

Every certification task requires assigning opaque control codes to scoped
decisions. These codes appear in the answer templates and the training answers
in consistent patterns. The solver must infer the correct code from the
observed data — the codes are not enumerated in the task materials.

## Identity Codes (IC-*)

Used for person/contact deduplication and master-record selection decisions.

| Code | Meaning (inferred from training evidence) |
|------|------------------------------------------|
| IC-25 | Single-source record — no merge, single row from one system |
| IC-40 | Quarantined row — record flagged for no usable contact channel |
| IC-70 | Multi-source merge — multiple rows merged with field-level precedence |
| IC-90 | Contested identifier — watchlist case with conflicting identity signals |

## Field Provenance Codes (FP-*)

Used for decisions about which source system provided a canonical field value.

| Code | Meaning (inferred from training evidence) |
|------|------------------------------------------|
| FP-20 | Single-source provenance — no alternative source available |
| FP-55 | Multi-source merge — field resolved via precedence rules |
| FP-75 | Quarantined or invalid — no usable field from any source |

## Outreach Codes (OR-*)

Used for communication-channel readiness and exclusion decisions.

| Code | Meaning (inferred from training evidence) |
|------|------------------------------------------|
| OR-15 | Inactive-person exclusion — record is inactive |
| OR-35 | Channel-eligible (consent granted with email and/or phone usable) |
| OR-60 | Quarantine — no usable contact channel |
| OR-80 | Consent-blocked — active person with usable channel but no consent |

## Reference Policy Codes (RB-*)

Used for alias-to-canonical classification decisions in fuel and freight audits.

| Code | Meaning (inferred from training evidence) |
|------|------------------------------------------|
| RB-17 | Unambiguous single-category match |
| RB-42 | Ambiguous match — alias maps to multiple canonical categories |
| RB-83 | Unrecognized — alias not found in reference table |

## Source Basis Codes (SB-*)

Used for source-retention decisions on individual transactions/charges.

| Code | Meaning (inferred from training evidence) |
|------|------------------------------------------|
| SB-24 | Single-source — record appears in only one snapshot |
| SB-61 | Certified-preference — record in both snapshots, certified copy retained |
| SB-79 | Provisional-only — record appears only in provisional snapshot |

## Ledger Disposition Codes (LD-*)

Used for accounting-ledger routing decisions on transactions/charges.

| Code | Meaning (inferred from training evidence) |
|------|------------------------------------------|
| LD-14 | Unrecognized/quarantine — cannot enter the ledger |
| LD-31 | Valid mismatch — enters ledger with exception flag |
| LD-53 | Valid clean — no exceptions, standard routing |
| LD-72 | Valid duplicate-resolved — retained from deduplication |
| LD-88 | Ambiguous alias — classification unresolved, quarantined |

## Maintenance Source Codes (MS-*)

Used for maintenance-event source attribution.

| Code | Meaning (inferred from training evidence) |
|------|------------------------------------------|
| MS-12 | Provisional-only — event appears only in provisional snapshot |
| MS-47 | Certified-only — event appears only in certified snapshot |
| MS-86 | Duplicate — event appears in both snapshots |

## History Route Codes (HR-*)

Used for maintenance-event history routing decisions.

| Code | Meaning (inferred from training evidence) |
|------|------------------------------------------|
| HR-19 | Regression — odometer regression detected |
| HR-33 | Clean duplicate — resolved from certified+provisional, no issues |
| HR-74 | Invalid — rejected for data-quality issues |

## How to assign codes

Look at the evidence rows supplied in the case scope. For each decision:

1. Query the source data for the specific row IDs.
2. Determine the factual situation: single-source vs multi-source, certified-only
   vs provisional-only vs both-snapshots, valid vs quarantined vs mismatched.
3. Map the fact pattern to the code using the tables above.

The pattern is consistent across all five training examples. For instance:
- A person merged from three source rows with field-level precedence always
  gets IC-70 and FP-55.
- A single-row quarantined person always gets IC-40 and FP-75.
- A transaction in both snapshots with certified retained always gets SB-61.
- A valid mismatch transaction always gets LD-31.
- A clean deduplicated transaction retained from both always gets LD-72.
