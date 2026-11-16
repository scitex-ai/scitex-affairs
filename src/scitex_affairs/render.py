"""Replaceable text and file renderers for pandas business reports."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def render_frame(frame: pd.DataFrame, format: str = "table") -> str:
    """Render a DataFrame without changing its business meaning."""

    if format == "table":
        return frame.to_string(index=False)
    if format == "csv":
        return frame.to_csv(index=False)
    if format == "json":
        return frame.to_json(orient="records", date_format="iso", indent=2)
    if format == "html":
        return frame.to_html(index=False, classes=["data-table"], border=0)
    if format == "markdown":
        return _markdown(frame)
    raise ValueError("format must be table, csv, json, html, or markdown")


def write_frame(
    frame: pd.DataFrame, path: str | Path, format: str | None = None
) -> Path:
    """Write a rendered DataFrame, inferring the format from the suffix."""

    destination = Path(path)
    selected = format or _format_for_suffix(destination.suffix)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_frame(frame, selected), encoding="utf-8")
    return destination


def _markdown(frame: pd.DataFrame) -> str:
    headers = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(_cell(header) for header in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in frame.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(_cell(value) for value in row) + " |")
    return "\n".join(lines) + "\n"


def _cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).replace("|", "\\|").replace("\n", " ")


def _format_for_suffix(suffix: str) -> str:
    formats = {
        ".csv": "csv",
        ".json": "json",
        ".html": "html",
        ".md": "markdown",
        ".markdown": "markdown",
        ".txt": "table",
    }
    try:
        return formats[suffix.lower()]
    except KeyError as exc:
        raise ValueError(f"cannot infer output format from suffix: {suffix}") from exc
