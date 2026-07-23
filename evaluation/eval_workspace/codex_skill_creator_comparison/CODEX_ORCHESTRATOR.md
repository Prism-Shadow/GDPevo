# Codex Orchestrator Guide

Codex is the main evaluation orchestrator and the tested harness for both skill
generation and test solving. The orchestrator may inspect the full task group to
stage allowed files, build and check the task environment, call evaluators,
preserve traces, and aggregate reports. It must not solve test tasks directly.

Every skill-generation run and every solver attempt must execute as a separate
Codex process inside Docker with a clean container-local `CODEX_HOME`.

## Resolve The Experiment Before Running

Accept exactly one caller-supplied value: `model_profile`. Reject the invocation
if it supplies a raw model/provider/reasoning value, task-group selector, creator
or mode filter, attempt count, harness, execution limit, schedule, or a second
model profile. The selected profile ID must occur in
`configs/experiment.yaml:model_profiles`.

Profile-resolution values loaded during preflight, such as provider endpoint or
authentication environment variables, are setup inputs rather than caller
parameters. Freeze them in the resolved profile before formal execution; never
accept them as per-invocation overrides.

Discover the task group by requiring exactly one directory under `task_group/`.
Load the entire fixed `skill_creators` list and all fixed modes from
`configs/experiment.yaml`; never construct a formal subset.

Load:

```text
configs/experiment.yaml
configs/models/<model_profile>.yaml
creators/<each configured creator>/manifest.yaml
```

Stop before formal runs if:

- The resolved model profile status remains blocked or any required resolved
  value is `null`.
- Any runtime option other than the single selected model profile was supplied.
- Generator and solver model/profile values differ.
- The staged task-group count is not exactly one, or the creator/mode set differs
  from the frozen experiment config.
- Any creator is unpinned, its entrypoint is missing, or its recorded hashes do
  not match the staged upstream bundle.
- The task group does not satisfy the expected structure.
- The resolved Codex executable, provider authentication, Responses protocol,
  tool calling, or primary trace cannot be verified.

First write the resolved model/provider values, without hashes or secrets, to:

```text
scratch/run_manifest/<model_profile>.resolved_profile.yaml
```

Hash the exact bytes of that closed artifact. Then write a sanitized resolved
run manifest to:

```text
scratch/run_manifest/<model_profile>.yaml
```

It must include the sole caller-supplied `model_profile`, confirmation that no
other runtime overrides were accepted, model IDs, reasoning values, provider ID,
creator revisions and hashes, Codex version/path, task-group ID, attempt counts,
execution limits, retry policy, randomized schedule seed/order, and preflight
results. It must also
record SHA-256 values for `configs/experiment.yaml`, the selected committed model
profile, the separate resolved-profile artifact, `creators/COMMON_CONTRACT.md`,
and `guides/agent_prompts.md`. Record a path-sorted manifest containing the
relative path and SHA-256 of every regular file in the complete task group; this
covers train/test inputs and answers, evaluators, environment build files, and
endpoint declarations. Also record the task group's file-mode digest.
Record the built environment image ID/digest, fixed agent-container UID:GID, and
the SHA-256 of a sanitized `environment_access.md` template whose credential
values are replaced by fixed placeholders. Never include secret values. Reject
symbolic links in the formal task group so the manifest cannot omit linked
content.

At profile start, generate a random HMAC key kept only in orchestrator memory or
a runtime-only secret file outside the workspace. Every physical run records an
HMAC-SHA-256 of the exact staged `environment_access.md` plus the frozen
sanitized-template SHA-256 in its metadata. This supports equality checks without
publishing a brute-forceable hash of task credentials and also covers future
infrastructure replacements. Never preserve the HMAC key; destroy it after the
profile is finalized.

Freeze this manifest before the first formal run. Immediately before and after
every physical run, compare all staged inputs, content/file-mode digests, image
identity, sanitized access template, and access HMAC against the frozen/logical
expected values. If any common input changes, stop the entire model profile
rather than continuing with incomparable branches.

## Docker Isolation

Mount only the current staged `/work` directory into an agent container. If
authentication or provider bootstrap is required, mount only the minimum file
read-only at a dedicated location. Never mount the host `CODEX_HOME`, host home,
full task group, full evaluation workspace, repository root, parent work
directory, `env/`, notes, evaluators, source test answers, previous runs, or
other creator bundles.

The `/work` root may be writable for required outputs, but overlay every staged
input as a separate read-only bind mount. For generation this includes
`creator/`, `creator_contract.md`, `train_tasks/`, `train_answers/`, and
`environment_access.md`. For solving it includes `input/`,
`environment_access.md`, and `skill/` when present. Recompute all relevant input
and generated-skill digests after the process exits; any mutation invalidates the
physical run.

