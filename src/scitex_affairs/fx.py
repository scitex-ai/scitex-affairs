"""Live exchange rates for prices denominated in another currency.

A price may be set in one currency (for example USD, the SciTeX price list)
while plans and accounts are kept in another (for example JPY). Converting
between them needs a rate, and a stale or invented rate silently misstates
every derived figure. So the rate is always **fetched from a declared
reference source**, recorded with its source and timestamps on every
converted figure, and a failure to fetch is an error, never a fallback.

The converted figure is an **estimate**. Actual billing happens in the price's
own currency; what a customer is charged in another currency is set by their
card issuer's rate and fees at settlement. :func:`disclosure` renders that
statement so every output that shows a converted figure can carry it.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from .config import ConfigError

#: Reference sources: id -> (display name, URL template taking the base code).
#: ExchangeRate-API is the source SciTeX Hub uses for its yen reference column,
#: so a figure computed here and one shown on scitex.ai agree on method.
PROVIDERS: dict[str, tuple[str, str]] = {
    "open.er-api.com": (
        "ExchangeRate-API (open.er-api.com)",
        "https://open.er-api.com/v6/latest/{base}",
    ),
}

#: ``opener(url, timeout_seconds) -> response body bytes``. Injectable so tests
#: can serve a real JSON body without patching this module.
Opener = Callable[[str, float], bytes]


class FxError(ConfigError):
    """A rate could not be obtained or the supplier's answer was unusable."""


@dataclass(frozen=True, slots=True)
class FxRate:
    """One ``base -> quote`` rate with everything needed to disclose it."""

    base: str
    quote: str
    rate: float
    as_of: str  # the supplier's own last-update timestamp
    source: str  # provider id, e.g. "open.er-api.com"
    retrieved_at: str  # when this process fetched it (UTC, ISO 8601)

    @property
    def source_label(self) -> str:
        return PROVIDERS.get(self.source, (self.source, ""))[0]


def _urlopen(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "scitex-affairs"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read()


def fetch_rate(
    base: str,
    quote: str,
    provider: str = "open.er-api.com",
    *,
    opener: Opener = _urlopen,
    timeout: float = 10.0,
) -> FxRate:
    """Fetch the current ``base -> quote`` rate from a declared provider.

    Raises :class:`FxError` when the provider is unknown, unreachable, or
    answers with anything but a positive rate for ``quote``.
    """

    base, quote = base.upper(), quote.upper()
    if provider not in PROVIDERS:
        raise FxError(f"unknown fx provider {provider!r}; known: {sorted(PROVIDERS)}")
    url = PROVIDERS[provider][1].format(base=base)
    try:
        payload = json.loads(opener(url, timeout))
    except Exception as exc:  # noqa: BLE001 — every failure is reported, not hidden
        raise FxError(f"cannot fetch {base}->{quote} from {provider}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("result") != "success":
        raise FxError(f"{provider} did not return a successful result for {base}")
    rate = payload.get("rates", {}).get(quote)
    if not isinstance(rate, (int, float)) or isinstance(rate, bool) or rate <= 0:
        raise FxError(f"{provider} returned no positive {base}->{quote} rate")
    return FxRate(
        base=base,
        quote=quote,
        rate=float(rate),
        as_of=str(payload.get("time_last_update_utc", "")),
        source=provider,
        retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def disclosure(rate: FxRate, language: str = "en") -> str:
    """State how a converted figure was obtained and that billing differs."""

    if language == "ja":
        return (
            f"{rate.quote}換算額は、{rate.source_label} が公開する為替レート "
            f"1 {rate.base} = {rate.rate:,.4g} {rate.quote}（{rate.as_of} 時点。"
            f"{rate.retrieved_at} に取得）で求めた概算です。あくまで目安であり、"
            f"実際の請求は{rate.base}で行われます。{rate.quote}での請求額は、"
            "カード会社等が決済時に適用する為替レートや手数料によって異なります。"
        )
    return (
        f"{rate.quote} figures are estimates converted at the rate published by "
        f"{rate.source_label}: 1 {rate.base} = {rate.rate:,.4g} {rate.quote} "
        f"(as of {rate.as_of}; retrieved {rate.retrieved_at}). They are a guide "
        f"only. Actual billing is in {rate.base}; an amount charged in "
        f"{rate.quote} is set by the card issuer's exchange rate and fees at "
        "settlement and will differ."
    )
