# Runtime Access Reference

How to reach the Harborview Synthetic Clinic runtime safely. The values below are **placeholders** — always read the actual `environment_access.md` staged in the work directory for the run, because the base URL, allowed endpoint set, and any token can change per run.

## 1. Read environment_access.md literally

- Copy the **Base URL** verbatim. Substitute it for every `<TASK_ENV_BASE_URL>` in the task prompt.
- Treat the **allowed endpoints** list as a closed set. If an endpoint you think you need is not listed, do not call it; work with what is allowed.
- Copy any required **auth header** (name and value) exactly. Do not re-derive, abbreviate, or guess it.

## 2. Endpoint categories

Typical allowed endpoints (only use those actually listed for the run):

- **Case / patient context**: `GET /api/patients`, `GET /api/patients/{patient_id}`, `GET /api/cases`, `GET /api/cases/{case_id}`
- **Clinical resources**: `GET /api/observations`, `GET /api/medications`, `GET /api/allergies`, `GET /api/problems`, `GET /api/imaging`
- **Care context**: `GET /api/care-registry`, `GET /api/sdoh`
- **Protocols**: `GET /api/protocols`, `GET /api/protocols/{protocol_id}`
- **Filtered query**: `POST /api/query` — requires the run's auth header; use for precise filtered retrieval (patient + code + window + status) instead of paging broad lists.

## 3. Calling pattern

1. Start at `GET /api/cases/{case_id}` to confirm the case and read its `patient_id`.
2. Use that `patient_id` for all patient-scoped fetches.
3. For protocol-gated decisions, fetch `GET /api/protocols` to find the governing protocol id, then `GET /api/protocols/{protocol_id}` for thresholds/red-flags/actions.
4. Use `POST /api/query` (with auth header) when you need a filtered slice, e.g. all final observations of a given code for a patient inside a time window.
5. Capture the stable id of every resource you rely on for `evidence_ids`.

## 4. Read-only rule

Never mutate the runtime. Do not place orders, do not write, do not call any non-GET state-changing endpoint. The only POST allowed is the read-only `POST /api/query`.

## 5. Failure handling

- If a listed endpoint returns an error or an unexpected shape, do not paper over it with a guessed value. Surface the problem rather than fabricate.
- If `environment_access.md` is missing or lists no usable base URL, stop and report — do not invent a URL.
