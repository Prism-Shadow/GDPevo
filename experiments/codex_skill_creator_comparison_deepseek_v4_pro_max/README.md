# Codex Skill-Creator Comparison: DeepSeek V4 Pro Preview max

This directory contains the reports for the Codex-harness skill-creator
comparison using the preview model identified on the wire as
`deepseek-ai/DeepSeek-V4-Pro`, with `max` reasoning effort.

The harness, model, prompts, task inputs, and shared base attempts are fixed.
The only few-shot treatment variable is the pinned creator bundle used to
generate the skill: `codex`, `cc`, `deepagents`, `opencode`, or the minimal
prompt-only `naive` control.

## Coverage

- 24 task groups.
- One shared base branch per task group.
- Five creator-specific few-shot branches per task group.
- Three generation attempts per creator.
- Five test tasks and three solver attempts per condition.
- All six conditions have usable fixed-denominator results for all 24 task
  groups.

The original layer contains the shared base and four externally sourced
creator conditions. The naive control was run later as a separate supplement.
Logical failures retained by the bounded-retry policy count as zero; obsolete
physical runs and infrastructure replacements are not counted again.

## Aggregate Accuracy

The table reports the macro mean of each task group's `overall_acc_at_3`.

| Condition | Mean accuracy | Lift over shared base |
| --- | ---: | ---: |
| Base | 42.4795% | — |
| Codex creator | 47.0522% | +4.5727 pp |
| CC creator | 46.7351% | +4.2556 pp |
| DeepAgents creator | 47.7472% | +5.2676 pp |
| OpenCode creator | 47.8354% | +5.3559 pp |
| Naive creator | 48.0145% | +5.5350 pp |

The naive control is +0.9623 pp over Codex creator, +1.2794 pp over CC,
+0.2674 pp over DeepAgents, and +0.1792 pp over OpenCode on this 24-group
macro average. These are descriptive results for this experiment, not a claim
that the minimal prompt will dominate on other models or task distributions.

## Recovery and audit provenance

The original creator layer uses bounded logical-retry reports for task groups
007, 011, 021, 022, 023, and 024. Task group 016 comes from its clean rerun.
All other task groups use their canonical complete report.
The six recovery reports retain their native audit schema: the selected
publication metrics are under `bounded_retry_v1` (or `bounded_retry_v2` for
task group 022), so the recovery ledger and the reported scores remain in one
verifiable artifact.

Nine naive task groups completed in their strict supplement. The other 15 use
explicitly labelled bounded logical-retry reports. Naive task group 021 has one
additional post-run canonical-evaluator audit: the selected physical run ended
with an outer agent failure but retained an evaluable `answer.json`. The audit
score of `0.23529411764705882` is applied to that logical slot in the
publication copy, which records both the raw failure and the audit provenance.
The source workspace report remains unchanged.

## Layout

- `config.yaml` records the fixed experiment dimensions and report selection.
- `reports/task_group_001.yaml` through `task_group_024.yaml` contain base and
  the four externally sourced creator conditions.
- `reports/naive_supplement/task_group_001.yaml` through
  `task_group_024.yaml` contain the naive-only supplement results.

Generated skills and raw traces are not included in this report repository.
The publication copies preserve the canonical metrics, recovery labels, and
audit structure while replacing host-specific absolute path prefixes and
provider bridge addresses with explicit redaction placeholders. The original
byte-identical reports, selected primary traces, metadata, manifests, and audit
artifacts are published separately in `Prism-Shadow/GDPevo_rawdata`.
