"""Responder token tests.

The link is the credential, and it travels by SMS to somebody with no account. These are
the checks that decide what a captured link is worth.
"""

from __future__ import annotations

import base64
import json
from datetime import timedelta

import pytest

from services.domain.clock import utc
from services.domain.ids import AlertId, PersonId
from services.domain.responder_token import (
    RESPONDER_PERMISSIONS,
    ResponderPermission,
    TokenError,
    issue,
    verify,
)

KEY = b"a-signing-key-that-lives-in-secrets-manager"
OTHER_KEY = b"a-different-signing-key-entirely-not-ours"
NOW = utc(2026, 8, 26, 21, 0)
ALERT = AlertId("alert-1")
MAYA = PersonId("person-maya")


def _reencode(payload: dict[str, object]) -> str:
    """Re-encode an edited payload, so a test can forge exactly one field."""
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(body).rstrip(b"=").decode()


def a_token(**overrides: object) -> str:
    params: dict[str, object] = {
        "alert_id": ALERT,
        "responder_id": MAYA,
        "nonce": "nonce-1",
        "key": KEY,
        "now": NOW,
    }
    params.update(overrides)
    return issue(**params)  # type: ignore[arg-type]


def test_a_token_round_trips() -> None:
    claims = verify(a_token(), key=KEY, now=NOW)

    assert claims.alert_id == ALERT
    assert claims.responder_id == MAYA
    assert claims.nonce == "nonce-1"
    assert claims.permissions == RESPONDER_PERMISSIONS


# -- forgery ------------------------------------------------------------------


def test_a_token_signed_with_another_key_is_refused() -> None:
    forged = a_token(key=OTHER_KEY)
    with pytest.raises(TokenError):
        verify(forged, key=KEY, now=NOW)


def test_editing_the_payload_invalidates_the_signature() -> None:
    """The attack that matters: point a valid link at somebody else's Alert."""
    body, signature = a_token().split(".")
    payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    payload["a"] = "alert-somebody-else"
    tampered_body = _reencode(payload)

    with pytest.raises(TokenError):
        verify(f"{tampered_body}.{signature}", key=KEY, now=NOW)


def test_escalating_permissions_invalidates_the_signature() -> None:
    body, signature = a_token(permissions=frozenset({ResponderPermission.VIEW_ALERT})).split(".")
    payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    payload["p"] = sorted(p.value for p in RESPONDER_PERMISSIONS)
    tampered = _reencode(payload)

    with pytest.raises(TokenError):
        verify(f"{tampered}.{signature}", key=KEY, now=NOW)


def test_extending_the_expiry_invalidates_the_signature() -> None:
    body, signature = a_token().split(".")
    payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    payload["e"] = payload["e"] + 86_400 * 365
    tampered = _reencode(payload)

    with pytest.raises(TokenError):
        verify(f"{tampered}.{signature}", key=KEY, now=NOW)


@pytest.mark.parametrize(
    "garbage",
    ["", ".", "not-a-token", "a.b.c", "!!!.???", "eyJhIjoiMSJ9"],
)
def test_malformed_tokens_are_refused_rather_than_crashing(garbage: str) -> None:
    with pytest.raises(TokenError):
        verify(garbage, key=KEY, now=NOW)


# -- expiry -------------------------------------------------------------------


def test_a_token_expires() -> None:
    token = a_token(lifetime=timedelta(hours=1))
    verify(token, key=KEY, now=NOW + timedelta(minutes=59))

    with pytest.raises(TokenError):
        verify(token, key=KEY, now=NOW + timedelta(hours=1, seconds=1))


def test_a_link_found_a_week_later_is_inert() -> None:
    token = a_token()
    with pytest.raises(TokenError):
        verify(token, key=KEY, now=NOW + timedelta(days=7))


# -- scope --------------------------------------------------------------------


def test_a_token_names_exactly_one_alert() -> None:
    """A leaked link exposes one incident, never a session."""
    claims = verify(a_token(), key=KEY, now=NOW)
    assert claims.alert_id == ALERT
    assert isinstance(claims.alert_id, str)


