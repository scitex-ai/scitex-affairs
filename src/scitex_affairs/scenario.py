"""Scenario calculation with explicit stock/flow time semantics."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

import pandas as pd

from .config import AffairsConfig, CatalogItem, ConfigError, Scenario

REPORT_COLUMNS = [
    "scenario_id",
    "scenario_status",
    "period_start",
    "period_end",
    "days",
    "item_id",
    "item_name",
    "direction",
    "model",
    "measure",
    "currency",
    "opening_units",
    "closing_units",
    "average_units",
    "units_flow",
    "amount",
    "signed_amount",
]


def monthly_report(config: AffairsConfig, scenario_id: str) -> pd.DataFrame:
    """Calculate the canonical monthly ledger for one optional scenario."""

    try:
        scenario = config.scenarios[scenario_id]
    except KeyError as exc:
        raise ConfigError(f"unknown scenario: {scenario_id}") from exc

    frames: list[pd.DataFrame] = []
    for series in scenario.series:
        item = config.catalog[str(series["item_id"])]
        if series["measure"] == "stock":
            frame = _stock_months(scenario, item, series, config.currency)
        else:
            frame = _flow_months(scenario, item, series, config.currency)
        frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=REPORT_COLUMNS)
    report = pd.concat(frames, ignore_index=True)[REPORT_COLUMNS]
    return report.sort_values(["period_start", "item_id"]).reset_index(drop=True)


def _stock_months(
    scenario: Scenario,
    item: CatalogItem,
    series: Mapping[str, Any],
    currency: str,
) -> pd.DataFrame:
    daily_index = pd.date_range(scenario.start_date, scenario.end_date, freq="D")
    point_values = {
        pd.Timestamp(point["date"]): float(point["value"]) for point in series["points"]
    }
    values = pd.Series(index=daily_index, dtype=float)
    for timestamp, value in point_values.items():
        values.loc[timestamp] = value
    if series.get("interpolation", "linear") == "step":
        values = values.ffill().bfill()
    else:
        values = values.interpolate(method="time").ffill().bfill()

    daily = pd.DataFrame({"date": daily_index, "units": values.to_numpy()})
    daily["month"] = daily["date"].dt.to_period("M")
    rows = []
    for _, group in daily.groupby("month", sort=True):
        average = float(group["units"].mean())
        dated_price = item.price.amount_on(group["date"].iloc[0].date())
        assert dated_price is not None
        monthly_price = (
            dated_price if item.price.interval == "month" else dated_price / 12
        )
        rows.append(
            _row(
                scenario,
                item,
                currency,
                period_start=group["date"].iloc[0].date(),
                period_end=group["date"].iloc[-1].date(),
                days=len(group),
                measure="stock",
                opening_units=float(group["units"].iloc[0]),
                closing_units=float(group["units"].iloc[-1]),
                average_units=average,
                units_flow=0.0,
                amount=average * monthly_price,
            )
        )
    return pd.DataFrame(rows)


def _flow_months(
    scenario: Scenario,
    item: CatalogItem,
    series: Mapping[str, Any],
    currency: str,
) -> pd.DataFrame:
    month_starts = pd.date_range(
        pd.Timestamp(scenario.start_date).to_period("M").start_time,
        pd.Timestamp(scenario.end_date).to_period("M").start_time,
        freq="MS",
    )
    allocated = {month.date(): 0.0 for month in month_starts}
    for period in series["periods"]:
        start = _as_date(period["start"])
        end = _as_date(period["end"])
        total_days = (end - start).days + 1
        for month in month_starts:
            month_start = max(month.date(), scenario.start_date)
            month_end = min((month + pd.offsets.MonthEnd(0)).date(), scenario.end_date)
            overlap_start = max(start, month_start)
            overlap_end = min(end, month_end)
            if overlap_start <= overlap_end:
                overlap_days = (overlap_end - overlap_start).days + 1
                allocated[month.date()] += (
                    float(period["value"]) * overlap_days / total_days
                )

    rows = []
    for month in month_starts:
        period_start = max(month.date(), scenario.start_date)
        period_end = min((month + pd.offsets.MonthEnd(0)).date(), scenario.end_date)
        units = allocated[month.date()]
        dated_price = item.price.amount_on(period_start)
        assert dated_price is not None
        rows.append(
            _row(
                scenario,
                item,
                currency,
                period_start=period_start,
                period_end=period_end,
                days=(period_end - period_start).days + 1,
                measure="flow",
                opening_units=float("nan"),
                closing_units=float("nan"),
                average_units=float("nan"),
                units_flow=units,
                amount=units * dated_price,
            )
        )
    return pd.DataFrame(rows)


def _row(
    scenario: Scenario,
    item: CatalogItem,
    currency: str,
    *,
    period_start: date,
    period_end: date,
    days: int,
    measure: str,
    opening_units: float,
    closing_units: float,
    average_units: float,
    units_flow: float,
    amount: float,
) -> dict[str, Any]:
    sign = 1 if item.direction == "revenue" else -1
    return {
        "scenario_id": scenario.id,
        "scenario_status": scenario.status,
        "period_start": period_start,
        "period_end": period_end,
        "days": days,
        "item_id": item.id,
        "item_name": item.name,
        "direction": item.direction,
        "model": item.model,
        "measure": measure,
        "currency": currency,
        "opening_units": opening_units,
        "closing_units": closing_units,
        "average_units": average_units,
        "units_flow": units_flow,
        "amount": amount,
        "signed_amount": amount * sign,
    }


def _as_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
