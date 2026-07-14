# Calibration And Review

## Calibration Targets

Across the 5 test tasks, overall base `avg@3` should be roughly `0.40-0.60`
when attempted without learning from the train set. Individual tasks should
normally remain near that band; justified outliers are allowed, but a group
should not pass because very easy and impossible tasks merely average together.

After using a skill derived directly from the train set, overall fewshot
`avg@3` should improve by roughly `0.10-0.20` over base `avg@3`. Inspect each
task as well: the intended transfer points should improve without making most
tasks nearly perfect.

The train-derived skill should not make every test task score extremely high. If most or all test tasks become near-perfect after using the skill, such as around `0.90` or higher, the SOP is probably too simple, too mechanical, or too directly inferable from the train tasks.

The goal is not to make all test tasks easy. The goal is to verify that the five solved train examples provide enough evidence for an isolated fewshot generator to infer transferable SOPs, facts, data conventions, environment-use patterns, or business-judgment experience.

## Base Test Attempts

Base attempts estimate performance without train-set learning.

Before running difficulty attempts, start the task-group environment on the
orchestration host with `TASK_ENV_BIND=0.0.0.0` and an available
`TASK_ENV_PORT`. Every calibration container must use
`--add-host=host.docker.internal:host-gateway`, and
`environment_access.md` must contain
`http://host.docker.internal:<TASK_ENV_PORT>`. Verify the health endpoint from a
disposable container through that exact route and record the startup command,
port, URL, and logs in `scratch/difficulty_calibration.md`. Never stage or mount
`env/` into a calibration agent. Reuse the same service for base and
fewshot attempts when state remains valid; reset or restart it after writes
or environment rework.

Run exactly 3 base attempts for each of the 5 test tasks, for 15 independent
Dockerized `codex exec` processes total. Do not use orchestration subagents for
these attempts. Each process receives one freshly staged target test task and
uses the fixed base prompt from `calibration_runtime.md`. Compute base
`avg@3` for each test task from its three scored attempts.

The Codex process may see only:

- The target test task's `input/`
- Necessary environment entry points, such as URLs, API endpoints, or an authenticated SQLite query-service URL and credentials

The Codex process must not see:

- train tasks
- notes
- standard answers
- eval
- task group design
- review records
- the `env/` directory, source files, generated data files, database dumps, seeds, manifests, or setup scripts

## Train-Derived Skill

Generate 3 independent calibration skills with 3 isolated Dockerized
`codex exec` processes, matching the formal evaluation's `fewshot` condition.
Each generator may see only:

- Solver-visible inputs for all 5 train tasks
- Standard `output/answer.json` for all 5 train tasks
- Necessary environment entry points, such as URLs, API endpoints, or an authenticated SQLite query-service URL and credentials

Each process uses the fixed fewshot skill-generation prompt from
`calibration_runtime.md` and independently distills transferable operating
experience from the solved train examples. The 3 processes must not share a
working directory, Codex home, prior skill, or trace.

Each generator must not see:

- test tasks
- notes
- eval
- task group design
- review records
- the `env/` directory, source files, generated data files, database dumps, seeds, manifests, or setup scripts

The skills are used only for calibration, stored under `scratch/`, and excluded
from the final `task_group/`. Each attempt directory is the complete skill
package root, with `SKILL.md` as its entry file:

```text
scratch/train_skill/fewshot_attempt_01/SKILL.md
scratch/train_skill/fewshot_attempt_02/SKILL.md
scratch/train_skill/fewshot_attempt_03/SKILL.md
```

Each package should contain the operating method inferred from train: source
precedence, reusable business rules, environment-use strategy, field and output
conventions, calculation rules, common pitfalls, and final validation checks.
Supporting files may live in the same attempt directory. The package must not
copy train answers or contain test-specific facts or final answers.

## Fewshot Test Attempts

Fewshot attempts validate transfer gain from the train-derived skill.

Run exactly 3 fewshot attempts for each of the 5 test tasks, for 15 independent
Dockerized `codex exec` processes total. Do not use orchestration subagents for
these attempts. Attempt 01 receives `fewshot_attempt_01`, attempt 02 receives
`fewshot_attempt_02`, and attempt 03 receives `fewshot_attempt_03`, together
with exactly one freshly staged target test task. Each process uses the fixed
fewshot prompt from `calibration_runtime.md`. Compute fewshot `avg@3` for each
test task from its three scored attempts.