def test_permissions_can_be_narrowed_at_issue_time() -> None:
    token = a_token(permissions=frozenset({ResponderPermission.VIEW_ALERT}))
    claims = verify(token, key=KEY, now=NOW)

    assert claims.allows(ResponderPermission.VIEW_ALERT)
    assert not claims.allows(ResponderPermission.RESOLVE)
    assert not claims.allows(ResponderPermission.CLAIM)


def test_the_permission_set_grants_nothing_beyond_one_alert() -> None:
    """A responder needs to know somebody has not checked in, not the shape of their life."""
    names = {p.value for p in RESPONDER_PERMISSIONS}
    for forbidden in ("VIEW_PLAN", "VIEW_CIRCLE", "VIEW_HISTORY", "MODIFY_PLAN", "VIEW_LOCATION"):
        assert forbidden not in names


# -- what the token carries ---------------------------------------------------


def test_the_payload_carries_only_opaque_identifiers() -> None:
    """Tokens travel by SMS and sit in message history and server logs.

    The payload names ids and nothing else. Anything human — a name, an email, a phone
    number — would be readable by everyone who ever saw the link, including whoever picks
    up an unlocked phone.

    This guarantee has a dependency worth stating: it holds only while person ids are
    *opaque*. Production ids come from ``uuid_factory``, so this uses one rather than the
    readable ids the other tests use for legibility.
    """
    opaque = PersonId("8f14e45f-ceea-467a-9a1c-4b1c2d5e6f70")
    body = a_token(responder_id=opaque).split(".")[0]
    payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))

    serialised = json.dumps(payload).lower()
    for leak in ("phone", "+1", "+44", "email", "@", "name", "display"):
        assert leak not in serialised, f"token payload leaks {leak!r}: {serialised}"


def test_the_payload_has_no_descriptive_fields_at_all() -> None:
    """Keys are single letters.

    Not for compactness — it is a standing check that nobody has added a convenient
    ``planLabel`` or ``subjectName`` to save a lookup. Every human-readable value is
    fetched server-side, after the token has been validated.
    """
    body = a_token().split(".")[0]
    payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))

    unexpected = [key for key in payload if len(key) > 1]
    assert not unexpected, f"token gained descriptive fields: {unexpected}"


def test_the_error_never_says_which_check_failed() -> None:
    """Distinguishing 'expired' from 'forged' tells an attacker which half of a guess was right."""
    expired = a_token(lifetime=timedelta(seconds=1))
    forged = a_token(key=OTHER_KEY)

    messages = set()
    for token in (expired, forged, "garbage"):
        with pytest.raises(TokenError) as caught:
            verify(token, key=KEY, now=NOW + timedelta(hours=1))
        messages.add(str(caught.value))

    assert len(messages) == 1, f"error messages differ and leak the cause: {messages}"


# -- the key itself -----------------------------------------------------------


def test_an_empty_signing_key_cannot_issue_a_token() -> None:
    """HMAC accepts an empty key and produces a valid-looking signature with it.

    Everything would appear to work — tokens would issue, tokens would verify — and every
    link would be forgeable by anyone who knew the scheme. This was a real gap: the key was
    never loaded from Secrets Manager and defaulted to b"".
    """
    with pytest.raises(TokenError):
        issue(
            alert_id=ALERT,
            responder_id=MAYA,
            nonce="n",
            key=b"",
            now=NOW,
        )


def test_an_empty_signing_key_cannot_verify_a_token() -> None:
    with pytest.raises(TokenError):
        verify(a_token(), key=b"", now=NOW)


def test_a_short_signing_key_is_refused() -> None:
    """32 bytes is the floor. A short key is brute-forceable offline from one link."""
    with pytest.raises(TokenError):
        issue(alert_id=ALERT, responder_id=MAYA, nonce="n", key=b"short", now=NOW)


def test_the_reason_is_still_available_for_the_audit_trail() -> None:
    with pytest.raises(TokenError) as caught:
        verify(a_token(key=OTHER_KEY), key=KEY, now=NOW)
    assert caught.value.reason == "bad_signature"
