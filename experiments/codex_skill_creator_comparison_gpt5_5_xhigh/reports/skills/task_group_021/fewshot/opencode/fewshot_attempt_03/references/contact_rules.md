# Contact Reconciliation Rules

Use these rules for contact-master, partner onboarding, field-service roster, dispatch readiness, and similar tasks.

## Normalization

- Normalize display text with Unicode NFKC, trim surrounding whitespace, and collapse internal whitespace for comparisons.
- Normalize email with Unicode NFKC, trim, and lowercase. Empty strings and nulls are missing.
- Normalize phone as digits only. Empty strings and nulls are missing.
- A usable channel exists when normalized email or normalized phone is nonempty.
- Record status is active only when the source status is active under the template's enum. Inactive records are not dispatchable/releasable.

## Identity Resolution

Cluster conservatively. Strong evidence is normalized email, normalized phone, explicit master hint, or source-system identity evidence that points to the same person. Do not merge rows only because name, city, or region match.

Watch for contested identifiers:

- Shared helpdesk or generic phone numbers across different names/emails are contested, not automatic merges.
- A shared `master_hint` with conflicting names/emails is contested unless another strong identifier confirms the same entity.
- Multiple no-contact rows with the same name are not enough to merge; they are separate or quarantined depending on the contract.

For each focus item, start from its anchor/seed row, find the resolved cluster, then return every member row id sorted lexicographically. Select the master/survivor from the strongest source-system row in the cluster, preferring verified registry/compliance rows when present.

## Field Precedence

Use field-level source precedence, not whole-row precedence, when sources disagree. If the data or task text names the source roles, use those roles first. In the observed Asteria patterns:

- Compliance or Identity Registry rows are strongest for stable master/survivor identity, contact fields, and consent.
- HR Directory rows are strongest for roster display name and depot/region.
- Dispatch and CRM rows are middle-tier operational sources.
- Portal/feed rows are lower-tier self-service sources.

Always report the source system for each canonical field when the template asks for it. The chosen field source may differ by field on the same canonical entity.

## Readiness and Quarantine

Quarantine source rows or entities with no usable email and no usable phone when the contract is about contact usability. Do not include quarantined contact rows in channel-ready counts unless the template explicitly asks for raw quarantine row ids separately.

For partner-contact readiness, an entity is readiness-eligible only when it is active and retains at least one usable email or phone. A channel is ready only when consent is granted. Partition ready entities by email-only, phone-only, both, and not-ready according to the template.

For dispatch rosters, a person is dispatchable only when:

- canonical record status is active
- at least one usable dispatch channel is retained
- canonical consent status is granted

For readiness-by-depot partitions, make the disposition counts add to the depot's total canonical people. Use the template's definitions to classify blocked consent, blocked no-contact, and blocked inactive cases.

## Contact Summary Fields

Common count definitions:

- `raw_row_count`: all in-scope public source rows.
- canonical entity/person count: resolved clusters plus unmerged singletons/quarantined entities, as defined by the template.
- merged duplicate cluster count: count of multi-row clusters that confidently merge into one entity.
- quarantine row count: source rows with no usable channel when the contact contract is row-oriented.
- contested identifier cluster count: requested or discovered identifier cases that remain contested.
- dispatchable/readiness count: count of canonical ids that pass the task's active/channel/consent policy.

For certification/release decisions, apply any case-scope thresholds or status/action maps exactly. If the task supplies no numeric gate, hold/review when contested identifiers or quarantines are material to the requested release decision.
