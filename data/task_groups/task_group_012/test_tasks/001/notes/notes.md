# Notes

## English

Data/source lineage: This test task belongs to `SCN_012_erp_hr_employee_lifecycle`, using the ERP HR employee lifecycle scenario and transfer patterns from the local train tasks, especially the authoritative-record selection in `train_tasks/001` and lifecycle communication/compliance checks in the recruiting and policy tasks. The solver-visible materials are `input/prompt.txt` and `input/payloads/answer_template.json`; the business evidence is expected to be gathered from the PeopleOps Console at runtime.

Task definition: The solver must decide final lifecycle clearance for `EMP-255`, Erin Novak, by combining employee detail, leave, payroll, document folder status, messages, approval history, and audit log. The expected output is structured JSON with the final decision, leave policy and assignment, leave balance, payroll assignment and salary, missing folder files, notice defects, controlling audit event, and escalation owner.

Scenario fit and material map: The task exercises the same cross-system HR operations pattern as the source scenario: lifecycle decisions depend on HRMS records, payroll assignments, document controls, notification quality, approvals, and audit evidence. `answer_template.json` defines the output contract without revealing the result. `output/answer.json` records the gold answer. `eval/rubric.json` defines exact-match scoring, and `eval/eval.sh` calls `eval/evaluate.py`.

Solution and evaluation basis: The gold answer identifies `EMP-255`, sets `clearance_decision` to `hold`, selects `R&D Flex Leave 2026` through `LA-255-APP-03`, records `leave_balance_days` as `21`, selects submitted payroll assignment `PAY-255-SUB-02` with `base_salary` `142000`, excludes `PAY-255-DRAFT-03`, flags missing folder files `benefits-election.pdf` and `executive-exception-approval.pdf`, records that the required tag is not fully present, flags notice defects `missing_ack_deadline` and `missing_appeal_instructions`, and ties the hold to audit event `AUD-CASE445-03` with escalation owner `People Ops Compliance`. The evaluator uses source-precedence, control-result, folder, notice, audit, and escalation scoring points; list fields are normalized by the shared helper, so order is not material.

Transfer design: This is a test task. Transfer should come from train tasks that teach authoritative submitted/approved record selection, exclusion of draft or stale lifecycle data, and compliance hold decisions when required documents or notice controls are defective. High-value scoring depends on transferring that SOP to a larger evidence set rather than merely copying fields from one page.

Likely pitfalls: A model may approve the clearance because leave and payroll are valid, choose a draft payroll or obsolete leave record, ignore the missing folder file, treat the notice message as adequate despite no acknowledgement deadline, or cite a non-controlling audit event.
