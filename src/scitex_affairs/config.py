"""Resolve, load, and validate the reviewable business design document."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from scitex_config._ecosystem import local_state

CONFIG_ENV = "SCITEX_AFFAIRS_CONFIG"
PACKAGE_SHORT = "affairs"
CONFIG_NAME = "config.yaml"

_DIRECTIONS = {"revenue", "expense"}
_MODELS = {"recurring", "one_time", "usage"}
_INTERVALS = {"month", "year", "day", "hour", "unit", "case", "usage"}
_PRICE_KINDS = {"fixed", "tbd", "cost_plus", "included", "free"}
_DISCOUNT_STATUSES = {"active", "proposed", "retired"}
_MEASURES = {"stock", "flow"}


class ConfigError(ValueError):
    """The business design document is inconsistent or incomplete."""


@dataclass(frozen=True, slots=True)
class DiscountPhase:
    """A dated discount phase shared through a pricing policy."""

    start: date
    end: date
    percent: float
    status: str
    label: str = ""

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end


@dataclass(frozen=True, slots=True)
class Price:
    """A catalog price in the configuration's currency."""

    amount: float | None
    interval: str
    unit: str
    kind: str = "fixed"
    list_amount: float | None = None
    discount_percent: float = 0.0
    markup_percent: float | None = None
    policy: str = ""
    discount_schedule: tuple[DiscountPhase, ...] = ()
    #: Currency the price is denominated in; "" means the config's currency.
    currency: str = ""

    @classmethod
    def from_mapping(
        cls,
        raw: Mapping[str, Any],
        where: str,
        policies: Mapping[str, Mapping[str, Any]],
    ) -> Price:
        policy = str(raw.get("policy", "")).strip()
        if policy and policy not in policies:
            raise ConfigError(f"{where}.policy is not defined: {policy}")
        merged = dict(policies.get(policy, {}))
        merged.update(raw)
        kind = _choice(merged.get("kind", "fixed"), _PRICE_KINDS, f"{where}.kind")
        interval = _choice(merged.get("interval"), _INTERVALS, f"{where}.interval")
        unit = _text(merged.get("unit"), f"{where}.unit")
        amount = _optional_number(merged.get("amount"), f"{where}.amount")
        list_amount = _optional_number(
            merged.get("list_amount"), f"{where}.list_amount"
        )
        schedule = _discount_schedule(
            merged.get("discount_schedule", []), f"{where}.discount_schedule"
        )
        discount = _optional_number(
            merged.get("discount_percent"), f"{where}.discount_percent"
        )
        if discount is None:
            active = [phase for phase in schedule if phase.status == "active"]
            discount = active[0].percent if active else 0.0
        discount = 0.0 if discount is None else discount
        markup = _optional_number(
            merged.get("markup_percent"), f"{where}.markup_percent"
        )
        if not 0 <= discount <= 100:
            raise ConfigError(f"{where}.discount_percent must be between 0 and 100")
        if amount is None and list_amount is not None:
            amount = list_amount * (1 - discount / 100)
        if kind == "fixed" and amount is None:
            raise ConfigError(f"{where}: fixed pricing requires amount or list_amount")
        if kind in {"free", "included"}:
            amount = 0.0
        if kind in {"tbd", "cost_plus"} and amount is not None:
            raise ConfigError(f"{where}: {kind} pricing must not declare amount")
        if kind == "cost_plus" and markup is None:
            raise ConfigError(f"{where}: cost_plus pricing requires markup_percent")
        if any(
            value is not None and value < 0 for value in (amount, list_amount, markup)
        ):
            raise ConfigError(
                f"{where} monetary values and markup must be non-negative"
            )
        return cls(
            amount=amount,
            interval=interval,
            unit=unit,
            kind=kind,
            list_amount=list_amount,
            discount_percent=discount,
            markup_percent=markup,
            policy=policy,
            discount_schedule=schedule,
            currency=str(merged.get("currency", "")).strip().upper(),
        )

    def amount_on(self, day: date) -> float | None:
        """Return the dated sell price, including proposed scenario phases."""

        if self.list_amount is not None and self.discount_schedule:
            for phase in self.discount_schedule:
                if phase.contains(day):
                    return self.list_amount * (1 - phase.percent / 100)
            return self.list_amount
        return self.amount


