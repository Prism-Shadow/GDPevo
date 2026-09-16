# Peer-to-Peer Discussion Finalization

## Overview

Finalize a completed peer-to-peer (P2P) discussion for a cardiac imaging authorization
case and produce the structured P2P summary. The output matches the P2P answer
template with required fields: `case_id`, `p2p_id`, `requested_cpt`, `p2p_outcome`,
`final_status`, `criteria_results`, `unresolved_criteria`,
`new_information_changed_review`, `missing_pet_factors`, `letter_type`,
`recommended_alternative`, `internal_appeal_deadline`, `basis_audit`.

## Workflow

### 1. Gather case and P2P context

Pull the authorization case and P2P event records from the environment. Identify:

- The case ID and P2P event ID
- The requested CPT code (cardiac imaging, typically PET MPI: `78431`)
- The policy criteria applicable to the requested procedure
- The clinical documents supporting the request
- The P2P event outcome: did the medical director overturn or uphold?

### 2. Determine P2P outcome

The P2P event records whether new patient-specific information changed the review:

| Outcome | p2p_outcome | final_status | Description |
|---------|------------|-------------|-------------|
| P2P overturned denial | `overturn_to_approval` | `approved` | New information justified approval |
| P2P upheld denial | `uphold_intended_adverse_decision` | `denied` | Information did not change the adverse determination |
| No P2P occurred | `not_applicable` | (as original) | Case didn't go through P2P |

### 3. Evaluate PET MPI criteria

Cardiac PET MPI requests are evaluated against two criterion keys:

| Criterion ID | What It Checks |
|-------------|----------------|
| `PET-IND` | Appropriate clinical indication for PET MPI |
| `PET-FACTOR` | At least one PET-over-SPECT factor documented |

Values: `met`, `not_met`, `unclear`, `not_applicable`.

**PET-FACTOR subfactors** (at least one must be supported):

- `prior_equivocal_spect` - Prior SPECT study was equivocal or inconclusive
- `bmi_limitation` - Patient BMI limits SPECT image quality
- `attenuation_artifact` - Known attenuation artifact risk with SPECT

When `PET-FACTOR` is `not_met`, list all unsupported subfactors in
`missing_pet_factors` using the order: prior_equivocal_spect, bmi_limitation,
attenuation_artifact.

### 4. List unresolved criteria

`unresolved_criteria` lists criterion IDs still unresolved after P2P. Use ascending
criterion ID order. An empty list means everything is resolved.

When `PET-FACTOR` remains `not_met` after P2P and the P2P did not supply new
evidence for its subfactors, it is unresolved.

### 5. New information assessment

`new_information_changed_review` is `true` only when the P2P discussion supplied
new patient-specific clinical information that materially changed the medical
director's assessment of the case. If the P2P confirmed the original determination
or added only marginal context, it is `false`.

### 6. Determine letter type and alternative

| final_status | letter_type | recommended_alternative |
|-------------|------------|------------------------|
| `approved` | `approval` | `PET MPI` (the approved service) |
| `denied` (PET MPI) | `denial` | `SPECT MPI` |
| `denied` (other) | `denial` | `none` |
| `partially_approved` | `partial_denial` | varies |

When a PET MPI request is denied because `PET-FACTOR` is not met, the recommended
alternative is `SPECT MPI` -- the standard non-PET alternative that does not require
the PET-specific factors.

### 7. Calculate internal appeal deadline

When the final status is `denied` (or any adverse determination), the plan provides
a 180-day internal appeal window from the final adverse determination date.

```
internal_appeal_deadline = final_adverse_determination_date + 180 calendar days
```

Use `null` when no adverse determination was issued (approved cases have no appeal
deadline).

The final adverse determination date is the date of the P2P outcome, not the
original denial date.

### 8. Construct the basis_audit

Use `new_patient_specific_p2p_information`:

- `controlling_record_ids`: the P2P event record and the primary clinical document(s)
  that survived the P2P review
- `exception_record_ids`: unresolved criterion IDs and any specific missing PET
  factor identifiers
- `precedence_record_order`: P2P event first (highest priority -- new information),
  then clinical documents, then unresolved criteria

## Key Patterns from Training

- Even when `PET-IND` is met, if `PET-FACTOR` is not met and P2P does not supply
  new evidence for it, the outcome is uphold/denied.
- `missing_pet_factors` lists all three subfactors when none are supported --
  it is not just the one the prescriber argued for.
- The internal appeal deadline is calculated from the date of the P2P final
  determination, not the original request date.
- `unresolved_criteria` includes `PET-FACTOR` when it remains `not_met` after P2P.
- `new_information_changed_review` is `false` when the P2P did not supply material
  new clinical evidence, even if the P2P occurred.
