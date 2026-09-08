from services.adapters.contact import DeliveryStatus, SafeDemoSender
from services.domain.ids import AlertId
from services.domain.plan import Channel


def test_safe_demo_sink_accepts_supported_channels_without_an_endpoint() -> None:
    result = SafeDemoSender().send(
        alert_id=AlertId("alert-demo"),
        member=None,
        channel=Channel.PUSH,
        body="private text that must not be persisted by the sink",
        link=None,
    )

    assert result.status is DeliveryStatus.ACCEPTED
    assert result.provider_reference == "safe-sink:alert-demo:PUSH"


def test_safe_demo_sink_does_not_claim_voice_support() -> None:
    result = SafeDemoSender().send(
        alert_id=AlertId("alert-demo"),
        member=None,
        channel=Channel.CALL,
        body="ignored",
        link=None,
    )

    assert result.status is DeliveryStatus.CHANNEL_UNAVAILABLE