The Codex process may see:

- train-derived skill
- The target test task's `input/`
- Necessary environment entry points, such as URLs, API endpoints, or an authenticated SQLite query-service URL and credentials

It must not see notes, standard answers, eval files, construction drafts, or the `env/` implementation files.

## Calibration Record

Store the calibration record at:

```text
scratch/difficulty_calibration.md
```

Record at least:

- Solver, input, prediction file, evaluation command, and score for each of the 15 base attempts.
- Calibration model, reasoning effort, container image, fixed host-gateway settings, fixed prompt type, run id, staged files, and primary Codex trace path for every process.
- Generator metadata, staged train inputs and answers, skill-package path, and primary trace path for each of the 3 independent fewshot skill-generation attempts.
- Solver, input, prediction file, evaluation command, and score for each of the 15 fewshot attempts.
- Base `avg@3`, fewshot `avg@3`, and gain for each test task.
- Overall base `avg@3` and overall fewshot `avg@3` across the 5 test tasks.
- Whether overall base `avg@3` is about `0.40-0.60` and whether individual task outliers are justified.
- Whether overall fewshot gain is about `0.10-0.20`, with a per-task explanation of which transfer-dependent rubric points changed.
- Whether fewshot scores saturate across most or all test tasks, and if so which scoring points became too easy.
- Whether low scores come from transfer failure or task complexity, not prompt ambiguity, schema friction, or fragile evaluation.

Builder-authored, hand-mutated, synthetic, or counterfactual prediction files do not count as difficulty calibration. They may be used only as evaluator sensitivity checks and must be recorded separately.

## Rework Loop

If calibration or review fails, the task group must be reworked and checked again before it can move to `data_construction/task_groups/<task_group_id>/`.

When overall base `avg@3` is outside roughly `0.40-0.60`, or individual tasks
are implausibly easy or impossible, the main agent may rework any combination
of:

- scoring points, if too much score comes from low-difficulty checks;
- task design, if the test task is solvable without train transfer;
- solver-facing prompt or payloads, if they leak too much procedure, source selection, or key facts;
- `scratch/env_blueprint.md`, if the environment is too narrow, too direct, too clean, too small, or exposes answer-like interfaces.

If the environment needs rework, the main agent should revise `scratch/env_blueprint.md` and send it back to the clean-context env-builder coding subagent. Environment-side rework may include increasing data volume, adding realistic noise, widening API/Web/database surfaces, removing direct-answer endpoints, adding stale or overlapping sources, changing what is exposed in payloads versus `env/`, or making source selection more realistic.

When overall train-derived skill improvement is below roughly `0.10`, rework
should focus on train/test transfer distance and diversity width. Inspect whether
the intended transfer-dependent high-weight points actually rely on methods that
can be inferred from real train tasks. Also check whether the group covers too
many one-off workflow families, causing each test task to have only a single
narrow train anchor. If transfer is too wide, narrow the group to 2-3 recurring
operation families, make reusable conventions recur across multiple train
tasks, or redesign test scoring points so the transfer core comes from repeated
train evidence. If the test requires missing SOPs, source-precedence rules,
calculations, or business judgments, add real train-task coverage or redesign
those points. If the test has no meaningful high-weight points that require
train transfer, add such points. Do not require every high-weight point to have
a train anchor, and do not fix transfer failure by making train tasks
instructional, making test prompts procedural, or leaking SOP steps into
solver-visible inputs.

When overall gain is substantially above roughly `0.20`, inspect whether the
skill reveals too much of the test solution, the train/test variants are too
mechanically similar, or correlated rubric points all reward the same learned
decision. Rework the transfer design rather than accepting an inflated gain.

When train-derived skill scores are too high across most or all test tasks by fewshot `avg@3`, rework should make the SOP less mechanical and the test tasks less directly solved by train examples. The main agent may increase train/test diversity within the same real-task distribution, require more task-specific evidence discovery, add larger or messier data, broaden environment surfaces, move some easy payload information into `env/`, or redesign scoring points so that the skill helps but does not answer the whole task. Do not reduce scores by adding ambiguity, hidden information, brittle schemas, or unfair evaluator behavior.

