# Codex Skill-Creator Comparison: GPT-5.5 xhigh

This directory contains the reports for the Codex-harness skill-creator
comparison using GPT-5.5 with `xhigh` reasoning effort.

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
- All six conditions have usable results for all 24 task groups.

The original report layer contains the shared base and four externally sourced
creator conditions. The later naive experiment is published as a separate
supplement so that it is not represented as part of the original one-pass run.
For 23 task groups the strict naive supplement completed directly. Task group
019 uses the explicitly labelled `bounded_logical_retry_v2` result after its
strict supplement and first recovery remained incomplete.

## Aggregate Accuracy

The table reports the macro mean of each task group's `overall_acc_at_3`.

| Condition | Mean accuracy | Lift over shared base |
| --- | ---: | ---: |
| Base | 49.6595% | — |
| Codex creator | 62.1858% | +12.5264 pp |
| CC creator | 62.1512% | +12.4918 pp |
| DeepAgents creator | 62.6908% | +13.0313 pp |
| OpenCode creator | 60.7859% | +11.1264 pp |
| Naive creator | 65.1231% | +15.4636 pp |

The naive control is +2.9373 pp over Codex creator, +2.9719 pp over CC,
+2.4323 pp over DeepAgents, and +4.3372 pp over OpenCode on this 24-group
macro average. These are descriptive results for this experiment, not a claim
that the minimal prompt will dominate on other models or task distributions.

## Layout

- `config.yaml` records the fixed experiment dimensions.
- `reports/task_group_001.yaml` through `task_group_024.yaml` are the
  canonical complete original results for base and the four externally sourced
  creator conditions.
- `reports/naive_supplement/task_group_001.yaml` through
  `task_group_024.yaml` are the naive-only supplement results. The 019 file
  retains its bounded-recovery labels and provenance.

The publication copies preserve the canonical metrics, recovery labels, and
audit structure while replacing host-specific absolute path prefixes and
provider bridge addresses with explicit redaction placeholders. The original
byte-identical reports and raw traces remain in `Prism-Shadow/GDPevo_rawdata`.
Generated skill packages and raw traces are not included in this report-only
publication. Task groups 001 and 009 in the original layer use the selected
logical-recovery results recorded by their final canonical reports.
