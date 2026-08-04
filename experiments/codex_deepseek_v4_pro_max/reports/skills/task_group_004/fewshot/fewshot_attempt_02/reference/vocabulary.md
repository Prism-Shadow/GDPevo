 # Controlled vocabularies

 Every enum field in the output must use exactly one of the values listed below. Pipe-delimited labels in templates (e.g. `critical|high|medium|low`) are a pick-list, not a literal to output.

 ## Risk levels

 - `critical` — imminent churn or severe revenue exposure with multiple compounding risk signals.
 - `high` — significant risk that demands proactive intervention this quarter.
 - `medium` — moderate risk; monitor closely and prepare contingency.
 - `low` — stable account with no urgent action required.

 ## Primary actions

 - `executive_qbr` — schedule an executive business review; appropriate for strategic accounts with expansion potential despite risk.
 - `collections_followup` — pursue overdue receivables; use when the dominant risk driver is unpaid invoices.
 - `technical_recovery` — deploy technical resources to address SLA failures, usage decline, or product-health issues.
 - `renewal_save` — initiate a structured renewal save play; use when the account is in or near a renewal window with elevated risk.
 - `nurture_monitor` — maintain regular cadence and watch for emerging signals; appropriate for low-risk accounts that still warrant attention.
 - `no_action` — no immediate action required.

 ## Reason codes

 - `overdue_receivable` — account has overdue balances in one or more aging buckets.
 - `low_tenure_high_churn` — account tenure is low relative to the cohort, indicating elevated churn probability.
 - `sla_degradation` — SLA compliance dropped below acceptable thresholds during the analysis period.
 - `nps_drop` — NPS score declined materially (≥10 points) or sits below 30.
 - `usage_decline` — product usage (active users, license utilization, or usage units) trended downward.
 - `renewal_window` — the account's renewal date falls within or near the analysis period.
 - `expansion_offset` — the account has open expansion pipeline that may partially offset risk.
 - `clean_billings` — no overdue receivables and billing is current.

 ## Ticket trend labels

 - `improving` — ticket count decreased across the period.
 - `worsening` — ticket count increased across the period.
 - `flat` — ticket count was stable across the period.

 ## Metric source labels

 - `crm_closed_won` — revenue data sourced from closed-won CRM opportunities.
 - `support_export` — ticket data sourced from support system export.
 - `sla_report` — SLA compliance data sourced from the SLA reporting system.
 - `nps_survey` — NPS data sourced from survey responses.
 - `billing_snapshot` — revenue/ARR data sourced from billing snapshots.
 - `ar_aging` — data sourced from accounts receivable aging reports.
 - `pipeline_crm` — data sourced from CRM pipeline/opportunity records.
 - `event_dashboard` — data sourced from the event performance dashboard.
 - `hr_report` — data sourced from HR system reports.

 ## Review owners

 - `solutions_engineering` — review owned by the solutions engineering / technical team.
 - `customer_success` — review owned by the customer success team.
 - `finance_ops` — review owned by finance operations.

 ## QBR agenda topics

 Ordered pick-list of exactly four from:
 - `partnership_overview`
 - `q2_metrics`
 - `performance_highlights`
 - `q3_initiatives`
 - `technical_recovery`
 - `commercial_expansion`

## Link status

 - `linked` — the A/R customer name matches a CRM account.
 - `unlinked` — the A/R customer name has no matching CRM account.

 ## Accuracy bands

 - `below_70` — accuracy < 70%.
 - `70_to_79` — accuracy 70-79%.
 - `80_to_89` — accuracy 80-89%.
 - `90_plus` — accuracy ≥ 90%.

 ## Tenure risk direction

 - `negative` — higher tenure is associated with lower churn risk (the typical pattern).
 - `positive` — higher tenure is associated with higher churn risk.
 - `zero` — tenure shows no directional relationship with churn.
 - `not_assessed` — tenure-risk relationship was not evaluated in this run.

 ## Outreach actions (churn model context)

 - `renewal_save` — target the account with a renewal save play.
 - `technical_recovery` — target the account with a technical recovery intervention.
 - `collections_followup` — target the account with collections outreach.
 - `nurture_monitor` — monitor the account; risk is low but maintain engagement.

 ## Policy-code families

 Each policy-code field in the output must hold a single code selected from its family's option set (the pipe-delimited list in the template). The code you choose should reflect the actual methodology used in the current analysis run.

 Common families:

 - **Risk model**: `RS-2`, `RS-6`, `RS-9` — codes indicating which risk-scoring methodology was applied.
 - **ARR source**: `REV-1`, `REV-4`, `REV-8` — codes indicating which revenue data source was used.
 - **Support hygiene**: `SUP-3`, `SUP-8`, `SUP-9` — codes indicating which support-data handling rules were applied.
 - **Action priority**: `ACT-1`, `ACT-5`, `ACT-7` — codes indicating the action-prioritization framework.
 - **Receivable trigger**: `RCP-4`, `RCP-7`, `RCP-9` — codes for the receivables trigger methodology.
 - **CRM match**: `CM-2`, `CM-5`, `CM-8` — codes for the CRM matching methodology.
 - **Pipeline window**: `PW-3`, `PW-6`, `PW-9` — codes for the pipeline window methodology.
 - **Followup scope**: `FS-1`, `FS-4`, `FS-8` — codes for the followup scope methodology.
 - **Board sort**: `BORD-1`, `BORD-4`, `BORD-8` — codes for the board sort methodology.
 - **Exposure formula**: `EXP-2`, `EXP-6`, `EXP-9` — codes for the net revenue exposure formula.
 - **Calendar policy**: `CAL-3`, `CAL-5`, `CAL-7` — codes for the followup calendar methodology.
 - **Model protocol**: `MOD-2`, `MOD-7`, `MOD-9` — codes for the churn model protocol.
 - **Probability scale**: `PRB-1`, `PRB-4`, `PRB-8` — codes for the probability scaling methodology.
 - **Deployment rule**: `DEP-3`, `DEP-5`, `DEP-9` — codes for the deployment rule set.
 - **Outreach mapping**: `OUT-2`, `OUT-6`, `OUT-8` — codes for the outreach-action mapping methodology.
