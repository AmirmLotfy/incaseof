# Golden fixtures

Shared across Python, Kotlin and TypeScript so the three stacks cannot drift. If a fixture changes,
every stack's tests see the change on the next run — that is the point.

## `valid/`
Must validate against `packages/domain-schemas/compiled-plan.schema.json`.

- **`solo-hike.json`** — the canonical worked example from the build contract. This is the plan the
  demo narrative compiles from natural language.
- **`evening-routine.json`** — recurring plan using the **P0 channel ladder** (push → push → SMS →
  responder), i.e. no dependency on Amazon Connect.
- **`recovery-interval.json`** — repeating interval plan ("check every three hours tonight").

## `invalid/`
Must **fail** validation. Each isolates exactly one rule so a failure is diagnostic rather than
vague.

| Fixture | Rule it proves |
|---|---|
| `responder-step-without-role.json` | Responder actions must name a role |
| `subject-step-with-role.json` | Subject actions must not address a responder |
| `no-stop-conditions.json` | A plan with no way to close would escalate forever |
| `missing-timezone.json` | An unzoned deadline silently moves across DST and travel |
| `arbitrary-phone-target.json` | **The structural prompt-injection defence** — the schema has no vocabulary for a raw endpoint |
| `unknown-stop-condition.json` | Delivery is not resolution |

### The `_why` key

Invalid fixtures carry a root-level `_why` explaining their purpose. Because the schema sets
`additionalProperties: false`, `_why` would itself cause a validation failure — which would make
every negative test pass for the wrong reason and prove nothing.

**Test harnesses must strip the root-level `_why` key before validating.** The shared Python
helper `services/tests/conftest.py::load_fixture` does this; any other stack reading these fixtures
must do the same.
