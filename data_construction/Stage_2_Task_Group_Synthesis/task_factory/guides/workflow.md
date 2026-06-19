# Main Agent And Subagent Workflow

## Roles

Stage 2 construction may use a main agent and multiple subagents.

This workspace requires subagents for construction and calibration. A user request to construct a task group in this workspace should be treated as permission to use subagents. If subagent concurrency is limited, run them in batches while preserving clean contexts.

The main agent owns overall consistency:

- Read the seed scenario and examples.
- Write `scratch/task_group_design.md`.
- Write the environment blueprint, including required business systems, public entry points, data contracts, random seeds, and generated-data expectations.
- Assign environment implementation to a clean-context coding subagent.
- Assign train/test task work to subagents.
- Integrate the environment implementation and other subagent outputs.
- Check paths, schemas, notes, answers, evaluation files, and calibration results.
- Maintain the final `task_group.yaml`.

The env-builder coding subagent owns environment implementation:

- Start from the environment blueprint rather than the full construction context.
- Implement the shared `env/` infrastructure for the whole task group, including setup scripts, Web/API/database services, generated business data, random seeds, and output manifests.
- Keep the environment reusable across train and test tasks, not tailored to one task.
- Report implemented endpoints, tables, generated files, seeds, and setup steps back to the main agent.
- Do not design task answers, notes, rubrics, or solver-facing prompts.

Task-builder subagents own local task production:

- There should be 10 task-builder subagents total: one for each of 5 train tasks and 5 test tasks.
- Work only on their assigned train or test task.
- Create `input/`, `notes/`, `output/`, and `eval/` based on the task group design, environment entry points, and data constraints provided by the main agent.
- Request additional environment capabilities or data through the main agent when needed, but do not independently implement separate environments.
- Do not modify tasks owned by other subagents.

The skill-builder subagent owns the train-derived skill:

- First read only solver-visible train inputs and attempt the 5 real train tasks without answers.
- Then compare those attempts with train answers and summarize transferable SOPs, facts, field conventions, and environment-use experience.
- Output the calibration skill under `scratch/`.

Solver subagents own difficulty testing:

- Direct test: run 2 clean-context attempts per test task, for 10 solver subagents total across 5 test tasks.
- Post-skill test: after skill distillation, run 2 clean-context attempts per test task with the train-derived skill, for another 10 solver subagents total.
- Each solver subagent handles exactly one target test task and one attempt.
- Do not access notes, standard answers, evaluation scripts, or construction drafts.

The reviewer subagent owns independent review:

- Check structure, interpretability, data generation, environment complexity, prompt leakage, transfer design, and evaluation validity.

## Stage Overview

Construction should move through these stages. Do not skip directly from reading the seed scenario to generating the final task group.

| Stage | Owner | Main outputs | Gate before next stage |
| --- | --- | --- | --- |
| 1. Scenario understanding | Main agent | Source example difficulty audit and scenario interpretation | The main agent can explain the source examples' real workflow, data surfaces, and difficulty drivers |
| 2. Task-group design | Main agent | `scratch/task_group_design.md` only | The 5 train and 5 test tasks, transfer plan, diversity plan, scoring plan, and task-builder assignments are explicit; no task files, answers, evaluators, or environment implementation are created in this stage |
| 3. Environment blueprint | Main agent | `scratch/env_blueprint.md` | Shared business systems, public entry points, data contracts, generation seeds, setup behavior, and manifest requirements are specified |
| 4. Environment implementation | Clean-context env-builder coding subagent | `env/` | The environment is shared across all tasks, domain-oriented, runnable, and free of answer-like per-task endpoints |
| 5. Task construction | 10 task-builder subagents | `train_tasks/` and `test_tasks/` task folders | Each assigned task has solver input, bilingual notes, standard answer, evaluator, and answer template |
| 6. Integration and evaluator self-check | Main agent | Finalized `task_group.yaml`, path/schema fixes, evaluator self-check logs | Every evaluator scores its own `output/answer.json` as full credit |
| 7. Difficulty calibration | Skill-builder and solver subagents, scored by main agent | `scratch/difficulty_calibration.md`, blind train attempts, reflection, `SKILL.md`, direct/post-skill results | Direct and post-skill attempts are clean-context and meet difficulty targets without saturation |
| 8. Independent review and rework | Reviewer subagent and main agent | Review findings, rework records, rerun calibration where needed | Structure, environment, notes, evaluation, transfer, and difficulty requirements all pass |

