# Evaluation Workflow

This guide describes one complete model-profile run for one task group. Codex
is both the isolated skill-generation harness and the isolated test-solver
harness. The main Codex orchestrator stages materials, starts environments,
launches isolated processes, scores outputs, preserves traces, and aggregates
reports; it must not solve test tasks itself.

The scored branches are:

```text
base
fewshot/codex
fewshot/cc
fewshot/deepagents
fewshot/opencode
```

Read `CODEX_ORCHESTRATOR.md` before launching any agent process.

## 1. Select And Resolve One Model Profile

Accept exactly one runtime parameter, `model_profile`, and verify it is listed in
`configs/experiment.yaml`. Reject raw model/provider values and every task-group,
creator, mode, harness, attempt, limit, schedule, or multi-model override.
Discover exactly one staged task-group directory; its ID is not a launch
parameter.

Select exactly one profile from `configs/models/`. Write the closed resolved
profile artifact and the sanitized run manifest required by
`CODEX_ORCHESTRATOR.md` under:

```text
scratch/run_manifest/<model_profile>.resolved_profile.yaml
scratch/run_manifest/<model_profile>.yaml
```

Verify:

- Generator and solver both use Codex.
- The resolved manifest records `model_profile` as the only accepted runtime
  parameter and records no override fields.
- Generator and solver use the same resolved model and reasoning settings.
- Provider, endpoint, authentication, and pricing are complete.
- The profile status is not blocked.
- The installed Codex version accepts the resolved configuration.
- A smoke prompt can stream, call a harmless tool, and leave one matchable
  primary session trace.
- Every execution-policy value is resolved and enforceable by the runner.
- Common-input hashes, the schedule seed, and the expanded randomized order are
  frozen in the run manifest.

Do not run the two model profiles in one mixed pool. Complete and audit one
profile before starting the other. Cross-model output is a later side-by-side
aggregation of independently finalized reports.

## 2. Verify Creator Inputs

All creators listed in `configs/experiment.yaml` are mandatory. Reject a formal
run if the caller requests a subset or if any configured creator is absent. For
each configured creator, verify:

```text
creators/<creator>/manifest.yaml
creators/<creator>/upstream/SKILL.md
```

The manifest status must be pinned/ready, revision fields must be immutable, and
recorded hashes must match the whole bundle. Check that every local file linked
from the upstream `SKILL.md` exists. Reject symbolic links and calculate bundle
digests exactly as specified in `creators/README.md`.

Copy no creator into another creator directory. Formal generation staging uses
one creator bundle at a time.

## 3. Prepare The Task Group

The task group must be located at:

```text
task_group/<task_group_id>/
```

Confirm exactly one task group is present and that it contains:

- 5 train tasks.
- 5 test tasks.
- Official `input/` for every task.
- Standard train and test answers retained outside agent staging.
- `eval/eval.sh` for each task.
- `env/Dockerfile`, `env.state_mode`, and environment endpoint declarations.

Do not modify task-group files.

## 4. Start And Verify The Task Environment

Load `.env` for owner naming and the container-visible environment URL. Build
the task environment and create owner/task/model/stage-scoped Docker networks
and containers as specified in `CODEX_ORCHESTRATOR.md`.

All formal generation and solving stages use `TASK_ENV_ENABLE_JUDGE=0`. This
workspace has no reflect mode. Do not stage `GDPEVO_JUDGE_PATH` or a judge
endpoint to any execution agent.

Read allowed business endpoints from `task_group/env/endpoints.txt`. Each
staged `environment_access.md` contains:

- The container-visible base URL.
- Required runtime credentials when the task defines them.
- Allowed endpoints as `METHOD /path` lines without descriptive hints.

Do not expose `/health`, reset/reseed endpoints, or judge endpoints to execution
agents. Verify health from a disposable orchestration container on the same
network, then record the sanitized result under:

```text
scratch/environment/<model_profile>/
```

