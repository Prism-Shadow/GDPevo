# Northstar Playbooks

## Contents
- [Shared rules](#shared-rules)
- [UM nurse determination](#um-nurse-determination)
- [Pharmacy appeal and assistance](#pharmacy-appeal-and-assistance)
- [Claim repricing](#claim-repricing)
- [Peer-to-peer summary](#peer-to-peer-summary)
- [Margin queue summary](#margin-queue-summary)
- [Basis audit](#basis-audit)

## Shared rules
- Use `task_context` as the source of truth for IDs, dates, tokens, queue row order, and memo constraints.
- Keep only the fields required by the active template.
- Normalize values exactly as requested: dates in `YYYY-MM-DD` or `YYYY-MM`, money as JSON numbers rounded to cents, ratios to the requested precision, and absent modifiers as `null`.
- Keep ordered lists in the template-specified order. Do not sort unless the template says to sort.
- Use empty lists when the template expects a list and no items apply.
- Do not add narrative outside JSON.

## UM nurse determination
- Review the case, active member and plan context, requested therapy lines, policy criteria, clinical documents, and authorization record.
- Fill `criteria_results` for `PT-ACTIVE`, `PT-DEFICIT`, `PT-DX`, `PT-POC`, and `PT-UNITS`.
- Put current evidence documents relied on in `evidence_documents`.
- Put considered but excluded case documents in `excluded_documents`.
- Set `authorization` from the controlling authorization record.
- Choose `recommendation`, `final_status`, `route`, `determination_letter`, and `next_action` from the reviewed evidence.
- Use `current_clinical_records_over_stale_export`.

## Pharmacy appeal and assistance
- Review the appeal record, denial notice, medication trial history, prescriber rationale, and assistance-screen facts.
- Classify documented medication failures separately from undocumented or insufficient failures.
- Sort medication names alphabetically in both failure lists.
- Build `required_packet_items` and `missing_packet_items` with appeal evidence before assistance items.
- Set `assistance.program_name`, `assistance.status`, and `assistance.missing_fields` from the program facts.
- Use `payer_appeal_before_manufacturer_assistance`.
- Use `appeal_deadline_then_clinical_then_payment_integrity` when timeliness controls whether the packet can proceed.

## Claim repricing
- Review the claim header, claim lines, case context, policy context, and rate schedules.
- Select the benchmark that matches the active plan, modifier, and date.
- Reject stale or distractor schedule data when it does not govern the result.
- Keep `lines` in source claim line order.
- Use `null` for missing modifiers.
- Compute each line and total amount to cents, then set `recovery_amount`, `resubmission_route`, and `priority`.
- Use `effective_benchmark_by_plan_modifier_and_date`.

## Peer-to-peer summary
- Review the case record, requested line, policy criteria, clinical evidence, P2P event, and authorization status.
- Determine whether new patient-specific information changed the review.
- Map `criteria_results` for `PET-IND` and `PET-FACTOR`.
- List unresolved criteria in ascending criterion order.
- List unsupported PET-specific factors in the template order.
- Set `recommended_alternative` only when it follows from the final review.
- If the final result is adverse, set `internal_appeal_deadline` to 180 days after the adverse determination date.
- Use `new_patient_specific_p2p_information`.

## Margin queue summary
- Review only the queue row IDs named in `task_context`.
- Preserve queue row order in `rows`.
- Derive `below_threshold` from the 1.2 revenue-to-cost threshold.
- Derive `charge_sensitive` from the finance memo.
- Set `recommended_action` from the row classification.
- Build `below_threshold_segments` and `charge_sensitive_segments` alphabetically.
- Set `top_issue` to the worst below-threshold segment/CPT combination by shortfall to 120 percent of cost.
- Compute `gap_to_120pct` as the shortfall from actual revenue to 120 percent of cost, rounded to cents.
- Use `margin_threshold_then_charge_sensitivity`.

## Basis audit
- Choose the source-precedence label that matches the governing rule for the packet.
- Put the highest-priority controlling record first in `precedence_record_order`.
- Put the records that directly control the result in `controlling_record_ids`.
- Put stale, excluded, missing, or lower-priority records in `exception_record_ids`.
- Use `appeal_deadline_then_clinical_then_payment_integrity` when a deadline or filing window controls the route or eligibility.
