---
name: licensing-record-review
description: Structured licensing-record analysis for contractor eligibility batches, restricted liquor staff packages, and alcohol renewal manual-review queues. Use when Codex must turn licensing environment records, policy tables, application files, violation histories, site evidence, financial coverage, or renewal boundary rules into schema-conformant JSON decisions or staff-review queues.
---

# Licensing Record Review

## Core Workflow

1. Read the prompt, the answer template, and the current environment instructions before querying data.
2. Extract the target identifiers, review date or release boundary, required queue size, ordering requirements, allowed enum values, and summary fields from the prompt/template.
3. Query only authorized data sources for target records and directly related records. Prefer targeted joins or filters over broad dumps, and keep distractor rows out unless the task's matching rules explicitly allow close-address or successor matches.
4. Build a trace table before writing JSON: one row per target application, license, or location with policy thresholds, current records, adverse history, evidence gaps, risk tier, and summary membership.
5. Emit only JSON that matches the provided template. Use exactly the requested keys, allowed enum values, empty arrays instead of nulls, required ordering, and summary counts that reconcile with item-level decisions.

## Contractor Eligibility Batches

Use the current contractor policy row for the application's trade/class. Parse policy details for minimum bond, insurance, years of experience, required endorsement, and serious-violation blocking rules.

Evaluate each application independently:

- Treat only active, uncancelled bond records as current. If no active bond exists, use the schema's no-active/cancelled-bond deficiency. If an active bond exists but is below the policy minimum, use the schema's bond-shortfall deficiency.
- Treat insurance as current only when status is active and the expiration date is after the review date when a review date is supplied. Pending, inactive, expired, or insufficient insurance should map to the schema's closest not-current, pending, expired, or shortfall labels.
- Treat missing and pending endorsements as deficiencies when the current policy requires an endorsement. Verified and not-required statuses are not deficiencies.
- Compare documented years of experience to the current policy minimum. Do not convert a correspondence conflict into an experience shortfall by itself when the application record already meets the numeric threshold; list that correspondence in the summary if requested.
- Treat active suspension history and open serious violations as high-risk blockers. Use deny-level determinations when the schema supports denial for these blockers; otherwise require board or complaint resolution actions. Open minor violations usually create a hold, not denial.
- Use inspection deficiencies only when the output schema has matching codes/actions. Failed or conditional document-gap and safety-recheck findings matter; pass, none, wrong-trade, stale, or unrelated inspection rows usually do not.
- Build stale/unverified correspondence summaries from records that are agency-unverified, stale, applicant-only with no agency confirmation, conflicting, explicitly unverified, or pending outside agency review. Do not let unrelated correspondence override authoritative application, bond, insurance, violation, or history records.
- Mark `policy_impacted` only when a current policy requirement materially creates or changes a deficiency compared with the prior baseline, such as a higher minimum or newly required endorsement. Do not mark it for unrelated status problems like a cancelled record or active suspension.

Determination pattern:

- `APPROVE`: no unresolved deficiencies or blocker history.
- `HOLD`: curable deficiencies such as missing documents, shortfalls, pending verification, no active coverage, or minor open matters.
- `DENY`: active suspension or unresolved serious matters when the schema and prompt frame them as blockers.

Always recompute summary counts and high-risk/policy-impacted lists from the final item decisions.

## Restricted Liquor Staff Packages

Separate ordinary license obligations from location-specific settlement controls.

- Ordinary obligations come from the privileges or rules for the requested license class where the obligation is marked standard-required.
- Location-specific controls come from active settlement/control records whose active flag is true and whose expiration has not passed.
- A same-premises basis applies when a current active settlement or current prompt facts make that basis operative. Expired historical same-premises records may inform context but should not be treated as currently applicable by default.
- Covered risk codes should reflect risks addressed by current active controls and currently supported ordinary obligations. Do not mark an open or evidence-missing risk as covered merely because the obligation exists in the abstract.
- Verification gaps should capture missing, conflicting, stale, identity-conflicted, or not-current site evidence; unresolved incident follow-up; open tax holds; camera or food-service evidence gaps when the prompt emphasizes them; and late-night monitoring needs when hours or after-hours history is not currently controlled.
- Recommended posture is usually `issue_restricted` when controls are current and remaining issues are not material; `request_follow_up` when current controls exist but evidence, incident, tax, or monitoring gaps remain; and `deny` only for unresolved disqualifying issues that cannot be handled by restrictions or follow-up.

For first-90-day plans, choose checks that directly verify the active controls and open gaps. Put urgent evidence, tax, camera, food-service, and signage checks in the first 30 days; use later windows for follow-up visits, log reviews, and stabilization checks unless the schema specifies a different ordering rule.

Escalation triggers should mirror the uncovered risks and verification gaps: control failures, missing or unavailable camera footage, food service not available, late-hours service, noise or patio breaches, unresolved tax holds, unreported major incidents, and ID-check failures when age-verification risk is in scope.

## Alcohol Renewal Manual-Review Queues

Start from the release boundary and renewal rules.

- Include only violations known on or before the boundary date. Treat the boundary as inclusive unless the prompt says otherwise.
- Record post-boundary violation IDs in the excluded summary when the schema asks for them.
- Prefer exact license-number matches. Use successor or close-address matches only when the rules or available records require them; mark the match confidence as uncertain or close-address and include the license in the close/uncertain summary.
- Build the matched-violation list from the violations actually used for the queue decision. If the rules distinguish manual-review triggers, keep alert-flag and unpaid-fine rows prominent in the risk analysis while still following the template's definition of matched count.
- Rank with the task's explicit priority rules first. If no formula is supplied, create a stable risk sort from blocker severity, open/pending status, alert flags, unpaid balances, violation count, most recent matched date, match confidence, and license number. Verify that rank order, item fields, and summary lists are all derived from the same trace table.

Typical next-step labels:

- Manual fine check for unpaid balances or fine-hold issues.
- Manual alert check for alert-trigger rows without stronger fine or board-review reasons.
- Board review for serious open/pending matters or other release-blocking risk.
- Additional record check for uncertain successor or close-address matches, thin evidence, or low-confidence records.

## Final JSON Checks

Before returning the answer:

- Validate all enum strings against the template.
- Sort arrays exactly as instructed by the schema; if the schema says operational sequence, use the actual monitoring sequence instead of alphabetical order.
- Keep application decisions ordered by target identifier and queue entries ordered by ascending rank.
- Recompute counts, high-risk lists, board-review lists, post-boundary exclusions, and stale/unverified summaries from the final item data.
- Remove prose, citations, comments, and any extra keys.
