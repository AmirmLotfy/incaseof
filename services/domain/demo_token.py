"""Short-lived credentials for the isolated, synthetic public judge demo."""

from __future__ import annotations

import base64
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from .clock import require_aware
from .ids import PersonId
from .responder_token import MIN_KEY_BYTES, TokenError

TOKEN_VERSION = 1
DEFAULT_LIFETIME = timedelta(minutes=30)


@dataclass(frozen=True, slots=True)
class DemoClaims:
    person_id: PersonId
    expires_at: datetime


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _key(key: bytes) -> bytes:
    if len(key) < MIN_KEY_BYTES:
        raise TokenError("signing_key_too_short")
    return key


def issue(
    person_id: PersonId,
    *,
    key: bytes,
    now: datetime,
    lifetime: timedelta = DEFAULT_LIFETIME,
) -> str:
    require_aware(now, "now")
    if not str(person_id).startswith("demo-"):
        raise TokenError("not_demo_subject")
    body = json.dumps(
        {
            "v": TOKEN_VERSION,
            "kind": "judge-demo-session",
            "s": str(person_id),
            "e": int((now + lifetime).timestamp()),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return f"{_b64(body)}.{_b64(hmac.new(_key(key), body, sha256).digest())}"


def verify(token: str, *, key: bytes, now: datetime) -> DemoClaims:
    require_aware(now, "now")
    try:
        encoded_body, encoded_signature = token.split(".")
        body = _unb64(encoded_body)
        signature = _unb64(encoded_signature)
    except (TypeError, ValueError) as error:
        raise TokenError("malformed") from error
    if not hmac.compare_digest(signature, hmac.new(_key(key), body, sha256).digest()):
        raise TokenError("bad_signature")
    try:
        payload = json.loads(body)
        if payload.get("v") != TOKEN_VERSION or payload.get("kind") != "judge-demo-session":
            raise TokenError("wrong_audience")
        person_id = PersonId(str(payload["s"]))
        expires_at = datetime.fromtimestamp(int(payload["e"]), tz=UTC)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise TokenError("malformed_payload") from error
    if not str(person_id).startswith("demo-"):
        raise TokenError("not_demo_subject")
    if now >= expires_at:
        raise TokenError("expired")
    return DemoClaims(person_id=person_id, expires_at=expires_at)
