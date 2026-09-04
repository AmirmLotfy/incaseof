"""Short-lived, single-invitation credentials for Circle consent."""

from __future__ import annotations

import base64
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from .clock import require_aware
from .ids import InvitationId
from .responder_token import MIN_KEY_BYTES, TokenError

DEFAULT_LIFETIME = timedelta(days=7)
TOKEN_VERSION = 1


@dataclass(frozen=True, slots=True)
class InvitationClaims:
    invitation_id: InvitationId
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
    invitation_id: InvitationId,
    *,
    key: bytes,
    now: datetime,
    lifetime: timedelta = DEFAULT_LIFETIME,
) -> str:
    require_aware(now, "now")
    body = json.dumps(
        {
            "v": TOKEN_VERSION,
            "kind": "circle-invitation",
            "i": str(invitation_id),
            "e": int((now + lifetime).timestamp()),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    return f"{_b64(body)}.{_b64(hmac.new(_key(key), body, sha256).digest())}"


def verify(token: str, *, key: bytes, now: datetime) -> InvitationClaims:
    require_aware(now, "now")
    try:
        encoded_body, encoded_signature = token.split(".")
        body = _unb64(encoded_body)
        signature = _unb64(encoded_signature)
    except (TypeError, ValueError) as error:
        raise TokenError("malformed") from error
    expected = hmac.new(_key(key), body, sha256).digest()
    if not hmac.compare_digest(signature, expected):
        raise TokenError("bad_signature")
    try:
        payload = json.loads(body)
        if payload.get("v") != TOKEN_VERSION or payload.get("kind") != "circle-invitation":
            raise TokenError("wrong_audience")
        expires_at = datetime.fromtimestamp(int(payload["e"]), tz=UTC)
        invitation_id = InvitationId(str(payload["i"]))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise TokenError("malformed_payload") from error
    if now >= expires_at:
        raise TokenError("expired")
    return InvitationClaims(invitation_id=invitation_id, expires_at=expires_at)
