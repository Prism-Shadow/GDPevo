# Metric And Scoring

Calculate `acc@3` and population `std@3` separately for:

```text
<model_profile>/base
<model_profile>/fewshot/codex
<model_profile>/fewshot/cc
<model_profile>/fewshot/deepagents
<model_profile>/fewshot/opencode
```

Never merge creators into one few-shot score or create creator-specific copies
of base.

## Solver Attempt Metadata

Each valid solver attempt produces:

```text
answer.json
score.yaml
run_metadata.yaml
```

Record at least:

```yaml
agent_run_id: <opaque UUID>
model_profile: <profile id>
condition: <base|fewshot>
skill_creator: <none|codex|cc|deepagents|opencode>
task_id: <test id>
attempt: <1|2|3>
prompt_template_id: <base_test_solver|fewshot_test_solver>
prompt_template_sha256: <sha256>
rendered_prompt_sha256: <sha256>
generator_harness: <codex|null>
solver_harness: codex
generator_model: <resolved model|null>
solver_model: <resolved model>
reasoning_effort: <resolved value>
provider_id: <resolved provider>
observed_model_identity: <identity|null>
skill_dir: <matching package|null>
skill_bundle_sha256: <sha256|null>
duration_seconds: <float>
timeout_status: <not_timed_out|timed_out>
trace_file: <canonical rollout path|null>
trace_match_status: <matched|missing|ambiguous>
input_tokens: <int|null>
cached_input_tokens: <int|null>
output_tokens: <int|null>
reasoning_output_tokens: <int|null>
total_tokens: <int|null>
cost_usd: <float|null>
assistant_turns: <int|null>
tool_calls: <int|null>
status: <valid|logical_failure|infrastructure_failure|contaminated|not_runnable>
```

For few-shot, the recorded package digest must match its generation record.

## Generation Attempt Metadata

Store one record under:

```text
scratch/skill_generation/<model_profile>/<creator>/attempt_<nn>/evolve_metadata.yaml
```

Record at least:

```yaml
agent_run_id: <opaque UUID>
model_profile: <profile id>
skill_creator: <creator id>
attempt: <1|2|3>
prompt_template_id: fewshot_skill_generation
prompt_template_sha256: <sha256>
rendered_prompt_sha256: <sha256>
generator_harness: codex
generator_model: <resolved model>
reasoning_effort: <resolved value>
provider_id: <resolved provider>
observed_model_identity: <identity|null>
creator_revision: <immutable revision>
creator_bundle_sha256: <sha256>
skill_dir: <canonical package|null>
skill_bundle_sha256: <sha256|null>
skill_file_modes_sha256: <sha256|null>
validation_status: <valid|invalid|missing|contaminated>
file_count: <int|null>
bytes: <int|null>
portability_warnings: []
duration_seconds: <float>
timeout_status: <not_timed_out|timed_out>
trace_file: <canonical rollout path|null>
trace_match_status: <matched|missing|ambiguous>
input_tokens: <int|null>
cached_input_tokens: <int|null>
output_tokens: <int|null>
reasoning_output_tokens: <int|null>
total_tokens: <int|null>
cost_usd: <float|null>
assistant_turns: <int|null>
tool_calls: <int|null>
status: <valid|logical_failure|infrastructure_failure|contaminated>
```

Generation usage is reported separately from solver efficiency.

## Trace Accounting

Use the final session-cumulative usage snapshot from the matching Codex primary
trace. Do not sum cumulative token events. If a provider exposes non-cumulative
per-response usage, document that mode and count one final record per stable
response ID.

Count assistant/model responses by stable response ID. Count solver-initiated
`function_call` and `custom_tool_call` items; do not count tool results.

If the trace is missing or ambiguous due to orchestration, classify the
physical execution as infrastructure failure, preserve it under
`scratch/infrastructure_failures/`, and rerun the same logical slot with a new
UUID. Do not estimate trace-derived fields.

## Cost

For normal Codex traces:

```text
uncached_input_tokens = max(input_tokens - cached_input_tokens, 0)

cost_usd =
  (uncached_input_tokens * uncached_input_rate
   + cached_input_tokens * cached_input_rate
   + output_tokens * output_rate) / 1_000_000
```

`cached_input_tokens` is a subset of `input_tokens`, and reasoning output is a
subset of output. Do not charge either twice. Use:

```text
total_tokens = input_tokens + output_tokens
```

If provider semantics or pricing are unresolved, leave cost null and record the
reason.

## Score Normalization

Normalize evaluator output to `[0, 1]`. Prefer an explicit normalized score;
otherwise use a documented `earned / maximum` field. Do not guess.

## acc@3

For one test task:

```text
task acc@3 = (score_01 + score_02 + score_03) / 3
```

For one branch:

```text
overall acc@3 = mean(test_001 acc@3, ..., test_005 acc@3)
```

## population std@3

For one task with mean `m`:

```text
task std@3 = sqrt(((s1-m)^2 + (s2-m)^2 + (s3-m)^2) / 3)
```

For one branch:

```text
overall std@3 = mean(test_001 std@3, ..., test_005 std@3)
```

## Creator Comparisons

Creator lift uses the one shared base:

```text
lift(c) = fewshot_acc@3(c) - shared_base_acc@3
```

Pairwise difference:

```text
delta(a,b) = fewshot_acc@3(a) - fewshot_acc@3(b)
```

Report all six unordered creator pairs. Preserve task-level differences. If a
required branch is incomplete, mark the comparison unavailable rather than
filling missing values with zero.

## Efficiency

For solver efficiency, average three attempts for each test task and then
average the five task values. Apply this independently to:

- input, cached input, output, and reasoning output tokens
- cost
- assistant turns
- tool calls

Count only selected formal solver processes. Exclude infrastructure
replacements, generation, environment checks, evaluators, and orchestrator
work.

For each creator, separately average its three generation attempts for usage,
duration, package size, and file count. Also report:

```text
valid_generation_rate = valid packages / 3
```

## Completeness And Failures

Base requires 15 valid solver scores. A creator branch requires 3 valid packages
and 15 matching valid solver scores. Missing packages are not scored as zero and
are never replaced with base.

Logical creator failures include missing/invalid packages, refusal to follow the
one-pass contract, agent timeout, or agent-originated boundary violations.
Logical solver failures include missing/unparseable answers, agent timeout, or
agent-originated boundary violations. Preserve them and do not retry for
quality.

Retry only verified infrastructure failures while keeping the logical slot
unchanged. Evaluator execution may be retried only against byte-identical solver
output.

Compute all metrics within one model profile. Never pool profiles.