Create `CODEX_HOME=/tmp/gdpevo-codex-home` inside the named container. Do not use
`--rm`; keep the stopped container until the primary trace and metadata have
been copied and verified.

For OpenAI authentication, mount only the active `auth.json` read-only, copy it
with mode `0600` into the container-local `CODEX_HOME`, and run
`codex login status` in that same container before the attempt. Do not copy the
host config, sessions, database, logs, plugins, skills, caches, or history.

For a custom provider, generate the minimum runtime provider configuration
inside the container from the resolved model profile. Pass the API key through
the declared environment variable. Do not stage provider config or credentials
under `/work`, and do not preserve them as artifacts.

For the DeepSeek scaffold, `.env` values are resolution inputs, not automatic
Codex overrides. Resolve them explicitly as follows and write only sanitized
values to the resolved run manifest:

```text
GDPEVO_DEEPSEEK_MODEL            -> generator.model and solver.model
GDPEVO_DEEPSEEK_PROVIDER_ID      -> generator/solver model_provider
GDPEVO_DEEPSEEK_BASE_URL         -> provider.base_url
GDPEVO_DEEPSEEK_REASONING_EFFORT -> generator/solver reasoning_effort
GDPEVO_DEEPSEEK_API_KEY_ENV      -> provider.env_key (the name, never the key)
```

Generate a minimum container-local Codex `config.toml` from those resolved
values. Do not edit the committed blocked profile in place. Resolve authentication,
model identity, Responses compatibility, and pricing separately; placeholder
strings beginning with `<` are unresolved and must fail preflight. Change only
the sanitized resolved manifest to ready after every probe passes.

## Task Environment Isolation

Build the environment from `task_group/<task_group_id>/env/Dockerfile`. If the
Dockerfile or `env.state_mode` is missing, stop and report an incompatible task
group rather than falling back to a host environment.

For every runtime scope, create a normal Docker bridge network whose name
contains normalized owner, task-group number, capability stage, model profile,
condition, creator when applicable, task/attempt when applicable, and an
eight-character random suffix. Use the same scope for `-env` and `-agent`
container suffixes. `task-env` is only the network alias, never a global
container name.

The environment listens on:

```text
TASK_ENV_BIND=0.0.0.0
TASK_ENV_PORT=9000 + numeric task-group id
```

Do not publish a host port. Agent containers use:

```text
http://task-env:<TASK_ENV_PORT>/
```

Do not create an `--internal` network; model-provider egress and normal DNS must
remain available.

Read `env.state_mode` from `task_group.yaml`. A read-only instance may be shared
only inside one capability stage. A mutable environment receives a fresh
network, environment container, and writable layer for every attempt. This
workspace never exposes the train-only judge to either few-shot generation or
test solving; use `TASK_ENV_ENABLE_JUDGE=0` for all formal stages.

Before formal attempts, verify `/health` from a disposable container attached
to the exact same network and record runtime names and results under
`scratch/environment/`.

## Model Profile And Command

Use the selected profile for both generator and solver. Do not silently map one
profile to another model or reasoning value.

The formal command shape is:

```bash
CODEX_HOME=/tmp/gdpevo-codex-home \
codex exec \
  -C /work \
  -m "<resolved_model_id>" \
  -c 'model_reasoning_effort="<resolved_effort>"' \
  --dangerously-bypass-approvals-and-sandbox \
  --json \
  "$PROMPT"
```

Apply the configured wall timeout outside this command. Do not add a
creator-specific model-output, turn, or tool-call limit. Record the exact command
shape, resolved default output-token behavior, start/end timestamps, duration,
and timeout status for each physical run.

Provider selection and custom-provider definitions must come from the sanitized
resolved runtime configuration generated from the model profile. Do not use
`--ephemeral`; formal attempts must leave native session traces.

If `codex` is not on `PATH`, locate it and record the path and version under
`scratch/run_manifest/`. Do not hard-code a host-specific executable in reusable
files.

For the DeepSeek profile, the orchestrator must prove that the selected endpoint
supports the Codex Responses wire protocol, streaming, tool calls, authentication,
the configured reasoning value, and trace token accounting. An
Anthropic-compatible or Chat-Completions-only endpoint is not sufficient.

Capture observed model identity in every physical run and compare it with the
preflight identity. If identity is missing where the profile requires capture,
or changes during a profile (especially for a preview model), stop the schedule
and mark the profile incomplete; do not pool runs from different identities.

## Skill-Generation Staging

