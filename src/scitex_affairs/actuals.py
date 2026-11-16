"""Append-only actual observations in the standard SciTeX PostgreSQL store."""

from __future__ import annotations

import socket
import uuid
from collections.abc import Mapping
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
from scitex_dev.store import (
    NEW_RECORD,
    FieldKind,
    FieldPolicy,
    FieldRole,
    MergeRule,
    Schema,
    Store,
    StorePlugin,
    WriterPolicy,
    resolve_target,
)

ACTUALS_SCHEMA = Schema.build(
    "affairs_actuals",
    {
        "id": FieldPolicy(
            kind=FieldKind.TEXT,
            role=FieldRole.IDENTITY,
            required=True,
            merge=MergeRule.IMMUTABLE,
            indexed=False,
        ),
        "occurred_on": FieldPolicy(
            kind=FieldKind.TEXT,
            role=FieldRole.DATA,
            required=True,
            merge=MergeRule.IMMUTABLE,
            indexed=True,
        ),
        "item_id": FieldPolicy(
            kind=FieldKind.TEXT,
            role=FieldRole.DATA,
            required=True,
            merge=MergeRule.IMMUTABLE,
            indexed=True,
        ),
        "metric": FieldPolicy(
            kind=FieldKind.TEXT,
            role=FieldRole.DATA,
            required=True,
            merge=MergeRule.IMMUTABLE,
            indexed=True,
        ),
        "value": FieldPolicy(
            kind=FieldKind.REAL,
            role=FieldRole.DATA,
            required=True,
            merge=MergeRule.IMMUTABLE,
            indexed=False,
        ),
        "amount_minor": FieldPolicy(
            kind=FieldKind.INTEGER,
            role=FieldRole.DATA,
            required=False,
            merge=MergeRule.IMMUTABLE,
            indexed=False,
        ),
        "currency": FieldPolicy(
            kind=FieldKind.TEXT,
            role=FieldRole.DATA,
            required=False,
            merge=MergeRule.IMMUTABLE,
            indexed=True,
        ),
        "source_ref": FieldPolicy(
            kind=FieldKind.TEXT,
            role=FieldRole.DATA,
            required=False,
            merge=MergeRule.IMMUTABLE,
            indexed=False,
        ),
        "note": FieldPolicy(
            kind=FieldKind.TEXT,
            role=FieldRole.DATA,
            required=False,
            merge=MergeRule.IMMUTABLE,
            indexed=False,
        ),
        "dimensions": FieldPolicy(
            kind=FieldKind.JSON,
            role=FieldRole.DATA,
            required=False,
            merge=MergeRule.IMMUTABLE,
            indexed=False,
        ),
        "recorded_at": FieldPolicy(
            kind=FieldKind.TEXT,
            role=FieldRole.DATA,
            required=True,
            merge=MergeRule.IMMUTABLE,
            indexed=False,
        ),
    },
)

ACTUALS_PLUGIN = StorePlugin(
    name="affairs_actuals",
    pkg="affairs",
    schema=ACTUALS_SCHEMA,
    writer_policy=WriterPolicy.MULTI_WRITER,
    provider="scitex_affairs.actuals",
    description="Append-only service and business actual observations",
)


def provide_store_plugins() -> tuple[StorePlugin, ...]:
    """Expose actuals through scitex-dev's leaf-store discovery contract."""

    return (ACTUALS_PLUGIN,)


def open_actuals_store(*, node: str | None = None, actor: str = "") -> Store:
    """Open the resolved PostgreSQL store; target policy belongs to scitex-dev."""

    resolved_node = node or socket.gethostname()
    return Store(
        resolve_target(ACTUALS_PLUGIN),
        ACTUALS_SCHEMA,
        node=resolved_node,
        writer_policy=ACTUALS_PLUGIN.writer_policy,
        actor=actor or resolved_node,
    )


def record_actual(
    store: Store,
    *,
    occurred_on: date | str,
    item_id: str,
    metric: str,
    value: float,
    amount_minor: int | None = None,
    currency: str | None = None,
    source_ref: str | None = None,
    note: str | None = None,
    dimensions: Mapping[str, Any] | None = None,
    record_id: str | None = None,
) -> str:
    """Append one immutable actual; corrections are new records, never edits."""

    actual_id = record_id or str(uuid.uuid4())
    values: dict[str, Any] = {
        "id": actual_id,
        "occurred_on": str(occurred_on),
        "item_id": item_id,
        "metric": metric,
        "value": float(value),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    optional = {
        "amount_minor": amount_minor,
        "currency": currency.upper() if currency else None,
        "source_ref": source_ref,
        "note": note,
        "dimensions": dict(dimensions) if dimensions else None,
    }
    values.update({key: value for key, value in optional.items() if value is not None})
    store.put(values, expected_revision=NEW_RECORD)
    return actual_id


def actuals_frame(store: Store, *, include_hidden: bool = False) -> pd.DataFrame:
    """Read actuals into pandas, preserving store metadata in explicit columns."""

    rows = []
    for row in store.rows(include_hidden=include_hidden):
        values = dict(row.values)
        values.update(
            {
                "_owner": row.owner,
                "_origin": row.origin,
                "_hidden": row.hidden,
                "_revision": store.revision(row.key),
            }
        )
        rows.append(values)
    return (
        pd.DataFrame(rows).sort_values(
            ["occurred_on", "item_id", "recorded_at"], ignore_index=True
        )
        if rows
        else pd.DataFrame(columns=list(ACTUALS_SCHEMA.fields))
    )
