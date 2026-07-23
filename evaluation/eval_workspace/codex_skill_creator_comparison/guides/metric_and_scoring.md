# Metric And Scoring

The primary metrics are `acc@3` and population `std@3`, calculated separately
for the shared base and each creator-specific few-shot branch.

## Scored Branch Identity

A branch is identified by:

```text
<model_profile>/base
<model_profile>/fewshot/<creator>
```

Never merge creators into one `fewshot` score. Never create creator-specific
copies of base.

## Single Solver Run

A valid solver run is one clean-context Codex process solving exactly one test
task under one branch. It produces:

```text
answer.json
score.yaml
run_metadata.yaml
```

Recommended metadata:

```yaml
logical_attempt_id: <descriptive id kept outside the agent prompt>
agent_run_id: <opaque UUID shown in the prompt>
model_profile: <model profile id>
condition: <base|fewshot>
skill_creator: <none|codex|cc|deepagents|opencode>
task_id: <test id>
attempt: <int>
generator_harness: codex
solver_harness: codex
generator_model: <resolved model id or null for base>
solver_model: <resolved model id>
generator_reasoning_effort: <resolved value or null for base>
solver_reasoning_effort: <resolved value>
generator_provider_id: <resolved provider id or null for base>
solver_provider_id: <resolved provider id>
observed_model_identity: <trace/provider identity or null>
model_identity_match_status: <matched|missing|changed>
skill_dir: <matching generated package or null>
skill_integrity:
  content_sha256_expected: <generation-record digest or null>
  content_sha256_before: <sha256 or null>
  content_sha256_after: <sha256 or null>
  file_modes_digest_algorithm: git_executable_bit_v1
  file_modes_sha256_expected: <generation-record digest or null>
  file_modes_sha256_before: <sha256 or null>
  file_modes_sha256_after: <sha256 or null>
duration_seconds: <float>
timeout_status: <not_timed_out|timed_out>
agent_container_uid_gid: "0:0"
staged_input_integrity:
  frozen_manifest_match_before: <bool>
  frozen_manifest_match_after: <bool>
  sanitized_environment_access_sha256: <sha256>
  environment_access_hmac_sha256: <hmac>

trace:
  copied_trace_file: <path under original_traces/ or null>
  session_id: <id or null>
  match_status: <matched|missing|ambiguous>
  missing_reason: <string or null>

token_usage:
  source: codex_session_trace
  input_tokens: <int or null>
  cached_input_tokens: <int or null>
  output_tokens: <int or null>
  reasoning_output_tokens: <int or null>
  total_tokens: <int or null>

cost_usd: <float or null>
turn_count:
  source: codex_session_trace
  assistant_turns: <int or null>
tool_call_count:
  source: codex_session_trace
  calls: <int or null>
```

If a trace cannot be matched uniquely, leave all trace-derived fields `null`
and preserve the physical run as an excluded infrastructure failure. Do not
estimate them manually or include that physical run in formal aggregation. A
replacement must use a new directory and opaque `agent_run_id`.

## Generation Run

Each creator has three independent generation records:

```text
scratch/skill_generation/<model_profile>/<creator>/attempt_<nn>/physical_runs/<agent_run_id>/evolve_metadata.yaml
```

Recommended fields:

```yaml
logical_attempt_id: <descriptive id kept outside the agent prompt>
agent_run_id: <opaque UUID shown in the prompt>
model_profile: <model profile id>
condition: fewshot
skill_creator: <creator id>
attempt: <int>
generator_harness: codex
generator_model: <resolved model id>
generator_reasoning_effort: <resolved value>
generator_provider_id: <resolved provider id>
observed_model_identity: <trace/provider identity or null>
model_identity_match_status: <matched|missing|changed>
duration_seconds: <float>
timeout_status: <not_timed_out|timed_out>
agent_container_uid_gid: "0:0"
staged_input_integrity:
  frozen_manifest_match_before: <bool>
  frozen_manifest_match_after: <bool>
  sanitized_environment_access_sha256: <sha256>
  environment_access_hmac_sha256: <hmac>

creator_source:
  revision: <immutable revision>
  skill_md_sha256: <sha256>
  bundle_sha256: <sha256>
  file_modes_digest_algorithm: git_executable_bit_v1
  file_modes_sha256: <sha256>

output:
  skill_dir: <canonical generated package path or null>
  skill_bundle_sha256: <sha256 or null>
  digest_algorithm: sorted_relative_file_sha256_v1
  file_modes_digest_algorithm: git_executable_bit_v1
  file_modes_sha256: <sha256 or null>
  entrypoint_present: <bool>
  validation_status: <valid|invalid|missing|contaminated>
  file_count: <int or null>
  bytes: <int or null>
  portability_warnings: []

trace:
  copied_trace_file: <path or null>
  session_id: <id or null>
  match_status: <matched|missing|ambiguous>

token_usage:
  source: codex_session_trace
  input_tokens: <int or null>
  cached_input_tokens: <int or null>
  output_tokens: <int or null>
  reasoning_output_tokens: <int or null>
  total_tokens: <int or null>

cost_usd: <float or null>
assistant_turns: <int or null>
tool_calls: <int or null>
```

