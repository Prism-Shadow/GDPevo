# Review Workflow

## Goal

Stage 3 decides whether one constructed and calibrated `task_group` is ready for the final evaluation pool. Review is not an automatic filtering pipeline; it uses multiple clean-context reviewers to independently judge data quality.

## Input Convention

At the start of review, `review_workspace/` should contain one candidate task group:

```text
task_group/<task_group_id>/
```

and the matching Stage 2 scratch material:

```text
scratch/
```

`task_group/` contains only the formal benchmark data. `scratch/` contains the Stage 2 `task_factory/scratch` material. These records are not solver-visible inputs and are not part of the formal task group, but reviewers may use them as evidence. `scratch/` may contain reference answers, construction drafts, calibration logs, and reflection notes; that alone does not count as answer leakage.

`review_workspace/` is a temporary review workspace and reviews one task group at a time.

## Agent Workflow

1. The lead agent reads `task_group/<task_group_id>/` and `scratch/`, confirming that both correspond to the same task group. Do not modify the formal candidate task group.

2. The lead agent runs the scripted structure check:

```bash
python3 scripts/check_task_group.py task_group/<task_group_id>
```

3. If the script fails, stop reviewer voting and record `script_check.pass: false` plus the failure reason in `../reports/<task_group_id>.yaml`.

4. If the script passes, the lead agent launches 6 clean-context reviewer subagents. Each reviewer independently reads the same task group and matching `scratch/`, including evaluator implementations, `rubric_validation.md`, fixed-prompt calibration records, and preserved run evidence, without seeing other reviewers' conclusions.

5. Each reviewer uses `review_criteria.md` and returns one vote:

```text
decision: pass
```

or:

```text
decision: fail
```

6. The lead agent summarizes the 6 votes into `review_votes`:

- When `pass_votes >= 5`, set `review_votes.pass: true`.
- When `pass_votes < 5`, set `review_votes.pass: false`.

7. The lead agent summarizes `manual_review` from the 6 reviewer conclusions and writes:

```text
../reports/<task_group_id>.yaml
```

8. If review fails, the report should explain what needs rework. A reworked task group must rerun the script check and receive a fresh 6-vote review; do not reuse old votes.

Script output, raw reviewer conclusions, and intermediate summaries can be stored in `scratch/review/`.

## Passing Rule

Passing review requires all of:

- `script_check.pass: true`
- `review_votes.pass: true`
- `manual_review.overall.pass: true`

## Reviewer Prompt

The lead agent can use this short prompt for each reviewer subagent:

```text
Please independently review <task_group_path> and scratch/ using guides/review_criteria.md as the standard. Inspect the actual evaluators and scratch/rubric_validation.md; verify that each task measures at least 4 independently fail-able business aspects, that every rubric point earns only full normalized credit or zero, that independently fail-able results are separate points, and that selective mistakes do not make unrelated points move together. Also verify the fixed-prompt Dockerized Codex calibration evidence. Do not use other reviewers' conclusions. Return one vote: pass or fail, with concise support for each required check.
```

Reviewers should judge whether the task group is valid benchmark data, not merely whether files exist.

Leakage checks only apply to solver-visible formal task group surfaces, such as prompts, payloads, answer templates, and public environment entry points. Do not mark leakage merely because `scratch/` stores answers, construction truth, or production records; it counts only if that material appears in solver-visible surfaces.
