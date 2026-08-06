# Policy Crosswalk: Determining `policy_impacted`

## Definition

`policy_impacted` is `true` when the **current** policy baseline creates a deficiency or material review flag that would **not** have applied under the **prior** baseline.

## Procedure

1. **Fetch `/api/policies`** — this returns the current policy record, which includes the baseline standards and any prior-baseline comparison data.

2. **Identify changed requirements.** Compare current vs. prior baseline for:
   - Minimum bond amounts
   - Minimum insurance coverage amounts
   - Endorsement requirements (newly required specialties)
   - Experience thresholds
   - Violation severity classifications (a minor violation reclassified as serious)
   - Inspection standards
   - Renewal deadlines or grace periods

3. **Apply per application.** For each target application:
   - If the application would have been **APPROVE** under the old baseline but has a deficiency under the new one → `policy_impacted: true`
   - If the application had a deficiency under **both** baselines → `policy_impacted: false` (the deficiency already existed)
   - If a deficiency is **more severe** under the new baseline (e.g., shortfall amount is larger) → `policy_impacted: true`
   - If the application is clean under both baselines → `policy_impacted: false`

4. **Common triggers for `policy_impacted: true`:**
   - Bond or insurance minimum was raised — applications that met the old minimum but not the new one
   - A new endorsement was added — applications missing it
   - A violation was reclassified (minor → serious) — applications with that violation now face a higher determination
   - A new inspection standard was introduced — applications that passed inspection under old rules

5. **In the summary**, list all `policy_impacted_application_ids` sorted ascending.

## Important

- `policy_impacted` is independent of the overall determination. An application can be `APPROVE` and still `policy_impacted` if the policy change affected risk tier or a review flag (though this is rare — usually a policy change that impacts the analysis creates a deficiency).
- When in doubt, default to `false`. The flag should mark cases where the policy change is the **cause** of a difference, not merely correlated.
