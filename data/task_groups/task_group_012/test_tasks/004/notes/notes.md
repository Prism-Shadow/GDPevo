# Task Notes
## English

Task definition and business objective: This test task audits three lifecycle document folders and related messages, then decides which folders are not ready, which notices are defective, which audit events support the document/notice findings, and what records remediation should occur.

Visible inputs and Web evidence: The solver-visible prompt names folders `DOC-ERIN-ONB`, `DOC-PRIYA-POL`, and `DOC-MARCO-PAY` and gives the local PeopleOps Console entry point. Public evidence should be gathered from Documents folder checklist/details, attachment or file lists, Messages notice inspection, related Policy Cases, Audit Log detail, and any policy viewer content that defines required tags or notice standards.

Expected reasoning and answer basis:
- Review all three folders: `DOC-ERIN-ONB`, `DOC-PRIYA-POL`, and `DOC-MARCO-PAY`.
- `DOC-ERIN-ONB` is not ready because it is missing `benefits-election.pdf`, `executive-exception-approval.pdf`, and required tag `PolicyException2026`.
- `DOC-PRIYA-POL` is not ready because it is missing `decision-record.txt` and required tag `PolicyException2026`.
- `DOC-MARCO-PAY` has no missing required files or tags.
- Use `folder_checklist_comparison` as folder evidence source.
- Identify defective messages `MSG-ERIN-445` and `MSG-PRIYA-118`, using `message_notice_inspection` as notice evidence source.
- Supporting document/notice audit events are `AUD-CASE445-03` and `AUD-DOC118-06`.
- Exclude `AUD-EMP118-LEAVE-04` because it supports leave source precedence, not document/notice findings.
- Set `audit_scope` to `document_notice_findings_only`.
- Remediation should be `open_records_remediation`, owner `Records`, and notice action `reissue_defective_notices`.

Train anchors and transferred knowledge: This test combines `train_002` for folder/notice closeout blocking, evidence source order, `Records` ownership, and `reissue_defective_notices`; `train_004` for audit-scope exclusion of adjacent leave events; and `train_001` for the contrast between clean folders/records and blocked lifecycle closeout. The test-specific work is applying the SOP to three folders rather than one case.

Likely pitfalls: Treating document titles as proof of readiness; missing required tags while finding missing files; including `AUD-EMP118-LEAVE-04` as support because it shares an employee; omitting `audit_scope`; using `People Ops Compliance` instead of `Records` for this records-remediation owner field; or writing prose instead of normalized remediation labels.

Evaluator/scoring basis: `eval/rubric.json` has seven checks with 13 total points: reviewed folders, readiness/files, missing tags/source, defective messages/source, supporting audit events/scope, excluded audit events, and remediation action/owner/notice action. The remediation check is high value and requires all three normalized fields.
