from datetime import timedelta

import pytest

from services.domain.clock import utc
from services.domain.demo_token import issue, verify
from services.domain.ids import PersonId
from services.domain.responder_token import TokenError

NOW = utc(2026, 9, 4, 12, 0)
KEY = b"demo-token-test-key-at-least-32-bytes"


def test_demo_session_is_scoped_and_expires() -> None:
    token = issue(PersonId("demo-session-1"), key=KEY, now=NOW, lifetime=timedelta(minutes=5))
    claims = verify(token, key=KEY, now=NOW + timedelta(minutes=4))
    assert claims.person_id == "demo-session-1"
    with pytest.raises(TokenError):
        verify(token, key=KEY, now=NOW + timedelta(minutes=5))


def test_demo_token_rejects_other_audiences_and_tampering() -> None:
    with pytest.raises(TokenError):
        issue(PersonId("person-real"), key=KEY, now=NOW)
    token = issue(PersonId("demo-session-1"), key=KEY, now=NOW)
    with pytest.raises(TokenError):
        verify(token[:-1] + ("A" if token[-1] != "A" else "B"), key=KEY, now=NOW)
