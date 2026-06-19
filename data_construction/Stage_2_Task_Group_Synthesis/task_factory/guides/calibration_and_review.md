# Calibration And Review

## Calibration Targets

Each test task should have direct `avg@2` roughly below `0.60` when attempted without learning from the train set.

After using a skill derived directly from the train set, each test task's post-skill `avg@2` should improve by about `0.15` or more over direct `avg@2`.

The train-derived skill should not make every test task score extremely high. If most or all test tasks become near-perfect after using the skill, such as around `0.90` or higher, the SOP is probably too simple, too mechanical, or too directly inferable from the train tasks.

The goal is not to make all test tasks easy. The goal is to verify that real train tasks provide enough evidence for the agent to infer transferable SOPs, facts, data conventions, environment-use patterns, or business-judgment experience through blind attempts, answer comparison, and reflection.

## Direct Test Attempts

Direct test attempts estimate performance without train-set learning.

Before running difficulty test attempts, start the task group's environment as a local process on a randomly selected available port in the `8000-8100` range. Randomly sample a port first, check whether it is available, and if it is not, randomly sample another remaining port rather than scanning upward from `8000`. Record the startup command, port, and any relevant logs in `scratch/difficulty_calibration.md`. Reuse the same process for direct and post-skill attempts when the environment has not changed; restart it after any environment rework.

Run exactly 2 clean-context direct attempts for each of the 5 test tasks, for 10 solver subagents total. Each solver subagent handles one target test task and one attempt. Compute direct `avg@2` for each test task from its two scored attempts.

The solver subagent may see only:

- The target test task's `input/`
- Necessary environment entry points, such as URLs, API endpoints, or database connection strings

It must not see:

- train tasks
- notes
- standard answers
- eval
- task group design
- review records
- the `env/` directory, source files, generated data files, database dumps, seeds, manifests, or setup scripts

## Train-Derived Skill

The skill-builder subagent derives a skill from the train tasks through a blind-solve, compare, reflect, and distill loop.

First, the skill-builder may see only:

- Solver-visible inputs for train tasks
- Necessary environment entry points, such as URLs, API endpoints, or database connection strings

It must solve all 5 train tasks without seeing train answers. Store those blind attempts under:

```text
scratch/train_skill/blind_attempts/
```

Then the skill-builder may see `output/answer.json` for the 5 train tasks. It compares its blind attempts against the standard answers and writes a mistake analysis at:

```text
scratch/train_skill/reflection.md
```

The reflection should identify missed source-precedence rules, missing SOP steps, wrong field conventions, wrong calculations, weak environment-use habits, and output-format mistakes. Only after this comparison should the skill-builder write the final skill.

It must not see:

- test tasks
- notes
- eval
- task group design
- review records
- the `env/` directory, source files, generated data files, database dumps, seeds, manifests, or setup scripts

The skill is used only for calibration, stored under `scratch/`, and excluded from the final `task_group/`.

The skill package should be stored as:

```text
scratch/train_skill/SKILL.md
```

`SKILL.md` should contain the corrected operating method learned from train: source precedence, reusable business rules, environment-use strategy, field and output conventions, calculation rules, common pitfalls, and final validation checks. It should not contain test-specific facts or final answers.

## Skill Test Attempts

Train-skill test attempts validate transfer gain.

Run exactly 2 clean-context post-skill attempts for each of the 5 test tasks, for 10 solver subagents total. Each solver subagent receives the train-derived skill and exactly one target test task. Compute post-skill `avg@2` for each test task from its two scored attempts.

The solver subagent may see:

- train-derived skill
- The target test task's `input/`
- Necessary environment entry points, such as URLs, API endpoints, or database connection strings

It must not see notes, standard answers, eval files, construction drafts, or the `env/` implementation files.

## Calibration Record

Store the calibration record at:

```text
scratch/difficulty_calibration.md
```

Record at least:

- Solver, input, prediction file, evaluation command, and score for each of the 10 direct test attempts.
- Paths to the train blind attempts, train answer comparison reflection, train-derived skill, and the train inputs used to create it.
- Solver, input, prediction file, evaluation command, and score for each of the 10 post-skill test attempts.
- Direct `avg@2`, post-skill `avg@2`, and gain for each test task.
- Overall direct `avg@2` and overall post-skill `avg@2` across the 5 test tasks.
- Whether each test task's post-skill `avg@2` improves by about `0.15` or more.
- Whether skill test scores saturate across most or all test tasks, and if so which scoring points became too easy.
- Whether low scores come from transfer failure or task complexity, not prompt ambiguity, schema friction, or fragile evaluation.