@dataclass(frozen=True, slots=True)
class CatalogItem:
    """One revenue or expense item."""

    id: str
    name: str
    direction: str
    model: str
    price: Price
    description: str = ""
    category: str = ""
    status: str = "draft"
    automated: bool | None = None
    attributes: Mapping[str, Any] | None = None

    @classmethod
    def from_mapping(
        cls,
        raw: Mapping[str, Any],
        index: int,
        policies: Mapping[str, Mapping[str, Any]],
    ) -> CatalogItem:
        where = f"catalog[{index}]"
        price_raw = raw.get("price")
        if not isinstance(price_raw, Mapping):
            raise ConfigError(f"{where}.price must be a mapping")
        item = cls(
            id=_text(raw.get("id"), f"{where}.id"),
            name=_text(raw.get("name"), f"{where}.name"),
            direction=_choice(raw.get("direction"), _DIRECTIONS, f"{where}.direction"),
            model=_choice(raw.get("model"), _MODELS, f"{where}.model"),
            price=Price.from_mapping(price_raw, f"{where}.price", policies),
            description=str(raw.get("description", "")).strip(),
            category=str(raw.get("category", "")).strip(),
            status=str(raw.get("status", "draft")).strip() or "draft",
            automated=_optional_bool(raw.get("automated"), f"{where}.automated"),
            attributes=_optional_mapping(raw.get("attributes"), f"{where}.attributes"),
        )
        if item.model == "recurring" and item.price.interval not in {"month", "year"}:
            raise ConfigError(
                f"{where}: recurring items require a month or year price interval"
            )
        return item


@dataclass(frozen=True, slots=True)
class Scenario:
    """An explicitly optional set of hypothetical time series."""

    id: str
    label: str
    status: str
    start_date: date
    end_date: date
    series: tuple[Mapping[str, Any], ...]

    @classmethod
    def from_mapping(
        cls,
        scenario_id: str,
        raw: Mapping[str, Any],
        catalog: Mapping[str, CatalogItem],
    ) -> Scenario:
        where = f"scenarios.{scenario_id}"
        start = _date(raw.get("start_date"), f"{where}.start_date")
        end = _date(raw.get("end_date"), f"{where}.end_date")
        if end < start:
            raise ConfigError(f"{where}.end_date must not precede start_date")
        raw_series = raw.get("series", [])
        if not isinstance(raw_series, list):
            raise ConfigError(f"{where}.series must be a list")
        series: list[Mapping[str, Any]] = []
        for index, entry in enumerate(raw_series):
            series_where = f"{where}.series[{index}]"
            if not isinstance(entry, Mapping):
                raise ConfigError(f"{series_where} must be a mapping")
            item_id = _text(entry.get("item_id"), f"{series_where}.item_id")
            if item_id not in catalog:
                raise ConfigError(
                    f"{series_where}.item_id is not in catalog: {item_id}"
                )
            measure = _choice(
                entry.get("measure"), _MEASURES, f"{series_where}.measure"
            )
            item = catalog[item_id]
            if measure == "stock":
                _validate_stock(entry, series_where, item, start, end)
            else:
                _validate_flow(entry, series_where, item, start, end)
            series.append(dict(entry))
        return cls(
            id=scenario_id,
            label=str(raw.get("label", scenario_id)).strip() or scenario_id,
            status=str(raw.get("status", "exploratory")).strip() or "exploratory",
            start_date=start,
            end_date=end,
            series=tuple(series),
        )