Generation usage is reported separately from solver efficiency. Do not add it
to solver token, turn, or tool-call averages.

## Codex Token And Cost Accounting

For the normal Codex session-cumulative token event, use only the final
cumulative usage snapshot for the entire isolated session. Never sum cumulative
snapshots across trace events or responses. If a verified Codex/provider variant
instead exposes non-cumulative per-response usage, record that accounting mode
and sum exactly one final usage record per stable response ID. Never mix the two
accounting modes. Response-ID deduplication for turns and tool calls does not
justify summing session-cumulative token snapshots.

In Codex traces, `cached_input_tokens` is a subset of `input_tokens`, and
`reasoning_output_tokens` is a subset of `output_tokens`. Therefore:

```text
uncached_input_tokens = max(input_tokens - cached_input_tokens, 0)

cost_usd =
  (uncached_input_tokens * profile.uncached_input_usd_per_million
   + cached_input_tokens * profile.cached_input_usd_per_million
   + output_tokens * profile.output_usd_per_million) / 1_000_000
```

Do not charge reasoning output a second time. Keep `input_tokens` as the gross
input value in metadata and reports; `total_tokens = input_tokens +
output_tokens`, because cached and reasoning buckets are subsets. A model profile may calculate cost only
after preflight confirms that its provider trace uses these bucket semantics and
its rate card is resolved; otherwise keep `cost_usd` null with a reason.

## Score Normalization

Normalize evaluator results to `[0, 1]`. Prefer an explicit normalized score;
otherwise use a documented `earned / maximum` field. If normalization cannot be
determined, fail the attempt instead of guessing.

## acc@3

For one test task in one branch:

```text
task acc@3 = (score_01 + score_02 + score_03) / 3
```

Overall branch accuracy:

```text
overall acc@3 = mean(test_001 acc@3, ..., test_005 acc@3)
```

## population std@3

For one test task with mean `m`:

```text
task std@3 = sqrt(((s1-m)^2 + (s2-m)^2 + (s3-m)^2) / 3)
```

Overall branch dispersion:

```text
overall std@3 = mean(test_001 std@3, ..., test_005 std@3)
```

## Shared-Base Lift

For creator `c` within one model profile:

```text
lift(c) = fewshot_acc@3(c) - shared_base_acc@3
```

All four creator lifts must reference the exact same base value and base attempt
set.

## Pairwise Creator Difference

For creators `a` and `b`:

```text
delta(a,b) = fewshot_acc@3(a) - fewshot_acc@3(b)
```

Report all six unordered creator pairs. Compute the difference for each test task
first, then average the five task differences. Preserve all five task-level
differences under the corresponding pair in the formal report. If either branch
is incomplete, mark the pair unavailable and leave its delta fields null.

## Solver Efficiency

For each task, average its three attempts, then average the five task values.
Apply that shape independently to:

- gross input tokens
- cached input tokens
- output tokens
- reasoning output tokens
- USD cost
- assistant/model-response turns
- tool calls

Count only the formal test solver process. Exclude generation, environment
checks, evaluators, retries that were replaced, and orchestrator work.

For Codex traces, count assistant/model responses by stable response/message ID
and count solver-initiated `function_call` and `custom_tool_call` items. Do not
count tool results.

## Generation Efficiency And Reliability

For each creator, report the arithmetic average across three generation
attempts for all token, cost, turn, tool-call, duration, package-size, and
file-count fields when present.

Also report:

```text
valid_generation_rate = valid packages / 3
```

Formal downstream `acc@3` requires three valid generated packages and their
matching solver attempts. Do not assign an arbitrary score of zero to a missing
skill and do not silently substitute base. If a creator cannot produce three
valid packages under the fixed contract, mark the branch incomplete and report
the creator failure rather than publishing a misleading `acc@3`.

## Failures And Retries

Infrastructure failures include unavailable provider/network, container start
failure, or missing trace caused by orchestration. Preserve evidence and rerun
the same logical attempt with a new physical directory and opaque agent run ID
after fixing only the infrastructure defect. The fixed external wall timeout is
not an infrastructure defect when the agent simply exhausts it.

Logical creator failures include no package, invalid entrypoint, agent-originated
forbidden access despite correct staging/isolation, or refusal to complete the
common one-pass contract. Preserve and report them. Do not fix the upstream
creator or generated skill during the experiment.

Logical solver failures include missing/unparseable `answer.json`, exhausting
the fixed timeout, or other failure by the solver process. Preserve the failed
record, do not retry it merely to obtain a valid answer, and mark the branch
incomplete.
An incomplete base leaves base metrics and all lifts null, but it does not erase
otherwise complete creator scores or creator-to-creator deltas.
An evaluator crash or non-normalizable evaluator output may be retried only when
the solver output is unchanged and the failure is verified as infrastructure.

Contaminated attempts never enter scores or aggregation. Only contamination
caused by a verified staging/isolation defect receives a replacement, using a
clean directory and new opaque `agent_run_id`. Agent-originated boundary
violations are logical failures and are not retried.

## Model Separation

Compute every metric within one resolved model profile. A comparison report may
place model profiles side by side but must not pool their attempts, pricing, or
token buckets.