Before formal execution, generate the seeded orders required by
`configs/experiment.yaml`. Interleave all 12 creator-generation logical attempts,
and separately interleave the 15 shared-base plus 60 creator-specific solver
logical attempts. Record both complete orders before observing any output or
score. Run generation first, then follow the fixed 75-entry solver order;
creator entries lacking a valid package are marked not runnable. Infrastructure
replacements stay adjacent to their failed logical attempt and are explicitly
marked.

## 5. Generate Three Skills Per Creator

Follow the frozen 12-entry generation schedule. For each creator and attempt,
create an immutable physical run under the logical attempt:

```text
scratch/skill_generation/<model_profile>/<creator>/attempt_<nn>/physical_runs/<agent_run_id>/
```

Stage only the paths listed in `CODEX_ORCHESTRATOR.md`. Normalize train-answer
staging as:

```text
train_answers/train_001/answer.json
...
train_answers/train_005/answer.json
```

Use the exact Fewshot Skill Generation prompt. Every generation process uses a
new opaque `agent_run_id` and a clean container-local `CODEX_HOME`.

After the process exits, keep all artifacts in the physical-run directory until
selection:

1. Extract and uniquely match the primary Codex trace into `audit/`.
2. Run read-only package validation; reject symbolic links and save
   `validation.yaml`.
3. Calculate the package digest and record size, file count, duration,
   portability warnings, common-contract friction, token/cost/turn/tool-call
   fields, and validation/contamination status in generation metadata.
4. Clean up the stopped container and write the cleanup record after the audit
   artifacts are complete.
5. Only if the package, trace, metadata, contamination, and cleanup checks are
   valid, copy the complete package through a temporary sibling and atomic rename
   to:

   ```text
   skills/<model_profile>/fewshot/<creator>/fewshot_attempt_<nn>/
   ```

6. Copy the selected trace to its canonical `original_traces/` path and then
   write `selected_run.yaml` at the logical `attempt_<nn>/` root.

Do not repair invalid packages. A verified infrastructure failure may be rerun
in a new physical directory while retaining evidence. A logical creator failure
or invalid package leaves the logical attempt unselected and makes that creator
branch incomplete; never substitute a hand-authored skill.

## 6. Run The Frozen Solver Schedule

Follow the precomputed 75-entry order. Across it, shared base has 5 test tasks x
3 attempts and each creator has 5 test tasks x 3 attempts. Do not create a base
copy per creator.

Base physical run:

```text
runs/<model_profile>/base/<test_id>/attempt_<nn>/physical_runs/<agent_run_id>/
```

Stage only the current test `input/` and `environment_access.md`; no creator or
skill is staged. Use the exact Base Test Solver prompt.

Few-shot physical run:

```text
runs/<model_profile>/fewshot/<creator>/<test_id>/attempt_<nn>/physical_runs/<agent_run_id>/
```

Stage only the current test `input/`, `environment_access.md`, and the complete
matching generated package as `skill/`. The creator key in orchestrator metadata,
logical run path, skill path, and attempt mapping must agree. It is deliberately
absent from the agent prompt and prompt-visible run ID. Mark a schedule entry not
runnable when its matching logical generation attempt has no selected package.

Every solver must not see train inputs/answers, an upstream creator bundle or
contract, another skill/attempt, test answers, notes, evaluators, environment
source, reports, traces, or judge instructions.

After the solver exits:

1. Keep its output and extracted trace in the immutable physical-run directory.
2. Check contamination, then call the evaluator from orchestrator context.
3. Write `score.yaml` and `run_metadata.yaml`; for few-shot, recompute and verify
   the selected package digest.
4. Uniquely match and verify the primary trace and trace-derived metadata.
5. Remove the stopped container and write the cleanup record after artifacts are
   complete.
6. Only when output, score, trace, metadata, contamination, and cleanup status
   are valid, copy the selected trace to canonical `original_traces/` and
   atomically write `selected_run.yaml` at the logical `attempt_<nn>/` root.

