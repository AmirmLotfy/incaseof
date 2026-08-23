"""Responder tokens.

A responder has no account. They are somebody's sister, at 2am, holding a link — and
requiring them to sign up before they can say "I've got her" would defeat the point of the
product. So the link *is* the credential, which means it has to be scoped as tightly as a
credential that arrives by SMS deserves.

Every rule here exists because of what a leaked token could otherwise do:

* **One Alert only.** Not a session. A captured link exposes one incident for a short
  window, and nothing about any other Alert, Plan or Circle member.
* **Short lifetime**, bounded by the Alert itself. A link found in a message thread a week
  later is inert.
* **A nonce**, so a specific token can be revoked without invalidating the signing key and
  every other outstanding link with it.
* **No subject data in the payload.** The token names identifiers; everything human is
  fetched server-side after the token is validated.

Pure and dependency-free, so every one of those properties is unit-testable.
"""

from __future__ import annotations

import base64
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from hashlib import sha256

from .clock import require_aware
from .ids import AlertId, PersonId

# Long enough for somebody to notice an SMS, get to a screen and act; short enough that a
# link resurfacing later is useless. The Alert's own lifetime bounds it further.
DEFAULT_LIFETIME = timedelta(hours=4)

TOKEN_VERSION = 1


class TokenError(Exception):
    """A token that cannot be trusted.

    Deliberately one type with a coarse message. Distinguishing "expired" from "bad
    signature" from "unknown alert" tells an attacker which half of a guess was right.
    """

    def __init__(self, reason: str) -> None:
        super().__init__("This link is not valid.")
        # Kept for the audit trail and server logs, never returned to the caller.
        self.reason = reason


class ResponderPermission(StrEnum):
    """What a link allows. Deliberately narrow.

    There is no VIEW_PLAN, no VIEW_CIRCLE and no VIEW_HISTORY: a responder needs to know
    that this person has not checked in and what has been tried, not the shape of
    somebody's life.
    """

    VIEW_ALERT = "VIEW_ALERT"
    CLAIM = "CLAIM"
    EXTEND = "EXTEND"
    REPORT_UNABLE = "REPORT_UNABLE"
    RESOLVE = "RESOLVE"


RESPONDER_PERMISSIONS = frozenset(ResponderPermission)


@dataclass(frozen=True, slots=True)
class ResponderClaims:
    """What a validated token asserts."""

    alert_id: AlertId
    responder_id: PersonId
    permissions: frozenset[ResponderPermission]
    expires_at: datetime
    nonce: str

    def allows(self, permission: ResponderPermission) -> bool:
        return permission in self.permissions

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


# HMAC accepts an empty key and produces a perfectly valid signature with it. That would
# make every responder link forgeable by anyone who knew the scheme, and it would look
# entirely normal in testing — tokens would issue and verify. So the key length is checked
# rather than assumed.
MIN_KEY_BYTES = 32


def _require_key(key: bytes) -> bytes:
    if len(key) < MIN_KEY_BYTES:
        raise TokenError("signing_key_too_short")
    return key


def _signature(payload: bytes, key: bytes) -> bytes:
    return hmac.new(key, payload, sha256).digest()


def issue(
    *,
    alert_id: AlertId,
    responder_id: PersonId,
    nonce: str,
    key: bytes,
    now: datetime,
    lifetime: timedelta = DEFAULT_LIFETIME,
    permissions: frozenset[ResponderPermission] = RESPONDER_PERMISSIONS,
) -> str:
    """Mint a token for one responder, for one Alert.

    The nonce is supplied rather than generated here so the caller records it in the same
    write that issues the token — a token whose nonce was never stored cannot be revoked.
    """
    require_aware(now, "now")
    _require_key(key)
    payload = {
        "v": TOKEN_VERSION,
        "a": str(alert_id),
        "r": str(responder_id),
        "p": sorted(p.value for p in permissions),
        "e": int((now + lifetime).timestamp()),
        "n": nonce,
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return f"{_b64(body)}.{_b64(_signature(body, key))}"


def verify(token: str, *, key: bytes, now: datetime) -> ResponderClaims:
    """Validate signature and expiry, and return what the token asserts.

    This does **not** check revocation, membership, consent, or whether the Alert is still
    open. Those need storage and belong to the caller, which keeps this function pure and
    keeps the checks from being accidentally satisfied by a well-formed token.
    """
    require_aware(now, "now")
    _require_key(key)

    try:
        encoded_body, encoded_signature = token.split(".")
        body = _unb64(encoded_body)
        signature = _unb64(encoded_signature)
    except (ValueError, TypeError) as error:
        raise TokenError("malformed") from error

    # Constant-time: a byte-by-byte comparison leaks how much of a forged signature was
    # correct, which is enough to reconstruct one.
    if not hmac.compare_digest(signature, _signature(body, key)):
        raise TokenError("bad_signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as error:
        raise TokenError("malformed_payload") from error

    if payload.get("v") != TOKEN_VERSION:
        raise TokenError("unsupported_version")

    expires_at = datetime.fromtimestamp(int(payload["e"]), tz=UTC)
    claims = ResponderClaims(
        alert_id=AlertId(payload["a"]),
        responder_id=PersonId(payload["r"]),
        permissions=frozenset(
            ResponderPermission(p) for p in payload["p"] if p in RESPONDER_PERMISSIONS
        ),
        expires_at=expires_at,
        nonce=payload["n"],
    )

    if claims.is_expired(now):
        raise TokenError("expired")

    return claims
