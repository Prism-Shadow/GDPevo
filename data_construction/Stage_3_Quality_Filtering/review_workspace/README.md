# Quality Review Workspace

`review_workspace/` is the Stage 3 quality review entry point. You are the lead review agent for this stage. Your goal is to decide whether one completed and calibrated `task_group` is ready for the final evaluation pool.

This workspace reviews one task group at a time. Run the deterministic structure check, coordinate 6 clean-context reviewer subagents, and summarize the script result, the 6 votes, and the final decision in one review report.

Review is not continued data generation and not automatic filtering. Do not modify the candidate task group. If you find issues, record them in the report and send the group back to Stage 2 for rework.

`task_group/` contains only the formal benchmark data. `scratch/` contains the matching Stage 2 `task_factory/scratch` material. Scratch records are not solver-visible inputs and are not part of the formal task group; they may include reference answers, construction drafts, calibration logs, and reflection notes. That material does not count as leakage by itself.

## Directories

| Path | Purpose |
| --- | --- |
| `guides/` | Review workflow, criteria, and report format. |
| `scripts/` | Deterministic structure-check scripts. |
| `task_group/` | The single task group currently under review. |
| `scratch/` | The matching Stage 2 `task_factory/scratch` material plus temporary review notes. |

Write the final review report to:

```text
../reports/<task_group_id>.yaml
```

## Guides

Read these guides before reviewing:

1. `guides/workflow.md` - Stage 3 workflow and 6-vote mechanism.
2. `guides/review_criteria.md` - Script checks and reviewer criteria.
3. `guides/report_format.md` - Final report format.

## Workflow

1. Confirm that `task_group/` contains exactly one candidate directory:

```text
task_group/<task_group_id>/
```

2. Confirm that `scratch/` contains the matching Stage 2 scratch material:

```text
scratch/
```

This scratch material comes from Stage 2 `task_factory/scratch`. Reviewers may use it to inspect design notes, calibration attempts, trial results, and rework history. Do not treat answers or construction truth in `scratch/` as leakage by themselves. Leakage checks only apply to solver-visible formal task group surfaces, such as prompts, payloads, answer templates, and public environment entry points.

3. Run the scripted structure check:

```bash
python3 scripts/check_task_group.py task_group/<task_group_id>
```

4. If the script fails, stop before reviewer voting. Record the failure in the report and send the task group back to Stage 2.

5. If the script passes, launch 6 clean-context reviewer subagents. Each reviewer independently reads the same task group and matching scratch material, then returns `pass` or `fail` using `guides/review_criteria.md`.

6. Save raw reviewer conclusions in `scratch/`, then write the summary report to `../reports/<task_group_id>.yaml`.

7. The task group passes Stage 3 only when the script passes and at least 5 of 6 reviewers vote pass.

## Review Principles

- The script checks deterministic structure and consistency only; it does not judge data quality.
- The 6 reviewers must have clean contexts. They must not see each other's conclusions, and the lead agent must not simulate all votes in one context.
- Reviewers judge whether the task group is suitable benchmark data, not merely whether files exist.
- Use `task_group/` and `scratch/` to check scenario lineage, train/test transfer design, transferable diversity, environment/container boundaries, leakage risk, note interpretability, evaluator trustworthiness, rubric independence and partial-credit behavior, Dockerized difficulty calibration, and the construction process. Leakage risk only applies to the formal solver-visible task group surfaces, not construction evidence in `scratch/`.
- Minor issues can be recorded as `concerns`; answer leakage, untrustworthy evaluation, invalid transfer, failed calibration, or missing structure should be `fail`.
- A reworked task group must rerun the script check and receive a fresh 6-vote review. Do not reuse old votes.

## Reviewer Prompt

Use this short prompt for each reviewer subagent:

```text
Please independently review <task_group_path> and scratch/ using guides/review_criteria.md as the standard. Inspect the actual evaluators and scratch/rubric_validation.md; verify that each task measures multiple independently fail-able business aspects, that selective mistakes do not make all rubric points move together, and that deterministic partial credit works where specified. Also verify the fixed-prompt Dockerized Codex calibration evidence. Do not use other reviewers' conclusions. Return one vote: pass or fail, with concise support for each required check.
```
