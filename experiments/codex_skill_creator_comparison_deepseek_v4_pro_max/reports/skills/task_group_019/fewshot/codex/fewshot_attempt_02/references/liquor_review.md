# Restricted Liquor License Staff Package

## Overview

Prepare a structured staff package for a single liquor license application at a specific location. The output is a JSON object with top-level fields whose exact key names and allowed values come from the task's answer template.

## Data-Fetching Sequence

1. GET /api/policies -- current policy baseline, including same-premises rules.
2. GET /api/liquor/applications -- the target application and its details.
3. GET /api/liquor/settlements -- prior settlement agreements tied to the applicant or premises.
4. GET /api/liquor/privileges -- current privilege grants and operating conditions.
5. GET /api/liquor/incidents -- incidents at or near the premises, including police memo references.
6. GET /api/liquor/site-evidence -- floor plans, photos, control signage, camera evidence, food-service evidence, neighbor notices, tax clearance.

## Posture Decision Logic

### issue_restricted

Assign when the application has no blocking deficiencies, all required evidence is verified, and any identified risks are covered by existing controls or obligations.

### request_follow_up

Assign when verification gaps exist that can be resolved by requesting additional evidence or follow-up checks, but no fundamental denial trigger is present. This is the most common posture when evidence is partially incomplete or conflicting.

### deny

Assign when a denial trigger is present: same-premises basis has lapsed or been revoked and cannot be reestablished; an open/active serious incident remains unresolved; required core evidence is missing and cannot be reasonably obtained.

## Same-Premises Basis

Check the application record and policy baseline. `same_premises_basis_applies` is true when:
- The application is filed under a same-premises provision that remains in effect per current policy.
- The prior license at the same premises was valid and the basis has not expired.

It is false when the policy has changed such that the same-premises basis no longer applies, or the prior license status invalidates the basis.

## Covered Risk Assessment

For each risk category in the template's allowed values, determine whether existing controls, obligations, or evidence adequately cover it. A risk is "covered" when:
- There is an active control or obligation that directly mitigates it.
- The site evidence confirms the control is in place.
- No incident record contradicts the coverage.

## Verification Gap Identification

A verification gap exists when:
- Required documentation is missing from site evidence (e.g., no camera evidence, no food-service photos, no control signage images).
- Floor plans conflict with application descriptions or are stale.
- Control signage is present but conflicting or outdated.
- Police memos are missing, conflicting, or reference unresolved follow-up.
- Neighbor notices are missing when required.
- Site photos are absent.
- Tax clearance is unresolved or missing.
- An incident follow-up remains open.

Use only the gap codes defined in the task's answer template.

## Standard Obligations vs. Location-Specific Controls

**Standard obligations** are conditions that apply to this license class regardless of location. They come from policy, license-class rules, and the application's privilege grants.

**Location-specific controls** are conditions tied to this particular premises through prior settlements, incident history, or site-specific requirements. They may overlap with standard obligations (when the location-specific condition reinforces a standard one) or be distinct.

If the template provides the same enum set for both fields, include an obligation code in the standard list when it is a class-level requirement, and in the location-specific list only when there is a premises-specific control that enforces it.

## First-90-Day Plan Construction

Build an ordered sequence of monitoring checks, each with a check_code and a timing bucket (first_30_days, days_31_60, days_61_90). Sequencing principles:

- Place foundational verification checks (control signage, camera checks) in the first 30 days.
- Place operational observation checks (id checks, food-service checks) across the first 60 days.
- Place follow-up and boundary enforcement checks (late-night visits, noise/patio checks) in days 31-90.
- Place tax clearance and incident follow-up checks at the point when evidence should be available.
- Each check_code + timing pair should appear at most once.

Use only the check_code and timing values from the task's answer template.

## Escalation Trigger Selection

An escalation trigger is a condition that, if observed, should cause field staff to escalate the license for further review. Select codes from the template based on:

- Risks that are partially covered but have high severity if breached (after-hours service, camera coverage gaps, noise/patio breaches).
- Unresolved issues that could recur (open tax hold, unresolved minor sale referrals).
- Structural vulnerabilities identified in the review (missing camera coverage, control signage not verified).
- Known incident patterns at or near the premises.

A trigger should correspond to a gap or risk that warrants immediate attention rather than routine monitoring.