A logical failure in base makes the model-profile report incomplete. A logical
failure in a creator entry makes that creator branch incomplete. Only verified
infrastructure failures receive replacement physical runs.

## 7. Logical Attempt IDs And Physical Run IDs

Logical IDs are descriptive orchestration metadata and are never shown to the
execution agent.

Generation logical ID:

```text
<task_group_id>__<model_profile>__skill_generation__fewshot__<creator>__attempt_<nn>__<timestamp>
```

Base solver logical ID:

```text
<task_group_id>__<model_profile>__base__<test_id>__attempt_<nn>__<timestamp>
```

Few-shot solver logical ID:

```text
<task_group_id>__<model_profile>__fewshot__<creator>__<test_id>__attempt_<nn>__<timestamp>
```

Every physical run receives a fresh opaque UUID `agent_run_id`. Only that opaque
UUID appears in the fixed prompt and is used to match the primary trace. Both the
logical ID and opaque UUID appear in run metadata. Failed physical runs remain
under `physical_runs/<agent_run_id>/`; never overwrite them. The logical
`attempt_<nn>/selected_run.yaml` points to the sole physical run included in
aggregation. A skill/solver mapping uses the logical attempt number, never the
number of infrastructure replacements.

Minimum `selected_run.yaml` shape:

```yaml
logical_attempt_id: <descriptive logical id>
status: selected
selected_agent_run_id: <opaque UUID>
physical_run: physical_runs/<opaque UUID>
selected_at: <RFC3339 timestamp>
output_sha256: <answer.json SHA-256 or generated-package digest>
trace_sha256: <selected rollout JSONL SHA-256>
cleanup_record_sha256: <sha256>
```

Write this file atomically only after all selection checks pass. An incomplete
logical attempt has no `selected_run.yaml`; preserve its failure state and reason
in the physical-run metadata and formal report.

## 8. Contamination Handling

If an execution agent accesses, lists, or reports seeing forbidden material:

1. Stop using the result.
2. Preserve the attempt and trace for audit.
3. Write the reason in `contamination_report.txt` or attempt metadata.
4. Do not score or aggregate it.
5. Determine whether the orchestrator accidentally exposed the material or the
   agent crossed a correctly enforced boundary.
6. For a verified staging/isolation leak, fix only that infrastructure defect and
   rerun in a new `physical_runs/<agent_run_id>/` directory with a new opaque
   UUID. Write `selected_run.yaml` only after the replacement is complete.
7. For agent-originated access with correct staging, do not rerun; record a
   logical failure and mark the affected branch incomplete.

Do not change the creator bundle, common contract, model profile, or task prompt
as part of a contamination retry.

## 9. Aggregate One Model Profile

Before aggregation, classify completeness:

- Base is complete only with 15 selected valid scores; otherwise record base as
  incomplete and keep base accuracy, dispersion, and all lifts null.
- A creator is complete only with 3 selected valid generation records and 15
  selected valid few-shot scores; otherwise report that creator as incomplete.
- Every included physical run has matching trace and metadata records.
- Each creator keeps one immutable revision/hash across the full profile.

Write:

```text
report/<model_profile>/<task_group_id>.yaml
```

Always write the report, including explicit incomplete branches. Compute base and
each complete creator branch independently, then compute:

- Each complete creator's lift when the shared base is also complete.
- Pairwise differences only when both creator branches are complete.
- Generation and solver efficiency per creator.
- Validation and portability observations.

## 10. Cross-Model Side-By-Side Report

This is post-hoc aggregation, not a multi-model formal invocation. Only after two
separate model-profile invocations are finalized, with incomplete branches
explicitly represented when necessary, write:

```text
report/comparison/<task_group_id>.yaml
```

Copy resolved model/provider identities and show creator results side by side.
Do not pool scores across models or present a causal model ranking when provider
and reasoning semantics differ.