When review finds structural, leakage, evaluation, or data-generation problems, the main agent assigns rework to the responsible subagent, reintegrates the result, reruns evaluators, reruns calibration when needed, and requests review again. Final acceptance requires three valid base attempts and three valid fewshot attempts for every test task after the last relevant rework.

## Review

The reviewer subagent should check:

- Whether the task group is abstracted from examples under the same scenario.
- Whether train and test tasks are both formal tasks from the same real-task distribution, rather than train tasks being tutorials, worked examples, or easier teaching problems.
- Whether train and test difficulty is aligned with the source examples' difficulty drivers, rather than being much easier, narrower, or arbitrarily harder.
- Whether train and test tasks have both diversity and transferability.
- Whether diversity stays inside a transfer band, with recurring operation families and reusable conventions, rather than many unrelated one-off SOP families.
- Whether every test task has a meaningful subset of high-weight scoring points that require train transfer, and whether those transfer-dependent points have clear train anchors.
- Whether the task group was produced through the required multi-agent process: one env-builder coding subagent and 10 task-builder subagents, one per task.
- Whether construction avoided a monolithic `build_task_group_*.py` style script that directly generated `env/`, all tasks, hidden answers, notes, evaluators, design docs, and calibration skill from one fixed specification.
- Whether every task preserves long-horizon task complexity.
- Whether prompts and payloads leak SOPs, key facts, or step lists.
- Whether `env/` is a shared public-data and office-work environment for the whole task group, rather than a temporary tool for one task.
- Whether solver-facing environment access is organized by shared business domains and interfaces, not by per-task data packages or endpoints such as `/api/tasks/<task_id>/data`.
- Whether `env/` was implemented by a clean-context env-builder coding subagent from `scratch/env_blueprint.md`, rather than directly hand-built by the main agent.
- Whether database-backed tasks use host-side SQLite and expose only the required read/write capability through an authenticated running query service, rather than using PostgreSQL or giving solver agents direct access to `.db`, `env/`, schema, or generated data files.
- Whether large-scale data is generated by programs and randomness, with seeds and scripts retained.
- Whether every task has `notes/notes.md`, including transfer design and transfer-source explanation for test tasks.
- Whether every `notes/notes.md` file is bilingual in English and Chinese for human review.
- Whether Chinese text is limited to `notes/notes.md`; solver-visible inputs, answer templates, standard answers, evaluators, task metadata, and environment files should remain English-only.
- Whether every train and test task has `input/payloads/answer_template.json`, and whether `output/answer.json` conforms to that template.
- Whether evaluation is rule-based, reproducible, and covers key business judgments.
- Whether every task has 6-10 scoring points, raw weights only use `1`, `2`, or `3`, and final score is normalized by `weight / sum(weight)`.
- Whether the rubric spans at least 3 independently fail-able business questions or aspects, rather than splitting one root decision into duplicated points that all rise or fall together.
- Whether `scratch/rubric_validation.md` maps rubric dependencies and contains selective perturbation probes showing that independent mistakes lose only the intended credit.
- Whether indivisible points use deterministic exact match and naturally decomposable points can award documented partial credit with an earned fraction in `[0, 1]`.
- Whether scoring points prefer numeric, enum, boolean, ranking, set, or normalized structured outputs; if string matching is needed, whether it has been converted into controlled-choice fields to avoid schema friction.
- Whether most scoring points genuinely depend on train transfer, substantial data exploration, or long-horizon work, instead of being obtainable without train learning or deep data exploration.
- Whether `scratch/difficulty_calibration.md` contains 15 valid base and 15 valid fewshot Dockerized `codex exec` attempts, all launched with the fixed prompts and dedicated staged work/Codex-home directories.
- Whether 3 independent fewshot skills were generated from the 5 train inputs and matching standard answers, with isolated Dockerized processes and package roots under `scratch/train_skill/fewshot_attempt_<nn>/`.
- Whether overall base `avg@3` is about `0.40-0.60`, with implausible per-task outliers reworked or justified.
- Whether overall fewshot gain is about `0.10-0.20` and comes from intended transfer-dependent aspects rather than duplicated rubric points.
- Whether fewshot `avg@3` avoids saturation across most or all test tasks; if skill scores are near-perfect everywhere, whether the SOP, task diversity, data exploration, environment, or scoring points should be reworked.