@dataclass(frozen=True, slots=True)
class AffairsConfig:
    """Validated single source of truth for business design facts."""

    schema_version: int
    organization: str
    currency: str
    fiscal_year_start_month: int
    catalog: Mapping[str, CatalogItem]
    scenarios: Mapping[str, Scenario]
    pricing_policies: Mapping[str, Mapping[str, Any]]
    sources: tuple[Mapping[str, Any], ...] = ()
    #: Live-rate source for prices in another currency, e.g. {"provider": ...}.
    fx: Mapping[str, Any] | None = None

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> AffairsConfig:
        version = raw.get("schema_version")
        if version != 1:
            raise ConfigError(f"schema_version must be 1, got {version!r}")
        policies = _pricing_policies(raw.get("pricing_policies", {}))
        raw_catalog = raw.get("catalog", [])
        if not isinstance(raw_catalog, list):
            raise ConfigError("catalog must be a list")
        catalog_items = [
            CatalogItem.from_mapping(item, i, policies)
            for i, item in enumerate(raw_catalog)
        ]
        catalog = {item.id: item for item in catalog_items}
        if len(catalog) != len(catalog_items):
            raise ConfigError("catalog item ids must be unique")
        month = raw.get("fiscal_year_start_month", 1)
        if (
            not isinstance(month, int)
            or isinstance(month, bool)
            or not 1 <= month <= 12
        ):
            raise ConfigError("fiscal_year_start_month must be an integer from 1 to 12")
        raw_scenarios = raw.get("scenarios", {})
        if not isinstance(raw_scenarios, Mapping):
            raise ConfigError("scenarios must be a mapping")
        scenarios = {
            str(key): Scenario.from_mapping(str(key), value, catalog)
            for key, value in raw_scenarios.items()
        }
        currency = _text(raw.get("currency"), "currency").upper()
        fx = _optional_mapping(raw.get("fx"), "fx")
        foreign = sorted({i.price.currency for i in catalog_items} - {"", currency})
        if foreign and not (fx and str(fx.get("provider", "")).strip()):
            raise ConfigError(
                f"prices in {foreign} need fx.provider to convert to {currency}"
            )
        return cls(
            schema_version=version,
            organization=_text(raw.get("organization"), "organization"),
            currency=currency,
            fx=fx,
            fiscal_year_start_month=month,
            catalog=catalog,
            scenarios=scenarios,
            pricing_policies=policies,
            sources=_sources(raw.get("sources", [])),
        )


def resolve_config_path(source: str | Path | None = None) -> Path:
    """Resolve explicit, environment, then canonical SciTeX config paths."""

    if source is not None:
        return Path(source).expanduser()
    configured = os.environ.get(CONFIG_ENV)
    if configured:
        return Path(configured).expanduser()
    return local_state.path(PACKAGE_SHORT, CONFIG_NAME)


