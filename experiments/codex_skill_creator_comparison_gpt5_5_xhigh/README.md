# Codex Skill-Creator Comparison: GPT-5.5 xhigh

This directory contains the reports for the Codex-harness skill-creator
comparison using GPT-5.5 with `xhigh` reasoning effort.

The harness, model, prompts, task inputs, and shared base attempts are fixed.
The only few-shot treatment variable is the pinned creator bundle used to
generate the skill: `codex`, `cc`, `deepagents`, or `opencode`.

## Coverage

- 24 task groups.
- One shared base branch per task group.
- Four creator-specific few-shot branches per task group.
- Three generation attempts per creator.
- Five test tasks and three solver attempts per condition.
- All 24 reports and all five branches in each report are complete.

Each task group is supported by 87 selected primary Codex traces: 12 skill
generation traces, 15 shared base solver traces, and 60 few-shot solver
traces. Raw traces are stored separately in the `GDPevo_rawdata` repository.

## Aggregate Accuracy

The table reports the macro mean of each task group's `overall_acc_at_3`.

| Condition | Mean accuracy | Lift over shared base |
| --- | ---: | ---: |
| Base | 49.6595% | — |
| Codex creator | 62.1858% | +12.5264 pp |
| CC creator | 62.1512% | +12.4918 pp |
| DeepAgents creator | 62.6908% | +13.0313 pp |
| OpenCode creator | 60.7859% | +11.1264 pp |

## Layout

- `config.yaml` records the fixed experiment dimensions.
- `reports/task_group_001.yaml` through `task_group_024.yaml` are the
  canonical complete task-group results.

The 24 report files are byte-identical copies of the final canonical workspace
reports. Their `skill_dir` values therefore remain workspace-relative audit
provenance. Generated skill packages are not included in this report-only
publication and can be reviewed as a separate artifact change. Task groups
001 and 009 use the selected logical-recovery results recorded by their final
canonical reports; old first-pass reports are not published.
