# Globex North Q2 QBR Metrics Packet Notes

## English

### Data Lineage
- Source environment: ApexCloud Retention Operations API and its generated data under `task_group_004/env`.
- Account: `acct_globex_north`, legal name `Globex North Holdings LLC`.
- Period: `2026-Q2`, covering `2026-04-01` through `2026-06-30`.
- Revenue lineage: monthly account metrics `recognized_revenue`.
- Support and SLA lineage: account ticket export for the Q2 date range.
- NPS lineage: account NPS response export for the Q2 date range.

### Task Definition
The solver must create a formal JSON QBR metrics packet with monthly revenue, support ticket volume, SLA compliance, NPS, quarter highlights, source labels, internal review routing, and an ordered four-topic client agenda.

### Scenario Fit
This task fits a customer success director preparing QBR material for a deck, internal review, and client discussion. It requires reconciling metrics from several endpoint families without revealing hidden construction conventions in the user-facing prompt.

### Material Map
- `input/prompt.txt`: solver-facing request, account, quarter, endpoint hints, and required JSON shape.
- `input/payloads/answer_template.json`: empty structured response template.
- `output/answer.json`: canonical expected business result.
- `eval/eval.sh`: weighted evaluator for a submitted prediction or the canonical answer.

### Solution and Evaluation Basis
- Q2 revenue values are April `95756.67`, May `98509.22`, and June `105156.27`.
- Clean support ticket counts are April `4`, May `4`, and June `1`.
- SLA compliance is April `100.0`, May `75.0`, and June `100.0`.
- NPS values are April `45`, May `61`, and June `56`.
- Average revenue is `99807.39`; peak revenue is June at `105156.27`.
- Maximum SLA is `100.0`, represented by the first month reaching the maximum, April.
- Peak NPS is May at `61`; ticket trend is `improving`.
- Review routing is `customer_success`, due `2026-07-22`, with no technical signoff required.
- The evaluator uses eight weighted business-result checks matching the rubric plan.

### Transfer Design
This train task teaches QBR metric-source usage, support/NPS cleaning implications, highlight calculations, and review routing in a compact account-specific packet. The same pattern transfers to other accounts and quarters with different support, SLA, and NPS edge cases.

### Construction Record
Created the task folder contents only under `train_tasks/002/`. The answer was derived from the shared environment data and the hidden shared business rules. No generated environment source files were copied into the task payloads.

