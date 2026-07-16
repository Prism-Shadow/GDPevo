# Review Criteria

## Scripted Check Scope

`check_task_group.py` checks deterministic conditions only:

- `task_group.yaml` parses and contains `task_group`, `env`, `train_tasks`, and `test_tasks`.
- `train_tasks` and `test_tasks` each contain 5 tasks.
- Each declared task contains `input/`, `prompt.txt`, `payloads/answer_template.json`, `notes/notes.md`, `output/answer.json`, `eval/eval.sh`, and evaluator files.
- Environment files declared in `env.dockerfile`, `env.setup`, and `env.files` exist.
- `env.files` declares the exact path `env/Dockerfile`, and `env.state_mode` is either `read_only` or `mutable`.
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
| `environment_design` | Whether `env/Dockerfile` builds from the `env/` directory alone; the environment and agent run on a non-`--internal`, orchestrator-created bridge network that preserves outbound model-API access; the environment is reachable only as `http://task-env:<TASK_ENV_PORT>/` inside that network without publishing a host port; and no env source, database, truth, or Docker socket is mounted into the agent. |
| `environment_lifecycle` | Whether `env.state_mode` matches actual behavior: a `read_only` environment remains unchanged under concurrent attempts and is shared only within one capability stage, while every `mutable` attempt gets a clean environment instance and writable layer. Runtime names must include normalized `<user_name>`, task-group/stage/attempt scope, and a random suffix so concurrent experiments cannot collide. |
| `environment_capabilities` | Whether calibration and skill-generation/test stages expose only their allowed endpoints; `/api/judge` is registered only when `TASK_ENV_ENABLE_JUDGE=1` for the isolated train-feedback stage, and is absent or returns `404` when the flag is disabled. |
| `leakage_control` | Whether solver-visible formal task group surfaces leak answers, complete SOPs, scoring points, construction truth, or solution steps; drafts and answers in `scratch/` do not count as leakage evidence. |
| `notes_interpretability` | Whether each task has bilingual `notes/notes.md` explaining the problem, answer basis, transfer source, common pitfalls, and scoring standard. |
| `rubric_independence` | Whether every task evaluates at least 4 semantically distinct business outcomes and does not reward the same underlying criterion, answer fact, or root decision more than once. |
| `evaluation_design` | Whether evaluation uses deterministic whole-point checks around key business outcomes; every point earns all of its assigned score or zero; and schema friction, free-text matching, and point stuffing are avoided. |
| `difficulty_calibration` | Whether base/fewshot attempts are isolated Dockerized `codex exec` runs with fixed prompts and traces; overall base `avg@3` is about `0.40-0.60`; overall fewshot `avg@3` remains roughly below `0.80` with a gain of about `0.10-0.30`; and most tasks do not score `0.95` or higher or otherwise approach a perfect score. |
| `construction_process` | Whether records show env-builder and task-builder subagents plus 3 isolated Dockerized fewshot skill-generation processes, solver calibration, review/rework, and complete run evidence. |
| `overall` | Whether the task group is ready for the final evaluation pool. |

The reviewer's `decision` should reflect overall quality. Small issues that do not harm benchmark validity can be `pass` with `concerns`. Answer leakage, untrustworthy evaluation, invalid train/test transfer, missing structure, or invalid calibration should be `fail`.

## Common Fail Reasons

- Solver-visible prompts, payloads, answer templates, or public environment entry points directly include SOPs, answer facts, scoring points, or solution steps.
- Answers, construction truth, or calibration logs from `scratch/` are copied into solver-visible surfaces.
- `env/` provides an answer calculator, task-specific data package, or near-answer endpoint such as `/api/tasks/<task_id>/data`.
- `env/Dockerfile` cannot build from `env/` alone; the bridge is created with `--internal` and blocks model-API egress; calibration or evaluation publishes a host port, mounts `env/`, its SQLite database, truth, or the Docker socket into an agent container; uses the agent container's own `localhost`; or lacks a successful health check from the same Docker network through `http://task-env:<TASK_ENV_PORT>/`.
- `env.state_mode` is inaccurate, a mutable attempt reuses state from another attempt, a read-only environment changes under concurrent requests, or runtime names can collide across users/runs.
- `/api/judge` remains reachable when `TASK_ENV_ENABLE_JUDGE=0`, or a formal test shares an environment instance with a judge-enabled stage.
- Test tasks can score well without transfer from train tasks.
- The apparent 6-10 rubric rows use different wording but reward the same underlying criterion, answer fact, or root decision more than once, causing semantic double counting.
- `scratch/rubric_validation.md` is missing, does not check semantic duplication, or allows any rubric point to receive only part of its assigned score.
- Overall base score falls outside the approximate `0.40-0.60` target, overall fewshot `avg@3` reaches roughly `0.80` or higher, fewshot gain falls outside the approximate `0.10-0.30` target without a convincing explanation, or most tasks score `0.95` or higher or otherwise approach a perfect score.
- Difficulty evidence comes from orchestration subagents, hand-authored predictions, non-fixed prompts, or runs without isolated staged work and preserved Codex traces.
- Evaluation scores free text, evidence phrasing, format friction, or unrelated fields instead of key business outcomes.
- Notes omit transfer source, answer basis, or scoring standard, making the data hard to interpret.
- Multi-agent construction records are missing, or all env/task/answer/notes/eval assets were clearly generated by one monolithic script.