Builder-authored, hand-mutated, synthetic, or counterfactual prediction files do not count as difficulty calibration. They may be used only as evaluator sensitivity checks and must be recorded separately.

## Rework Loop

If calibration or review fails, the task group must be reworked and checked again before it can move to `data_construction/task_groups/<task_group_id>/`.

When direct `avg@2` is too high, the main agent may rework any combination of:

- scoring points, if too much score comes from low-difficulty checks;
- task design, if the test task is solvable without train transfer;
- solver-facing prompt or payloads, if they leak too much procedure, source selection, or key facts;
- `scratch/env_blueprint.md`, if the environment is too narrow, too direct, too clean, too small, or exposes answer-like interfaces.

If the environment needs rework, the main agent should revise `scratch/env_blueprint.md` and send it back to the clean-context env-builder coding subagent. Environment-side rework may include increasing data volume, adding realistic noise, widening API/Web/database surfaces, removing direct-answer endpoints, adding stale or overlapping sources, changing what is exposed in payloads versus `env/`, or making source selection more realistic.

When train-derived skill improvement is too small by post-skill `avg@2`, rework should focus on train/test transfer distance and diversity width. Inspect whether the intended transfer-dependent high-weight points actually rely on methods that can be inferred from real train tasks. Also check whether the group covers too many one-off workflow families, causing each test task to have only a single narrow train anchor. If transfer is too wide, narrow the group to 2-3 recurring operation families, make reusable conventions recur across multiple train tasks, or redesign test scoring points so the transfer core comes from repeated train evidence. If the test requires missing SOPs, source-precedence rules, calculations, or business judgments, add real train-task coverage or redesign those points. If the test has no meaningful high-weight points that require train transfer, add such points. Do not require every high-weight point to have a train anchor, and do not fix transfer failure by making train tasks instructional, making test prompts procedural, or leaking SOP steps into solver-visible inputs.

When train-derived skill scores are too high across most or all test tasks by post-skill `avg@2`, rework should make the SOP less mechanical and the test tasks less directly solved by train examples. The main agent may increase train/test diversity within the same real-task distribution, require more task-specific evidence discovery, add larger or messier data, broaden environment surfaces, move some easy payload information into `env/`, or redesign scoring points so that the skill helps but does not answer the whole task. Do not reduce scores by adding ambiguity, hidden information, brittle schemas, or unfair evaluator behavior.

When review finds structural, leakage, evaluation, or data-generation problems, the main agent assigns rework to the responsible subagent, reintegrates the result, reruns evaluators, reruns calibration when needed, and requests review again. Final acceptance requires two valid direct attempts and two valid post-skill attempts for every test task after the last relevant rework.

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
- Whether database-backed tasks expose database access through a running service and connection details, rather than by giving solver agents direct access to `env/` files or generated data dumps.
- Whether large-scale data is generated by programs and randomness, with seeds and scripts retained.
- Whether every task has `notes/notes.md`, including transfer design and transfer-source explanation for test tasks.
- Whether every `notes/notes.md` file is bilingual in English and Chinese for human review.
- Whether Chinese text is limited to `notes/notes.md`; solver-visible inputs, answer templates, standard answers, evaluators, task metadata, and environment files should remain English-only.
- Whether every train and test task has `input/payloads/answer_template.json`, and whether `output/answer.json` conforms to that template.
- Whether evaluation is rule-based, reproducible, and covers key business judgments.
- Whether every task has 6-10 scoring points, raw weights only use `1`, `2`, or `3`, and final score is normalized by `weight / sum(weight)`.
- Whether scoring points exact-match key business results instead of wording, evidence strings, formatting friction, or irrelevant details.
- Whether scoring points prefer numeric, enum, boolean, ranking, set, or normalized structured outputs; if string matching is needed, whether it has been converted into controlled-choice fields to avoid schema friction.
- Whether most scoring points genuinely depend on train transfer, substantial data exploration, or long-horizon work, instead of being obtainable without train learning or deep data exploration.
- Whether `scratch/difficulty_calibration.md` contains 10 valid direct clean-context solver attempts and 10 valid post-skill clean-context solver attempts.
- Whether the train-derived skill was produced by blind-solving all 5 train inputs first, comparing against `output/answer.json`, writing `scratch/train_skill/reflection.md`, and only then writing `scratch/train_skill/SKILL.md`.
- Whether direct `avg@2` is roughly below `0.60` for each test task; if not, whether scoring points, task design, solver-visible inputs, or the environment should be reworked.
- Whether post-skill `avg@2` shows the target gain over direct `avg@2`.
- Whether post-skill `avg@2` avoids saturation across most or all test tasks; if skill scores are near-perfect everywhere, whether the SOP, task diversity, data exploration, environment, or scoring points should be reworked.
