# Notes

## English

Data/source lineage: This test task belongs to `SCN_012_erp_hr_employee_lifecycle` and adapts the recruitment, offer, notice, payroll handoff, and audit-control patterns into opening `REQ-OPS-19`. The solver-visible prompt gives only the business request, local URL, login, and output contract. The answer facts must be found in the PeopleOps Console.

Task definition: The solver must reconcile the candidate outcome, accepted offer, cost ledger, waitlist notice defect, payroll handoff gate, draft exclusion, and supporting audit event. Evidence is intentionally distributed across Recruitment candidate review, offer register, cost ledger, notice inspection, Messages, Policy Viewer, related case detail, and Audit Log.

Solution and evaluation basis: Gold identifies `CAND-OPS-1902` as selected, `CAND-OPS-1901` as waitlisted, and `CAND-OPS-1903` plus `CAND-OPS-1904` as rejected. Offer `OFFER-OPS-1902` is accepted with base salary `124000`. Cost ledger total is `7350`. The defective notice belongs to `CAND-OPS-1901` with defect `missing_waitlist_status`, requiring `reissue_waitlist_notice_not_rejection`. The already-sent rejected-candidate notices require `no_action`. Payroll handoff requires `create_submitted_assignment_after_acceptance`, with gate `accepted_offer_only`, required status `submitted_after_acceptance`, policy `PAY-SRC-001`, and exclusion of draft precheck `PAY-PRECHECK-OPS-1901-D`. Supporting audit event is `AUD-REQOPS-11`.

Transfer design: This task deliberately combines 2-3 train anchors. `train_003` transfers candidate outcome reconstruction, accepted-offer use, recruitment cost summing, and notice follow-up conventions. `train_005` transfers submitted-versus-draft payroll assignment handling. `train_002` transfers formal notice defect review and use of audit evidence. The test-specific work is finding the new opening's evidence and applying those conventions across more modules.

Likely pitfalls: Copying the recruitment summary without opening the review panels; treating the waitlisted candidate as offer-eligible; accepting a draft payroll precheck; omitting one rejected candidate; taking notice quality from status alone without inspecting the message; or citing the case instead of the audit event.
