# Effective request resolution

Resolve exactly one effective request before any data access, fold, random draw, fit, aggregation, or decision, and use it consistently in every module.

## Activation

- If the request declares a `protocol_id`, treat it as the **exact, case-sensitive** activation key. Family membership, a similar name, or similar subject matter is **not** a match.
- If the request declares only a `request_id` (no protocol profile), resolve the request as-is; there is no profile to merge.

## Base

Start from the registered method profile for the exact protocol version and its inherited canonical defaults. The method itself lives in this skill's references (`numerical_conventions.md`, `module_families.md`); the request does not redefine the method, it binds instance values onto it.

## Override targets

- A **direct** root key `k` targets the canonical root key of the identical name. Inside a named section or module, a direct child key `k` targets only the identical child path.
- A root key named `<section>_overrides` targets canonical `<section>` (strip only the terminal `_overrides`).
- `module_overrides.<module_name>` targets the canonical top-level module of that exact name.
- `reporting_overrides` targets `reporting`.

## Merge (apply resolved entries in request document order)

- **Objects** recursively merge by exact key.
- **Arrays** replace the whole array — never concatenate, union, or merge by position.
- **Explicit scalars/strings/booleans/null** replace only their exact paths.
- **Absent paths** inherit unchanged.
- Task-local direct bindings and resolved overrides take precedence over inherited values at the same path.

## Validation (reject before any computation)

- No array concatenation or positional patching.
- No inferred aliases, key renaming, or type coercion.
- Reject unknown targets and incompatible types.

## Freeze

Resolve one effective request and use it in every module. Do not re-derive bindings mid-audit, and do not let one module's results redefine another module's effective bindings.
