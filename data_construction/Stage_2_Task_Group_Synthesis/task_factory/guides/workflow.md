# Main Agent And Subagent Workflow

## Roles

Stage 2 construction may use a main agent and multiple subagents.

This workspace requires subagents for environment and task construction. A user request to construct a task group in this workspace should be treated as permission to use those construction subagents. Difficulty calibration is different: do not use orchestration subagents for calibration. Launch each calibration run as an isolated Dockerized `codex exec` process using `calibration_runtime.md`.

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

Dockerized Codex processes own difficulty calibration. Every process must use
the Codex harness with `gpt-5.5` at `xhigh` reasoning effort; do not inherit the
main construction agent's model or client defaults:

- Three isolated fewshot skill-generation processes each read all 5 train inputs and matching standard answers, producing 3 independent skill packages.
- Base: run 3 isolated processes per test task, for 15 processes total.
- Fewshot: run 3 isolated processes per test task, pairing attempt 01/02/03 with the matching skill package, for another 15 processes total.
- Every process receives a fresh staged `/work`, a dedicated temporary `CODEX_HOME` seeded only with the active `auth.json` and verified by `codex login status`, a fixed prompt, and only the files allowed for that run.
- Copy only the matched primary `sessions/.../rollout-*.jsonl` into the run's `trace/` directory. Populate and verify all trace-derived token, cost, turn, tool-call and calibration-record fields from that copy before deleting the temporary `CODEX_HOME`. Do not archive the full Codex home or use stdout as the trace. Calibration agents must not access notes, evaluator files, environment source, construction drafts, or other runs.

The reviewer subagent owns independent review:

- Check structure, interpretability, data generation, environment complexity, prompt leakage, transfer design, evaluation validity, and whole-point scoring.

## Stage Overview

Construction should move through these stages. Do not skip directly from reading the seed scenario to generating the final task group.

| Stage | Owner | Main outputs | Gate before next stage |
| --- | --- | --- | --- |
| 1. Scenario understanding | Main agent | Source example difficulty audit and scenario interpretation | The main agent can explain the source examples' real workflow, data surfaces, and difficulty drivers |
| 2. Task-group design | Main agent | `scratch/task_group_design.md` only | The 5 train and 5 test tasks, transfer plan, diversity plan, scoring plan, and task-builder assignments are explicit; no task files, answers, evaluators, or environment implementation are created in this stage |
| 3. Environment blueprint | Main agent | `scratch/env_blueprint.md` | Shared business systems, public entry points, data contracts, generation seeds, Docker image/runtime behavior, declared state mode, network-only access, reset behavior, and manifest requirements are specified |
| 4. Environment implementation | Clean-context env-builder coding subagent | `env/` | The environment is shared across all tasks, domain-oriented, reachable from a separate agent container, and free of answer-like per-task endpoints |
| 5. Task construction | 10 task-builder subagents | `train_tasks/` and `test_tasks/` task folders | Each assigned task has solver input, bilingual notes, standard answer, evaluator, and answer template |
| 6. Integration and evaluator self-check | Main agent | Finalized `task_group.yaml`, path/schema fixes, `scratch/rubric_validation.md`, evaluator and judge-API self-check logs | Every evaluator scores its own answer fully; the rubric covers distinct business outcomes without duplicate scoring; each point earns all of its assigned score or zero; and `/api/judge` rejects test ids without hidden details |
| 7. Difficulty calibration | Dockerized Codex processes, scored by main agent | `scratch/difficulty_calibration.md`, primary session JSONL traces, 3 independent fewshot skill packages, base/fewshot results | Fixed-prompt runs are isolated; overall base score is about `0.40-0.60`; fewshot remains roughly below `0.80` with a gain of about `0.10-0.30` and no saturation |
| 8. Independent review and rework | Reviewer subagent and main agent | Review findings, rework records, rerun calibration where needed | Structure, environment, notes, evaluation, transfer, and difficulty requirements all pass |

## Construction Flow

