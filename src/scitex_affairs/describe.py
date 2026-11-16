"""Pandas-first descriptions of catalogs and calculated ledgers."""

from __future__ import annotations

import pandas as pd

from .config import AffairsConfig


def catalog_frame(config: AffairsConfig) -> pd.DataFrame:
    """Return the catalog as a stable, renderer-independent DataFrame."""

    rows = [
        {
            "id": item.id,
            "name": item.name,
            "direction": item.direction,
            "model": item.model,
            "price": item.price.amount,
            "price_kind": item.price.kind,
            "list_price": item.price.list_amount,
            "discount_percent": item.price.discount_percent,
            "markup_percent": item.price.markup_percent,
            "pricing_policy": item.price.policy,
            "currency": config.currency,
            "interval": item.price.interval,
            "unit": item.price.unit,
            "category": item.category,
            "status": item.status,
            "automated": item.automated,
            "description": item.description,
        }
        for item in config.catalog.values()
    ]
    return pd.DataFrame(rows)


def summarize(
    monthly: pd.DataFrame,
    frequency: str = "month",
    fiscal_year_start_month: int = 1,
) -> pd.DataFrame:
    """Aggregate the canonical monthly ledger without losing stock semantics."""

    if frequency not in {"month", "quarter", "year"}:
        raise ValueError("frequency must be month, quarter, or year")
    if monthly.empty:
        return monthly.copy()
    frame = monthly.copy()
    starts = pd.to_datetime(frame["period_start"])
    frame["period"] = _period_labels(starts, frequency, fiscal_year_start_month)
    frame["weighted_stock"] = frame["average_units"].fillna(0) * frame["days"]
    stock_days = frame["days"].where(frame["measure"].eq("stock"), 0)
    frame["stock_days"] = stock_days
    keys = [
        "scenario_id",
        "scenario_status",
        "period",
        "item_id",
        "item_name",
        "direction",
        "model",
        "measure",
        "currency",
    ]
    groups = frame.groupby(keys, sort=True, dropna=False)
    result = groups.agg(
        period_start=("period_start", "min"),
        period_end=("period_end", "max"),
        days=("days", "sum"),
        opening_units=("opening_units", "first"),
        closing_units=("closing_units", "last"),
        units_flow=("units_flow", "sum"),
        amount=("amount", "sum"),
        signed_amount=("signed_amount", "sum"),
        weighted_stock=("weighted_stock", "sum"),
        stock_days=("stock_days", "sum"),
    ).reset_index()
    result["average_units"] = result["weighted_stock"].div(
        result["stock_days"].where(result["stock_days"].ne(0))
    )
    return result.drop(columns=["weighted_stock", "stock_days"])


def financial_statement(report: pd.DataFrame) -> pd.DataFrame:
    """Reduce an item-level report to revenue, expense, and net by period."""

    if report.empty:
        return pd.DataFrame(columns=["period", "revenue", "expense", "net"])
    frame = report.copy()
    if "period" not in frame:
        frame["period"] = (
            pd.to_datetime(frame["period_start"]).dt.to_period("M").astype(str)
        )
    pivot = frame.pivot_table(
        index="period",
        columns="direction",
        values="amount",
        aggfunc="sum",
        fill_value=0,
    )
    for column in ("revenue", "expense"):
        if column not in pivot:
            pivot[column] = 0.0
    pivot["net"] = pivot["revenue"] - pivot["expense"]
    return pivot[["revenue", "expense", "net"]].reset_index()


def _period_labels(starts: pd.Series, frequency: str, fiscal_start: int) -> pd.Series:
    if frequency == "month":
        return starts.dt.to_period("M").astype(str)
    end_month = 12 if fiscal_start == 1 else fiscal_start - 1
    suffix = pd.Timestamp(2000, end_month, 1).strftime("%b").upper()
    if frequency == "quarter":
        periods = starts.dt.to_period(f"Q-{suffix}")
        return periods.map(lambda period: f"FY{period.qyear}-Q{period.quarter}")
    periods = starts.dt.to_period(f"Y-{suffix}")
    return periods.map(lambda period: f"FY{period.year}")
