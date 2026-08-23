"""The two adapter families must be indistinguishable to a caller.

The in-memory adapters exist so invariants can be proven without the cloud. That argument
only holds while a caller cannot tell which one it has — a divergence in key names or
return shapes makes a test pass against one and fail against the other, which is worse than
having no in-memory adapter at all.
"""

from __future__ import annotations

from typing import Any

from services.adapters.dynamo import DynamoAuditLog
from services.adapters.memory import InMemoryAuditLog
from services.domain.clock import utc
from services.domain.ids import AlertId

ALERT = AlertId("alert-1")
AT = utc(2026, 8, 26, 21, 0)


def _write(log: Any) -> None:
    log.append(
        alert_id=ALERT,
        actor_type="SYSTEM",
        actor_id="workflow",
        event_type="MOMENT_DUE",
        at=AT,
        metadata={"sequence": "1"},
    )


def test_the_audit_log_returns_the_same_keys_from_both_adapters(table: Any) -> None:
    memory = InMemoryAuditLog()
    dynamo = DynamoAuditLog(table)

    _write(memory)
    _write(dynamo)

    from_memory = memory.for_alert(ALERT)[0]
    from_dynamo = dynamo.for_alert(ALERT)[0]

    shared = {"alertId", "actorType", "actorId", "eventType", "at", "metadata"}
    assert shared <= set(from_memory), f"in-memory missing {shared - set(from_memory)}"
    assert shared <= set(from_dynamo), f"dynamo missing {shared - set(from_dynamo)}"

    for key in shared:
        assert from_memory[key] == from_dynamo[key], (
            f"adapters disagree on {key}: {from_memory[key]!r} vs {from_dynamo[key]!r}"
        )


def test_both_adapters_scope_reads_to_one_alert(table: Any) -> None:
    memory = InMemoryAuditLog()
    dynamo = DynamoAuditLog(table)

    for log in (memory, dynamo):
        _write(log)
        log.append(
            alert_id=AlertId("alert-2"),
            actor_type="SYSTEM",
            actor_id="workflow",
            event_type="MOMENT_DUE",
            at=AT,
        )

    assert len(memory.for_alert(ALERT)) == 1
    assert len(dynamo.for_alert(ALERT)) == 1