## Construction Flow

1. The main agent writes `scratch/task_group_design.md`, covering the 10 task plan, task-builder assignments, task diversity, transferable SOPs, train/test roles, environment plan, data-generation plan, and evaluation plan. This is a design document only; it must not create task folders, prompts, notes, standard answers, evaluators, or environment implementation files.
2. The main agent writes `scratch/env_blueprint.md`, specifying shared business systems, public interfaces, data contracts, generation seeds, manifest requirements, and expected environment behavior.
3. A clean-context env-builder coding subagent implements `env/` from `scratch/env_blueprint.md`, including Web, API, PostgreSQL, data-generation scripts, generated data, setup scripts, and manifests.
4. The main agent reviews and integrates the env-builder output, then records usable environment entry points for task builders.
5. The main agent launches 10 task-builder subagents, in parallel or batches: one for each `train_001` through `train_005` and `test_001` through `test_005`.
6. Task-builder subagents generate their own assigned task `input/`, `notes/`, `output/`, and `eval/`.
7. The main agent integrates all tasks and standardizes paths, schemas, notes, and environment usage.
8. The main agent runs every evaluator against the standard answer to check reproducibility.
9. Before difficulty calibration, the main agent starts the task-group environment as a local process on a randomly selected available port in the `8000-8100` range and records the startup command and port. Do not start by scanning upward from `8000`.
10. Direct calibration: 10 clean-context solver subagents run no-skill attempts, 2 attempts for each of the 5 test tasks. The main agent scores predictions outside solver contexts and records direct `avg@2`.
11. A clean-context skill-builder subagent first solves the 5 train inputs without seeing answers and stores blind attempts under `scratch/train_skill/blind_attempts/`.
12. The skill-builder then compares those blind attempts with the 5 train `output/answer.json` files, writes `scratch/train_skill/reflection.md`, and distills the corrected method into `scratch/train_skill/SKILL.md`.
13. Post-skill calibration: 10 clean-context solver subagents run post-skill attempts, 2 attempts for each of the 5 test tasks. The main agent scores predictions outside solver contexts and records post-skill `avg@2`.
14. A clean-context reviewer subagent performs an independent review after generation, validation, and calibration.
15. The main agent revises based on calibration and review, reruns affected subagents and calibration attempts, and repeats until structure, transfer design, data generation, evaluation, and difficulty targets all pass.

## Monolithic Builder Ban

Do not replace the workflow above with one builder script that writes the whole task group.

A script such as `scratch/build_task_group_001.py` is not acceptable if it directly creates most or all of these artifacts from one fixed specification:

- `env/`
- all 5 train task folders and all 5 test task folders
- solver-visible prompts and payloads
- hidden `notes/notes.md`
- `output/answer.json`
- `eval/`
- `task_group.yaml`
- `scratch/task_group_design.md`
- `scratch/env_blueprint.md`
- `scratch/difficulty_calibration.md`
- `scratch/train_skill/SKILL.md`

Allowed scripts must have a narrow owner and purpose:

- The env-builder may write scripts under `env/` for shared environment data generation, service startup, migrations, and manifests.
- A task-builder may write helper scripts for its assigned task only, such as a local evaluator implementation or task-local data transformation.
- The main agent may run validation scripts that check paths, schemas, evaluator reproducibility, and consistency after subagent outputs are integrated.

Design docs must be written before implementation, not backfilled by the same script that generated the final artifacts. `SKILL.md` must be produced by the clean-context blind-solve, answer-comparison, and reflection workflow, not prewritten from the construction specification.

## Collaboration Constraints

- The main agent owns blueprint quality, task-group coherence, and final integration.
- The env-builder coding subagent owns `env/` implementation and programmatic data-generation code.
- Task-builder subagents own task-file generation. The main agent should not directly generate all task prompts, standard answers, notes, and evaluators in one monolithic builder script.
- A monolithic script that creates env, all task files, answers, notes, evaluators, scratch docs, and skills is not a valid substitute for subagent construction.
- Solver subagents used for difficulty calibration must be clean-context and counted only when they produce a prediction from the allowed inputs.
- Subagent write scopes should be clear to avoid overwriting each other.
- Subagents must not transform notes, standard answers, or eval files into solver-facing input.
- All temporary designs, solver runs, skills, and review records belong under `scratch/`.
