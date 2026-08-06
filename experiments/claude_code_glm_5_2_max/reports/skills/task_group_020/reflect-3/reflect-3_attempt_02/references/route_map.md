# Workbench Route Map

Compact reference for the M&A deal workbench. Replace `<deal_id>`, `<playbook_id>`, `<policy_id>` with the values named by the task. All routes are GET (JSON) under `/api/...`.

## Deal resources
| Route | Returns | Key fields |
|---|---|---|
| `GET /api/deals` | all deals list | deal_id (use only to confirm the given id exists; many distractors) |
| `GET /api/deals/<deal_id>` | deal record | client_name, counterparty_name, client_side, currency, headline_value, upfront_cash, stock_value, milestone_value, playbook_id, policy_id, signing_date, meeting_date, transaction_type, strategic_context |
| `GET /api/deals/<deal_id>/terms` | current draft terms | term_id, category, clause_ref, draft_value, numeric_value, unit, basis, staleness_flag, source_document |
| `GET /api/deals/<deal_id>/consents` | third-party consents | consent_id, consent_type, contract_name, counterparty, required_for_closing (yes/no), risk_rating, amount_at_risk |
| `GET /api/deals/<deal_id>/material-contracts` | material contracts | contract_id, contract_name, contract_type, consent_required (yes/notice only/no), change_of_control, anti_assignment, annual_revenue |
| `GET /api/deals/<deal_id>/employees` | employee groups | employee_id, employee_group, count, pto_liability, service_credit_required, warn_risk, playbook_requirement |
| `GET /api/deals/<deal_id>/regulatory` | regulatory record | hsr_required, hell_or_high_water_required, regulatory_approval, threshold_basis |
| `GET /api/deals/<deal_id>/benchmarks` | benchmarks | benchmark_id, category, metric, sample_size, median_value, mean_value, upper_quartile |
| `GET /api/deals/<deal_id>/risk-estimates` | exposure estimates | estimate_id, category (closing certainty / indemnity leakage / transition disruption), exposure_low, exposure_high, confidence, method |
| `GET /api/deals/<deal_id>/diligence-findings` | findings | finding_id, topic, severity, source, amount |
| `GET /api/deals/<deal_id>/notes` | negotiation notes | note_id, author, topic, content, note_date |
| `GET /api/deals/<deal_id>/cap-table` | holders | holder, security_class, fully_diluted_pct, as_converted_shares, shares |
| `GET /api/deals/<deal_id>/documents` | documents | document_id, document_type, title, version, effective_date |

## Reference rules
| Route | Returns | Key fields |
|---|---|---|
| `GET /api/playbooks/<playbook_id>/rules` | playbook rules (PB_SELLER_A, PB_BUYER_A) | category, preferred_position, fallback_position, limit_value, limit_unit, basis, risk_default, required_action |
| `GET /api/policies` | policy list | policy_id, threshold_count |
| `GET /api/policies/<policy_id>/thresholds` | committee thresholds | category, policy_standard, threshold_value, threshold_unit, basis, restricted_flag, approval_required |

## Optional SQL
`POST /api/query` (token `deal-workbench-readonly`) for cross-table joins. The per-resource GETs above are sufficient for standard tasks.

## Field → answer-field mapping (transferable)
- `deal.headline_value` → top-level headline/purchase-price value (unless a rule states a different basis such as equity value).
- `term.numeric_value` + `term.unit` → the draft value cell for that issue category.
- `playbook.preferred_position` / `fallback_position` / `limit_value` → preferred/fallback cells; `risk_default` → risk_rating; `required_action` → recommended_action.
- `policy.threshold_value` / `threshold_unit` / `policy_standard` → policy_metric block; `restricted_flag=yes` + `approval_required=M&A Committee` → escalate; `restricted_flag=no` or stale → exclude.
- `consent.required_for_closing=yes` → required closing consent; `amount_at_risk` sums into consent-at-risk totals.
- `material_contract.consent_required=yes` → contract requiring consent; `annual_revenue` sums into revenue-conditioned totals; `notice only` → non-blocking notice.
- `risk_estimate.exposure_low/high` → quantified exposure ranges (include/exclude categories per template).
- `benchmark.median_value/upper_quartile` → benchmark block + `position`.
- `cap_table.fully_diluted_pct` → holder allocation (see quantification.md — it is a fraction).
