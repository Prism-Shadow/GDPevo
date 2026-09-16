# Policy Evaluation (Cross-Domain)

## Purpose

Determine whether a current policy baseline creates deficiencies or material review flags that would not have applied under a prior baseline. This feeds the `policy_impacted` boolean in contractor reviews and influences posture decisions in liquor reviews.

## Method

1. **Read the current policy baseline** from `GET /api/policies`. The response includes current standards: minimum bond amounts, minimum insurance coverage, required endorsements, minimum experience thresholds, inspection requirements, and other regulatory standards.

2. **Identify the prior baseline** from the same response. The policy record typically includes both `current` and `prior` or `previous` fields, or describes changes in a narrative field. Look for explicit "increased from X to Y", "new requirement", or "changed from" language.

3. **For each deficiency** found in an application:

   a. Determine which policy standard triggers the deficiency.
   b. Compare that standard against the prior baseline.
   c. If the standard is **new** or **stricter** than the prior baseline (higher minimum, new endorsement, higher experience threshold), and the applicant meets the prior standard but fails the current one, mark `policy_impacted = true`.
   d. If the standard is **unchanged** from the prior baseline, or the applicant fails both baselines equally, mark `policy_impacted = false`.

4. **Non-policy deficiencies** are never policy-impacted:
   - Bond cancellation (the bond existed but was cancelled — not a policy minimum issue).
   - Insurance expiration (the policy lapsed — not a coverage-amount issue).
   - Pending endorsement or insurance that has simply not yet been processed (the standard exists but the applicant hasn't completed the paperwork).
   - Open violations or complaints (these are behavioral, not policy-driven).
   - Inspection gaps (these are procedural, not policy-driven).

## Examples from Train Evidence

### Policy-impacted deficiencies

- **Bond shortfall due to raised minimum**: The prior baseline allowed a lower bond amount; the current baseline raised the minimum, and the applicant's bond meets the old minimum but falls below the new one.
- **Insurance shortfall due to raised minimum**: Same pattern for insurance coverage.
- **New endorsement requirement**: The current baseline requires an endorsement that the prior baseline did not require at all.

### Non-policy-impacted deficiencies

- **Bond cancelled**: The bond was cancelled by the surety — independent of minimum amount.
- **Insurance expired**: The policy period ended — independent of coverage amount.
- **Endorsement pending**: The endorsement application is in process — the requirement exists but the delay is administrative.
- **Experience shortfall**: Only policy-impacted when the experience threshold itself was raised. If the threshold is unchanged and the applicant simply doesn't meet it, it is not policy-impacted.

## Liquor Review Policy Impact

In restricted liquor license reviews, policy changes can affect:
- Whether the same-premises basis still applies (if policy changed the eligibility window).
- Which obligations are now standard vs. previously optional.
- Whether new control requirements (CCTV, security) create verification gaps.

The same comparison logic applies: identify what changed from the prior baseline and whether the change creates a new deficiency or alters the posture.
