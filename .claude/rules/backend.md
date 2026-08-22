---
description: Python services, domain logic, workflows
globs: ["services/**", "packages/**"]
---

# Backend rules

## The state machine is normative
`docs/PRODUCT-STATES.md` defines every Alert transition. Implementations derive from it. If the
code needs a transition the document does not have, change the document first, deliberately.

## Invariants to assert in tests, not assume
1. One Moment produces **at most one** Alert.
2. An Alert is pinned to one Plan Version for its whole life.
3. Terminal states never transition out.
4. Reaching a terminal state cancels all pending external actions.
5. An action with an existing idempotency key is never dispatched twice.
6. A lease expiry resumes escalation **at the right step** — never restarts the ladder.

## Every external action
```
idempotency_key = alert_id + escalation_step_id + attempt_number
```
Guarded by a DynamoDB conditional write. Never call a provider directly from a workflow — write an
ActionIntent, then outbox → SQS → worker → provider → callback.

## Style
- Pin versions exactly. No ranges.
- `ruff` + `ruff format` + `mypy --strict` all pass before a change is done.
- Type everything. `Any` needs a comment explaining why.
- Domain logic has no AWS imports — keep it testable without mocking the cloud.

## Time
- All stored timestamps are UTC. All user-facing times render in the plan's IANA timezone.
- A plan without an explicit timezone is a bug: DST and travel silently move the deadline.
- Never use wall-clock arithmetic across a DST boundary; use zoneinfo.
