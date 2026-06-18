# Notes for train_003

## English

This train task is derived from `E003`, the theatre CBA weekly payroll workbook. It targets production `PROD-HAMILTON-26` and uses the shared payroll rate book and production roster/schedule.

The task definition is to compute service counts, pay category totals, weekly total, per-musician totals, top-paid musician, and contract conflict flags. The visible materials are the prompt, environment access, payroll request, and answer template.

Material map: `/api/payroll/rate-book` provides service rates, time limits, premium percentages, doubles, vacation, substitute, and weekly guarantee rules. `/api/payroll/productions?production_id=PROD-HAMILTON-26` provides schedule rows and roster assignments.

The solution applies per-service pay, hourly rehearsal minimums, premium stacking, electronic substitute treatment, doubles, vacation, and guarantee adjustments. Conflict flags are derived from early rehearsals and services over CBA time limits. There are 8 scoring points with raw weights 2, 3, 2, 2, 3, 1, 2, and 2.

Transfer design: this formal train task teaches rate-book source precedence, schedule classification, premium stacking, substitute electronic treatment, and conflict-flag detection for `test_003`.
