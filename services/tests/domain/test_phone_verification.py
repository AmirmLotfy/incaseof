from __future__ import annotations

import pytest

from services.domain.account import SupportedCountry
from services.domain.errors import DomainError
from services.domain.phone_verification import validate_phone_for_country

EG_TEST_NUMBER = "+20" + "10" + "00000000"


@pytest.mark.parametrize(
    ("number", "country"),
    [
        (EG_TEST_NUMBER, SupportedCountry.EGYPT),
        ("+20" + "15" + "00000000", SupportedCountry.EGYPT),
        ("+12025550123", SupportedCountry.UNITED_STATES),
    ],
)
def test_launch_market_phone_numbers_use_strict_e164(
    number: str, country: SupportedCountry
) -> None:
    assert validate_phone_for_country(number, country) == number


@pytest.mark.parametrize(
    ("number", "country"),
    [
        ("01012345678", SupportedCountry.EGYPT),
        (EG_TEST_NUMBER, SupportedCountry.UNITED_STATES),
        ("+12025550123", SupportedCountry.EGYPT),
        ("+10115550123", SupportedCountry.UNITED_STATES),
        (" +12025550123", SupportedCountry.UNITED_STATES),
    ],
)
def test_phone_number_must_match_the_profile_country(
    number: str, country: SupportedCountry
) -> None:
    with pytest.raises(DomainError):
        validate_phone_for_country(number, country)