For each model profile, creator, and attempt, create a dedicated directory:

```text
scratch/skill_generation/<model_profile>/<creator>/attempt_<nn>/physical_runs/<agent_run_id>/
```

Stage only:

```text
creator/                 # exact pinned upstream bundle for this creator only
creator_contract.md      # unchanged copy of creators/COMMON_CONTRACT.md
train_tasks/             # five official train input directories
train_answers/           # five matching answer.json files
environment_access.md    # allowed network environment entrypoint and endpoints
```

Do not stage another creator, manifests from another condition, test tasks,
test answers, notes, evaluator files, `env/`, prior runs, reports, or judge
instructions.

The process writes `/work/skill/` inside its immutable physical-run directory.
Keep it there while validating the required entrypoint and local references;
validation may report a failure but must not rewrite or improve the package.
Reject symbolic links, then calculate and record the complete package digest
using `sorted_relative_file_sha256_v1` plus the file-mode digest from
`creators/README.md`.

Only after package validation, trace matching, metadata, contamination checks,
and container cleanup/cleanup record all pass, copy the complete package without
semantic modification through a temporary sibling and atomic rename to:

```text
skills/<model_profile>/fewshot/<creator>/fewshot_attempt_<nn>/
```

Then copy the selected trace to its canonical path and atomically write
`selected_run.yaml`. An invalid or failed physical run remains only under
`physical_runs/<agent_run_id>/` and never occupies a canonical package path.

## Solver Staging

Base attempt:

```text
runs/<model_profile>/base/<test_id>/attempt_<nn>/physical_runs/<agent_run_id>/
```

Few-shot attempt:

```text
runs/<model_profile>/fewshot/<creator>/<test_id>/attempt_<nn>/physical_runs/<agent_run_id>/
```

Stage only the current test `input/`, `environment_access.md`, and, for
few-shot, the complete matching generated package as `skill/`. Solver
`attempt_<nn>` must use creator skill `fewshot_attempt_<nn>`.
Mount the generated package read-only. Recompute its content and file-mode
digests before staging and after the solver exits, and record both in solver
metadata; all values must match the corresponding generation record.

Do not stage train tasks, source answers, notes, evaluators, environment source,
other test tasks, another creator, another attempt, prior runs, or judge access.

## Fixed Prompt Contract

Use exactly one template from `guides/agent_prompts.md`. Replace only declared
angle-bracket placeholders. Do not append task hints, answer summaries, notes,
rubric/evaluator details, construction truth, or paths outside `/work`.

The mounted contents enforce information boundaries. The prompt identifies the
run and required output; it must not compensate for one creator with extra
domain guidance.

The prompt-visible `agent_run_id` is a freshly generated opaque UUID and must not
encode creator, model, task, condition, or attempt number. Keep the descriptive
logical attempt ID only in orchestrator metadata. For creator comparisons, do
not put the creator name in the prompt, container environment, or any staged path
visible under `/work`.

## Trace Preservation

Preserve exactly one primary Codex `rollout-*.jsonl` for every generation and
solver run. The runtime home remains inside the named container. After Codex
exits, use `docker cp` to extract only the matching file, or temporarily extract
only `sessions/` to `scratch/trace_extract/<run_id>/` for discovery.

Match the trace by run ID and `/work` path. Copy it to:

```text
original_traces/<model_profile>/skill_generation/<creator>/attempt_<nn>/rollout-*.jsonl
original_traces/<model_profile>/base/<test_id>/attempt_<nn>/rollout-*.jsonl
original_traces/<model_profile>/fewshot/<creator>/<test_id>/attempt_<nn>/rollout-*.jsonl
```

Those canonical locations contain only the trace selected for formal
aggregation. Before selection, keep each physical trace inside its immutable
`physical_runs/<agent_run_id>/audit/` directory. Failed or replaced physical
traces remain there and are never copied over the canonical selected trace.

Populate token, cost, turn, tool-call, model identity, contamination, and trace
metadata from the copied primary session. Only after verification may the
temporary extraction directory and stopped container be removed.

Never preserve the complete runtime home, config, credentials, plugins, skills,
caches, logs, databases, or stdout as trace artifacts. If the primary trace is
missing or ambiguous, preserve the failed physical run with null trace-derived
fields, clean up securely, and treat it as an infrastructure failure. A
replacement uses a new physical directory and opaque agent run ID; do not guess
trace-derived fields or overwrite the failed record.

A formal attempt included in aggregation is complete only when its output package
or `answer.json`, uniquely matched primary trace, score when applicable,
metadata, validation/contamination status, and cleanup record are present.
