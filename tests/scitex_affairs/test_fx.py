"""Live exchange rates: fetching, failing loudly, converting, disclosing."""

from __future__ import annotations

import json

import pytest

from scitex_affairs import ConfigError, load_config, monthly_report
from scitex_affairs.fx import FxError, FxRate, disclosure, fetch_rate

#: A body in the exact shape open.er-api.com returns (trimmed to two rates).
_ER_API_BODY = json.dumps(
    {
        "result": "success",
        "provider": "https://www.exchangerate-api.com",
        "time_last_update_utc": "Mon, 16 Nov 2026 00:02:31 +0000",
        "base_code": "USD",
        "rates": {"USD": 1, "JPY": 159.784314},
    }
).encode()


def _serve(body: bytes):
    """A real opener that returns ``body`` and records the URL it was asked for."""
    asked: list[str] = []

    def opener(url: str, timeout: float) -> bytes:
        asked.append(url)
        return body

    opener.asked = asked  # type: ignore[attr-defined]
    return opener


def _usd_priced_config(*, with_fx: bool = True) -> dict:
    raw = {
        "schema_version": 1,
        "organization": "Example Co",
        "currency": "JPY",
        "catalog": [
            {
                "id": "pro",
                "name": "Pro",
                "direction": "revenue",
                "model": "recurring",
                "price": {
                    "kind": "fixed",
                    "amount": 39,
                    "currency": "USD",
                    "interval": "month",
                    "unit": "person",
                },
            }
        ],
        "scenarios": {
            "one": {
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "series": [
                    {
                        "item_id": "pro",
                        "measure": "stock",
                        "interpolation": "step",
                        "points": [{"date": "2026-01-01", "value": 10}],
                    }
                ],
            }
        },
    }
    if with_fx:
        raw["fx"] = {"provider": "open.er-api.com"}
    return raw


def _raised(call) -> BaseException | None:
    """Run ``call`` and return what it raised (``None`` if it returned)."""
    try:
        call()
    except BaseException as exc:  # noqa: BLE001 — the test inspects it
        return exc
    return None


def _rate() -> FxRate:
    return fetch_rate("USD", "JPY", opener=_serve(_ER_API_BODY))


def test_fetch_rate_reads_the_quote_from_the_provider_body():
    # Arrange
    opener = _serve(_ER_API_BODY)
    # Act
    rate = fetch_rate("usd", "jpy", opener=opener)
    # Assert
    assert (rate.base, rate.quote, rate.rate, rate.source, opener.asked) == (
        "USD",
        "JPY",
        159.784314,
        "open.er-api.com",
        ["https://open.er-api.com/v6/latest/USD"],
    )


def test_fetch_rate_raises_when_the_provider_is_unreachable():
    # Arrange
    def unreachable(url: str, timeout: float) -> bytes:
        raise OSError("network is unreachable")

    # Act
    error = _raised(lambda: fetch_rate("USD", "JPY", opener=unreachable))
    # Assert
    assert isinstance(error, FxError) and "cannot fetch USD->JPY" in str(error)


def test_fetch_rate_raises_when_the_quote_is_missing():
    # Arrange
    body = json.dumps({"result": "success", "rates": {"USD": 1}}).encode()
    # Act
    error = _raised(lambda: fetch_rate("USD", "JPY", opener=_serve(body)))
    # Assert
    assert isinstance(error, FxError) and "no positive USD->JPY rate" in str(error)


def test_foreign_price_without_fx_provider_is_a_config_error():
    # Arrange
    raw = _usd_priced_config(with_fx=False)
    # Act
    error = _raised(lambda: load_config(raw))
    # Assert
    assert isinstance(error, ConfigError) and "need fx.provider" in str(error)


def test_monthly_report_converts_a_usd_price_into_the_base_currency():
    # Arrange — 10 subscribers x $39 x the fetched rate, for one full month
    config = load_config(_usd_priced_config())
    rate = _rate()
    # Act
    report = monthly_report(config, "one", rates={"USD": rate})
    # Assert
    assert report.loc[0, "amount"] == pytest.approx(10 * 39 * 159.784314)


def test_monthly_report_records_the_rate_on_each_converted_row():
    # Arrange
    config = load_config(_usd_priced_config())
    rate = _rate()
    # Act
    report = monthly_report(config, "one", rates={"USD": rate})
    # Assert
    assert report.loc[
        0, ["currency", "price_currency", "fx_rate", "fx_as_of", "fx_source"]
    ].tolist() == [
        "JPY",
        "USD",
        159.784314,
        "Mon, 16 Nov 2026 00:02:31 +0000",
        "open.er-api.com",
    ]


def test_monthly_report_lists_the_rates_used_for_disclosure():
    # Arrange
    config = load_config(_usd_priced_config())
    rate = _rate()
    # Act
    report = monthly_report(config, "one", rates={"USD": rate})
    # Assert
    assert report.attrs["fx"] == [rate]


@pytest.mark.parametrize(
    ("language", "phrases"),
    [
        (
            "en",
            (
                "ExchangeRate-API (open.er-api.com)",
                "estimates",
                "Actual billing is in USD",
                "card issuer's exchange rate and fees",
            ),
        ),
        (
            "ja",
            (
                "ExchangeRate-API (open.er-api.com)",
                "概算",
                "あくまで目安",
                "実際の請求はUSDで行われます",
                "カード会社等が決済時に適用する為替レートや手数料",
            ),
        ),
    ],
)
def test_disclosure_states_source_estimate_and_billing(language, phrases):
    # Arrange
    rate = _rate()
    # Act
    text = disclosure(rate, language)
    # Assert
    assert [p for p in phrases if p not in text] == []
