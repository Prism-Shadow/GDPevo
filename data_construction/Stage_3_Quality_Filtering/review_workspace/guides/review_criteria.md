# Review Criteria

## Scripted Check Scope

`check_task_group.py` checks deterministic conditions only:

- `task_group.yaml` parses and contains `task_group`, `env`, `train_tasks`, and `test_tasks`.
- `train_tasks` and `test_tasks` each contain 5 tasks.
- Each declared task contains `input/`, `prompt.txt`, `payloads/answer_template.json`, `notes/notes.md`, `output/answer.json`, `eval/eval.sh`, and evaluator files.
- Environment files declared in `env.setup` and `env.files` exist.
- `env.files` declares `env/judge_api.py` for the required train-only judge endpoint.
- All JSON/YAML files parse.
- Each task's `eval.rubric` has 6-10 items, and every item has `goal` plus an integer `weight` in `{1, 2, 3}`.
- Each task evaluator gives full credit to the reference answer. The script only requires evaluator stdout to be JSON and supports common full-credit fields such as `score`, `normalized_score`, `earned_score/max_score`, `earned_weight/total_weight`, `passed`, `points`, or `checks`.
- `notes/notes.md` contains at least Chinese notes; Chinese should appear only in `notes/notes.md`.

The script does not judge business realism, task difficulty, transfer design, rubric independence, semantic weight appropriateness, leakage risk, or evaluation design quality. Reviewer subagents must judge those.

## Reviewer Inputs

Each reviewer must read both:

```text
task_group/<task_group_id>/
scratch/
```

`task_group/` is the formal benchmark data. `scratch/` is a copy of the Stage 2 `task_factory/scratch` material; it is not solver-visible input and is not part of the final evaluation tasks. Reviewers may use it to inspect design, calibration, attempts, and rework history.

`scratch/` may contain reference answers, construction truth, generated fewshot skill packages, skill-generation traces, calibration logs, and rework history. These do not count as leakage by themselves. Leakage checks only apply to solver-visible formal task group surfaces: `input/prompt.txt`, `input/payloads/`, `answer_template.json`, public APIs, public web pages, public databases, or other runtime entry points. If answers, SOPs, or construction truth from `scratch/` are copied into those solver-visible surfaces, mark it as leakage.

## Reviewer Checks

Each reviewer must independently check:

| Check | Focus |
| --- | --- |
| `scenario_lineage` | Whether the task group comes from examples under one scenario and preserves the difficulty drivers from the source examples. |
| `train_predict_design` | Whether train/test are all real tasks; train tasks are not tutorials; test tasks require transferable experience from train. |
| `transfer_band` | Whether diversity sits within a transferable band, with 2-3 recurring operation families rather than unrelated one-off SOPs. |
| `environment_design` | Whether `env/` is a shared public data and workspace environment; it runs outside agent containers; Dockerized agents can reach it through a verified network route without mounting env source or truth. |
| `leakage_control` | Whether solver-visible formal task group surfaces leak answers, complete SOPs, scoring points, construction truth, or solution steps; drafts and answers in `scratch/` do not count as leakage evidence. |
| `notes_interpretability` | Whether each task has bilingual `notes/notes.md` explaining the problem, answer basis, transfer source, common pitfalls, and scoring standard. |
| `rubric_independence` | Whether every task evaluates at least 3 independently fail-able business questions/aspects; points do not merely duplicate one root decision; and `scratch/rubric_validation.md` uses selective perturbations to show that points do not all rise or fall together. |
| `evaluation_design` | Whether evaluation uses deterministic checks around key business outcomes, supports documented within-point partial credit where the outcome naturally decomposes, and avoids schema friction, free-text matching, and point stuffing. |
| `difficulty_calibration` | Whether base/fewshot attempts are isolated Dockerized `codex exec` runs with fixed prompts and traces; overall base `avg@3` is about `0.40-0.60`; fewshot gain is about `0.10-0.20`; and most tasks do not score `0.95` or higher or otherwise approach a perfect score. |
| `construction_process` | Whether records show env-builder and task-builder subagents plus 3 isolated Dockerized fewshot skill-generation processes, solver calibration, review/rework, and complete run evidence. |
| `overall` | Whether the task group is ready for the final evaluation pool. |

The reviewer's `decision` should reflect overall quality. Small issues that do not harm benchmark validity can be `pass` with `concerns`. Answer leakage, untrustworthy evaluation, invalid train/test transfer, missing structure, or invalid calibration should be `fail`.

## Common Fail Reasons

- Solver-visible prompts, payloads, answer templates, or public environment entry points directly include SOPs, answer facts, scoring points, or solution steps.
- Answers, construction truth, or calibration logs from `scratch/` are copied into solver-visible surfaces.
- `env/` provides an answer calculator, task-specific data package, or near-answer endpoint such as `/api/tasks/<task_id>/data`.
- Calibration or evaluation mounts `env/` into an agent container, uses the container's own `localhost` for an external API, or lacks a successful container-side health check for the configured route.
- Test tasks can score well without transfer from train tasks.
- The apparent 6-10 rubric rows mostly depend on one answer field or upstream decision, so they all pass or fail together.
- `scratch/rubric_validation.md` is missing, selective wrong-aspect probes collapse most points together, or naturally decomposable points provide only full-or-zero credit without justification.
- Overall base score falls outside the approximate `0.40-0.60` target, fewshot gain falls outside the approximate `0.10-0.20` target without a convincing explanation, or most tasks score `0.95` or higher or otherwise approach a perfect score.
- Difficulty evidence comes from orchestration subagents, hand-authored predictions, non-fixed prompts, or runs without isolated staged work and preserved Codex traces.
- Evaluation scores free text, evidence phrasing, format friction, or unrelated fields instead of key business outcomes.
- Notes omit transfer source, answer basis, or scoring standard, making the data hard to interpret.
- Multi-agent construction records are missing, or all env/task/answer/notes/eval assets were clearly generated by one monolithic script.
