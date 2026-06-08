# Task Notes
## English

Task definition and business objective: This test task asks the solver to review policy case `CASE-445` and determine whether an approved-with-conditions lifecycle case is ready to close. The business objective is to combine approval history, document readiness, formal notice quality, audit evidence, closeout blockers, and tag remediation into one operational decision.

Visible inputs and Web evidence: The solver-visible prompt gives the local PeopleOps Console URL/login and the case under review. Public evidence should be gathered from Policy Cases, approval history, document folder checklist or attachment viewer, message/notice inspection, policy document viewer if needed, and Audit Log detail. The answer template exposes field names and allowed shapes, but not the business findings.

Expected reasoning and answer basis:
- Use approval history to identify `CASE-445`, final decision `approved_with_conditions`, authority `VP People`, and approval event `APP-445-FINAL`.
- Open the folder checklist and compare required files/tags to filed evidence. The folder is not ready; missing files are `benefits-election.pdf` and `executive-exception-approval.pdf`; `required_tag_present` is `false`.
- Inspect the formal notice rather than trusting case summary. Notice quality is `defective`, with `missing_appeal_instructions` and `missing_ack_deadline`.
- Cite audit event `AUD-CASE445-03`.
- Approval does not permit closeout when folder or notice controls fail. Use `approval_not_sufficient_when_folder_or_notice_defective`.
- Return blockers `missing_required_files`, `missing_required_tag`, and `defective_formal_notice`.
- Use `approval_history_folder_notice_audit` as evidence source order.
- Because the required tag is absent, use `add_required_tag_before_close`.
- Use `block_close_and_reissue_notice` as the next action.

Train anchors and transferred knowledge: This test reuses `train_002` for approved-but-blocked closeout, formal-notice defect handling, source order, and the approval gate label. It reuses `train_001` for the contrast between clean closeout and blocked closeout. It reuses `train_004` for scoped audit reasoning and not overusing adjacent evidence. The task-specific work is finding the `CASE-445` folder, message, approval, and audit details.

Likely pitfalls: Closing the case because the approval says final; listing only one missing file; forgetting the missing required tag; using prose for `approval_closeout_gate`; omitting `missing_required_tag` from blockers; or selecting an audit event that confirms payroll rather than case closeout.

Evaluator/scoring basis: `eval/rubric.json` has eight checks with 18 total points: case ID, approval record, folder readiness, notice quality, approval closeout gate, closeout blockers, evidence source/tag action, and audit/next action. The highest-weight points require the normalized gate, blockers, and next action.

Construction/rework note: This notes file was expanded after reviewer feedback to synchronize with current `output/answer.json` and `eval/rubric.json`, including `approval_closeout_gate`, `closeout_blockers`, `evidence_source_order`, and `folder_required_tag_action`.