def load_config(
    source: str | Path | Mapping[str, Any] | None = None,
) -> AffairsConfig:
    """Load a mapping or resolved YAML config.

    Path precedence is explicit argument, ``SCITEX_AFFAIRS_CONFIG``, then
    ``$SCITEX_DIR/affairs/config.yaml`` (normally
    ``~/.scitex/affairs/config.yaml``). Project-scope resolution is provided
    by the ecosystem-wide :mod:`scitex_config` local-state primitive.
    """

    if isinstance(source, Mapping):
        raw = source
    else:
        path = resolve_config_path(source)
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigError(f"cannot load {path}: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise ConfigError("configuration root must be a mapping")
    return AffairsConfig.from_mapping(raw)


def _validate_stock(
    raw: Mapping[str, Any],
    where: str,
    item: CatalogItem,
    start: date,
    end: date,
) -> None:
    if item.model != "recurring":
        raise ConfigError(f"{where}: stock measure requires a recurring catalog item")
    if item.price.amount is None:
        raise ConfigError(f"{where}: scenario items require a numeric price")
    interpolation = raw.get("interpolation", "linear")
    if interpolation not in {"linear", "step"}:
        raise ConfigError(f"{where}.interpolation must be linear or step")
    points = raw.get("points")
    if not isinstance(points, list) or not points:
        raise ConfigError(f"{where}.points must be a non-empty list")
    dates: list[date] = []
    for index, point in enumerate(points):
        if not isinstance(point, Mapping):
            raise ConfigError(f"{where}.points[{index}] must be a mapping")
        point_date = _date(point.get("date"), f"{where}.points[{index}].date")
        value = _number(point.get("value"), f"{where}.points[{index}].value")
        if value < 0:
            raise ConfigError(f"{where}.points[{index}].value must be non-negative")
        if not start <= point_date <= end:
            raise ConfigError(f"{where}.points[{index}].date is outside the scenario")
        dates.append(point_date)
    if dates != sorted(dates) or len(dates) != len(set(dates)):
        raise ConfigError(f"{where}.points dates must be unique and increasing")


def _validate_flow(
    raw: Mapping[str, Any],
    where: str,
    item: CatalogItem,
    start: date,
    end: date,
) -> None:
    if item.model == "recurring":
        raise ConfigError(f"{where}: flow measure cannot use a recurring catalog item")
    if item.price.amount is None:
        raise ConfigError(f"{where}: scenario items require a numeric price")
    periods = raw.get("periods")
    if not isinstance(periods, list) or not periods:
        raise ConfigError(f"{where}.periods must be a non-empty list")
    for index, period in enumerate(periods):
        if not isinstance(period, Mapping):
            raise ConfigError(f"{where}.periods[{index}] must be a mapping")
        period_start = _date(period.get("start"), f"{where}.periods[{index}].start")
        period_end = _date(period.get("end"), f"{where}.periods[{index}].end")
        value = _number(period.get("value"), f"{where}.periods[{index}].value")
        if period_end < period_start:
            raise ConfigError(f"{where}.periods[{index}] has end before start")
        if period_start < start or period_end > end:
            raise ConfigError(f"{where}.periods[{index}] is outside the scenario")
        if value < 0:
            raise ConfigError(f"{where}.periods[{index}].value must be non-negative")


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{where} must be a non-empty string")
    return value.strip()


def _choice(value: Any, choices: set[str], where: str) -> str:
    text = _text(value, where)
    if text not in choices:
        raise ConfigError(f"{where} must be one of {sorted(choices)}, got {text!r}")
    return text


def _number(value: Any, where: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ConfigError(f"{where} must be a number")
    return float(value)


def _optional_number(value: Any, where: str) -> float | None:
    if value is None:
        return None
    return _number(value, where)


def _optional_bool(value: Any, where: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ConfigError(f"{where} must be true or false")
    return value


def _optional_mapping(value: Any, where: str) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ConfigError(f"{where} must be a mapping")
    return dict(value)


def _sources(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, list):
        raise ConfigError("sources must be a list")
    if not all(isinstance(item, Mapping) for item in value):
        raise ConfigError("each source must be a mapping")
    return tuple(dict(item) for item in value)


def _pricing_policies(value: Any) -> Mapping[str, Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        raise ConfigError("pricing_policies must be a mapping")
    if not all(isinstance(item, Mapping) for item in value.values()):
        raise ConfigError("each pricing policy must be a mapping")
    return {str(key): dict(item) for key, item in value.items()}


def _discount_schedule(value: Any, where: str) -> tuple[DiscountPhase, ...]:
    if not isinstance(value, list):
        raise ConfigError(f"{where} must be a list")
    phases = []
    for index, raw in enumerate(value):
        phase_where = f"{where}[{index}]"
        if not isinstance(raw, Mapping):
            raise ConfigError(f"{phase_where} must be a mapping")
        percent = _number(raw.get("percent"), f"{phase_where}.percent")
        if not 0 <= percent <= 100:
            raise ConfigError(f"{phase_where}.percent must be between 0 and 100")
        phase = DiscountPhase(
            start=_date(raw.get("start"), f"{phase_where}.start"),
            end=_date(raw.get("end"), f"{phase_where}.end"),
            percent=percent,
            status=_choice(
                raw.get("status"), _DISCOUNT_STATUSES, f"{phase_where}.status"
            ),
            label=str(raw.get("label", "")).strip(),
        )
        if phase.end < phase.start:
            raise ConfigError(f"{phase_where}.end must not precede start")
        if phases and phase.start <= phases[-1].end:
            raise ConfigError(f"{where} phases must be ordered and non-overlapping")
        phases.append(phase)
    active_count = sum(phase.status == "active" for phase in phases)
    if active_count > 1:
        raise ConfigError(f"{where} must not contain multiple active phases")
    return tuple(phases)


def _date(value: Any, where: str) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ConfigError(f"{where} must be an ISO date") from exc
    raise ConfigError(f"{where} must be an ISO date")
