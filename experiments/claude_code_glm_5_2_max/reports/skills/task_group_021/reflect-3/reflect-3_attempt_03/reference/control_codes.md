# Control Code Inference Rules

Control codes are compact internal identifiers whose expansions are not provided in task materials. The following mappings are inferred from training patterns.

## Identity Codes (IC)

| Code | Condition |
|------|-----------|
| IC-90 | 3 or more verified source rows confirm the entity |
| IC-70 | 2 verified source rows |
| IC-40 | 1 verified source row |
| IC-25 | No verified source rows |

"Verified" means `verified_flag = 1` on at least one contributing row.

## Field Provenance Codes (FP)

| Code | Source System |
|------|---------------|
| FP-75 | Compliance Master or Identity Registry |
| FP-55 | Partner Portal or HR Directory |
| FP-20 | CRM or Dispatch |

Use the source system that provides the canonical value for the field in question (typically city for focus clusters, highest-authority source for anchored cases).

## Outreach Codes (OR)

| Code | Condition |
|------|-----------|
| OR-80 | Has usable channel AND consent = GRANTED |
| OR-60 | Has usable channel AND consent = DENIED |
| OR-35 | Has usable channel AND consent = PENDING |
| OR-15 | No usable channel, or consent = UNKNOWN, or inactive |

## Reference Basis Codes (RB)

| Code | Condition |
|------|-----------|
| RB-83 | ACTIVE alias with no `valid_to` (permanently active) |
| RB-42 | ACTIVE with bounded `valid_to`, or PROVISIONAL status |
| RB-17 | INACTIVE, RETIRED, or not yet valid for the audit period |

Check validity dates against the cutoff! An alias with `valid_from` after the cutoff is NOT applicable even if ACTIVE.

## Source Basis Codes (SB)

| Code | Condition |
|------|-----------|
| SB-79 | Row comes from the authoritative (CERTIFIED) snapshot |
| SB-24 | Row comes from a PROVISIONAL snapshot |
| SB-61 | Mixed/uncertain source |

## Ledger Disposition Codes (LD)

| Code | Condition |
|------|-----------|
| LD-88 | Fully accepted (valid, recognized, matches expected) |
| LD-72 | (Usage unclear — possibly conditionally accepted) |
| LD-53 | Class mismatch but otherwise valid |
| LD-31 | Unrecognized or ambiguous category |
| LD-14 | Rejected (invalid quantity, weight, distance) |

## Maintenance Source Codes (MS)

| Code | Condition |
|------|-----------|
| MS-86 | Highest authority snapshot |
| MS-47 | Standard certified snapshot |
| MS-12 | Provisional or lower authority |

## History Route Codes (HR)

| Code | Condition |
|------|-----------|
| HR-74 | Accepted into canonical history |
| HR-33 | Flagged (e.g., regression detected) |
| HR-19 | Rejected / routed for review |

## Caution

These mappings are best-effort inferences from observed data patterns. The exact mapping may vary across collections or over time.
