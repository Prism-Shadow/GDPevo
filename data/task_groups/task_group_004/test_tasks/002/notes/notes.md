# Lumen Rail Q3 QBR Readiness Packet Notes

## English

### Data lineage
- Source service: ApexCloud Retention Operations API on port 8074.
- Source files used for construction: `accounts.json`, `account_metrics.json`, `support_tickets.json`, and `nps_responses.json`.
- Account scope: `acct_lumen_rail`, legal name `Lumen Rail Systems Ltd.`.
- Period scope: 2026-Q3, months `2026-07`, `2026-08`, `2026-09`, date range `2026-07-01` through `2026-09-30`.

### Task definition
- The solver must produce a formal QBR readiness packet with monthly metrics, highlights, metric source labels, review routing, and a client meeting plan.
- The visible prompt gives the API and endpoint families, the requested account and period, the exact output shape, due dates, channel slug, meeting date, and controlled enum choices.

### Scenario fit
- This is a Customer Success readiness task, matching the QBR rollup conventions from the training anchor.
- It also exercises risk-aware agenda selection because Lumen Rail has a September SLA deterioration and a September NPS decline from the August peak.

### Material map
- Revenue is sourced from monthly account metrics recognized revenue.
- Support tickets are derived from the support export for the requested date range.
- SLA compliance is derived from support ticket SLA outcomes.
- NPS is derived from valid survey responses in each month.
- Review routing is derived from the quarter-level service reliability pattern.

### Solution and evaluation basis
- Monthly rows are ordered July, August, September 2026.
- Revenue values are `94016.00`, `99027.22`, and `100184.47`.
- Support ticket counts are `5`, `4`, and `4`.
- SLA compliance values are `100.0`, `100.0`, and `50.0`.
- NPS values are `67`, `74`, and `54`.
- Highlights: average revenue `97742.56`, peak revenue month `2026-09`, peak revenue `100184.47`, max SLA month `2026-07`, max SLA `100.0`, peak NPS month `2026-08`, peak NPS `74`, average SLA `83.3`, total support tickets `13`.
- The evaluator checks exact business outputs with the rubric weights from the task brief and accepts an optional prediction path.

### Transfer design
- The task transfers the same QBR monthly rollup and metric source conventions as `train_002`.
- The client agenda transfers the risk-aware selection pattern from `train_005` while using this test task's own agenda and risk theme enums.

### Construction record
- Built inside `test_tasks/002/` only.
- No environment source data was copied into solver-visible payloads.
- `eval/eval.sh` evaluates the bundled answer by default and supports a caller-provided prediction JSON path.

