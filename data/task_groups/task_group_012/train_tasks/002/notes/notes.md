# Task Notes
## English

Task definition and business objective: This train task asks the solver to review remote-work policy case `CASE-RW-221` and decide whether an approved-with-conditions case can close. The objective is to reconcile approval history with document-folder readiness, formal notice quality, remediation ownership, and audit scope.

Visible inputs and Web evidence: The solver-visible prompt provides the local PeopleOps Console entry point and case ID. Public evidence should be gathered from Policy Cases, approval history, Documents/folder checklist, Messages or notice packet inspection, Audit Log detail, and any policy document viewer content needed to interpret required files, tags, or notices.

Expected reasoning and answer basis:
- Use approval history to report `final_decision` as `approved_with_conditions`, authority `HR Director`, and event `APP-221-FINAL`.
- Compare the folder checklist to filed documents. The folder is not ready because `tax-equalization-agreement.pdf` is missing.
- The required tag is present, so `folder_required_tag_action` is `no_tag_action`.
- Inspect the formal notice packet. It is `defective` because it has `missing_appeal_instructions`.
- Use `AUD-CASE221-09` as both `audit_event_id` and the single `supporting_audit_event_ids` entry.
- Set `audit_scope` to `document_notice_findings_only`; no adjacent audit events need exclusion here, so `excluded_audit_event_ids` is empty.
- Approval is not sufficient because folder and notice evidence are defective. Use `approval_not_sufficient_when_folder_or_notice_defective`, blockers `missing_required_files` and `defective_formal_notice`, and final result `hold_for_folder_and_notice_defects`.
- Use `approval_history_folder_notice_audit` as the evidence order, `open_records_remediation` for escalation, `Records` as owner, and `reissue_defective_notices` for notice remediation.

Transferable SOP and field conventions: This task teaches that final approval does not override failed document or formal-notice controls. It anchors reusable labels for closeout gates, blockers, evidence-source order, document/notice audit scope, remediation ownership, and notice reissue. These labels transfer directly to test tasks involving `CASE-445` and document/message audits.

Likely pitfalls: Treating the final approval as enough to close; overlooking the missing required file; writing prose for `approval_closeout_gate`; confusing `next_action` with `escalation_action`; omitting `supporting_audit_event_ids`; or using a broad audit scope instead of `document_notice_findings_only`.

Evaluator/scoring basis: `eval/rubric.json` scores six exact-match checks: case/approval, folder readiness, notice quality, approval gate/blockers, source order/audit, and remediation. The audit check includes `audit_event_id`, `supporting_audit_event_ids`, `excluded_audit_event_ids`, and `audit_scope`.

Construction/rework note: This notes file was expanded after the notes review to reflect the current reworked answer and rubric, especially the added audit-scope fields and normalized remediation labels.

