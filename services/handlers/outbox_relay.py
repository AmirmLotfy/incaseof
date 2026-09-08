"""Retry durable pending intents without reclaiming uncertain provider attempts."""

from __future__ import annotations

from typing import Any

from services.handlers import bootstrap


def relay(ctx: bootstrap.Context) -> int:
    if ctx.outbox is None or ctx.queue is None:
        raise RuntimeError("outbox relay is not configured")
    ctx.outbox.reconcile_stale(ctx.now())
    count = 0
    for intent in ctx.outbox.pending():
        row = ctx.outbox.get(intent.idempotency_key)
        if row is None or row["status"] != "PENDING":
            continue
        alert = ctx.alerts.get(intent.alert_id)
        if alert is not None and alert.is_paused:
            continue
        ctx.queue.enqueue(intent)
        count += 1
    return count


def handler(event: dict[str, Any], _context: Any = None) -> dict[str, int]:
    del event
    return {"relayed": relay(bootstrap.build())}