1. The main agent writes `scratch/task_group_design.md`, covering the 10 task plan, task-builder assignments, task diversity, transferable SOPs, train/test roles, environment plan, data-generation plan, and evaluation plan. This is a design document only; it must not create task folders, prompts, notes, standard answers, evaluators, or environment implementation files.
2. The main agent writes `scratch/env_blueprint.md`, specifying shared business systems, public interfaces, data contracts, generation seeds, manifest requirements, `env/Dockerfile`, `env.state_mode`, `TASK_ENV_BIND`/`TASK_ENV_PORT`, the `task-env` network route, judge enable/disable behavior, reset behavior, and expected environment behavior.
3. A clean-context env-builder coding subagent implements `env/` from `scratch/env_blueprint.md`, including the environment Dockerfile, Web/API services, `env/endpoints.txt`, any required container-internal SQLite database and authenticated query service, data-generation scripts, generated data, setup scripts, manifests, health checks, and an operator reset/reseed path.
4. The main agent reviews and integrates the env-builder output, then records usable environment entry points for task builders.
5. The main agent launches 10 task-builder subagents, in parallel or batches: one for each `train_001` through `train_005` and `test_001` through `test_005`.
6. Task-builder subagents generate their own assigned task `input/`, `notes/`, `output/`, and `eval/`.
7. The main agent integrates all tasks and standardizes paths, schemas, notes, and environment usage.
8. The main agent runs every evaluator against the standard answer and creates `scratch/rubric_validation.md`. It verifies that each task covers at least 4 distinct business outcomes, does not score the same criterion or answer fact more than once, and gives every point either all of its assigned score or zero. The main agent connects `env/judge_api.py` to the service and verifies that `/api/judge` gives full credit to train standard answers, preserves the evaluator's weighted aggregate score, rejects test task ids, and returns no hidden evaluator or answer content.
9. Before difficulty calibration, the main agent builds the environment image, creates owner- and run-scoped Docker networks, and verifies `/health` from a disposable container at `http://task-env:<TASK_ENV_PORT>/`. Read-only environments may be shared within the judge-disabled calibration stage; mutable environments receive a fresh network and environment container per attempt.
10. Base calibration: launch 15 independent Dockerized `codex exec` runs with the fixed base prompt, 3 attempts for each test task. The main agent scores predictions outside the Codex processes and records base `avg@3`.
11. Launch 3 isolated Dockerized `codex exec` processes with the fixed fewshot skill-generation prompt. Each receives all 5 train inputs, the matching train answers, and the environment entrypoint, then writes one complete package under `scratch/train_skill/fewshot_attempt_<nn>/` with `SKILL.md` as its entry file.
12. Fewshot calibration: launch 15 independent Dockerized `codex exec` runs with the fixed fewshot prompt, 3 attempts for each test task. Pair test attempt 01/02/03 with `fewshot_attempt_01/02/03`. The main agent scores predictions outside the Codex processes and records fewshot `avg@3`.
13. A clean-context reviewer subagent performs an independent review after generation, validation, and calibration.
14. The main agent revises based on calibration and review, reruns affected subagents and calibration attempts, and repeats until structure, transfer design, data generation, evaluation, and difficulty targets all pass.

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
- `scratch/train_skill/fewshot_attempt_01/SKILL.md`
- `scratch/train_skill/fewshot_attempt_02/SKILL.md`
- `scratch/train_skill/fewshot_attempt_03/SKILL.md`

Allowed scripts must have a narrow owner and purpose:

- The env-builder may write scripts under `env/` for shared environment data generation, service startup, migrations, and manifests.
- A task-builder may write helper scripts for its assigned task only, such as a local evaluator implementation or task-local data transformation.
- The main agent may run validation scripts that check paths, schemas, evaluator reproducibility, and consistency after subagent outputs are integrated.

Design docs must be written before implementation, not backfilled by the same script that generated the final artifacts. Every `SKILL.md` must be produced by an isolated fewshot skill-generation process from staged train inputs and standard answers, not prewritten from the construction specification.

## Collaboration Constraints

- The main agent owns blueprint quality, task-group coherence, and final integration.
- The env-builder coding subagent owns `env/` implementation and programmatic data-generation code.
- Task-builder subagents own task-file generation. The main agent should not directly generate all task prompts, standard answers, notes, and evaluators in one monolithic builder script.
- A monolithic script that creates env, all task files, answers, notes, evaluators, scratch docs, and skills is not a valid substitute for subagent construction.
- Calibration runs must use Dockerized `codex exec`, dedicated staged work and temporary `CODEX_HOME` directories, the fixed prompts in `calibration_runtime.md`, and copied primary `rollout-*.jsonl` traces. Delete each temporary Codex home only after all trace-derived data has been populated and verified. Orchestration subagent runs do not count as difficulty evidence.
- Subagent write scopes should be clear to avoid overwriting each other.
- Subagents must not transform notes, standard answers, or eval files into solver-facing input.
- All temporary designs, solver runs, skills, and review records belong under `scratch/`.
