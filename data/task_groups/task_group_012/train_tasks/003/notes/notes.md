# Task Notes
## English

Task definition and business objective: This train task reconciles recruitment opening `REQ-DA-77`. The solver must determine candidate outcomes, accepted offer details, recruitment cost total, notice follow-up obligations, and payroll handoff readiness. It is a formal PeopleOps reconciliation task, not a tutorial.

Visible inputs and Web evidence: The solver-visible prompt gives the local PeopleOps Console URL, login, opening ID, and answer template. Evidence should be collected from Recruitment candidate review, offer register, cost ledger, notice packets/messages, related case detail, policy viewer, payroll handoff or precheck evidence, and audit evidence available through the app.

Expected reasoning and answer basis:
- Use candidate review plus offer evidence to classify `CAND-DA-7701` as selected, `CAND-DA-7702` as waitlisted, and `CAND-DA-7703` as rejected.
- Use offer `OFFER-DA-7701`, accepted status `accepted`, and salary `112000`.
- Sum cost ledger lines to `6200`.
- Use `notice_packet_inspection` as the notice quality source.
- Include `CAND-DA-7702` and `CAND-DA-7703` in `notice_followup_required`.
- Use `send_waitlist_notice` for the waitlisted candidate and `send_rejection_notice` for the rejected candidate.
- Use `accepted_offer_only` as the payroll handoff gate and `submitted_after_acceptance` as the required payroll status.
- Set `draft_payroll_allowed` to `false`, and use `no_accepted_status_or_offer` to explain why a waitlisted candidate must not be routed to offer/payroll.
- Return `create_payroll_precheck` as the onboarding handoff and `submitted_handoff_required_after_acceptance` as the final handoff control result.

Transferable SOP and field conventions: This train task teaches several conventions used later in recruitment tests: candidate outcomes must come from committee/interview plus offer confirmation; accepted offers gate payroll handoff; waitlisted candidates are not offer/payroll eligible; recruitment cost must come from the cost ledger; notice actions must distinguish waitlist notices from rejection notices; and control fields must use exact normalized labels.

Likely pitfalls: Copying only the recruitment summary; omitting the waitlisted or rejected candidate from follow-up; summing only part of the cost ledger; treating waitlisted status as an accepted offer; allowing draft payroll handoff; or using free-text status labels instead of `committee_decision_with_offer_confirmation`, `accepted_offer_only`, and `submitted_handoff_required_after_acceptance`.

Evaluator/scoring basis: `eval/rubric.json` has six exact-match scoring points: opening/outcomes, candidate outcome control, accepted offer/cost, notice follow-up, handoff gate, and draft/waitlist exclusion. High-value checks include normalized labels such as `candidate_status_source`, `candidate_outcome_control`, `notice_quality_source`, `payroll_handoff_gate`, `payroll_assignment_status_required`, and `handoff_control_result`.

Construction/rework note: This task was reworked to be Web-first and to provide reusable train coverage for recruitment normalized labels, source precedence, notice follow-up, and payroll handoff gates. This notes file now reflects all current answer and scoring fields.

