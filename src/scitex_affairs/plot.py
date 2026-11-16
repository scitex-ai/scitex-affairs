"""Financial plot adapters for FigRecipe and Plotly."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from scitex_dev import try_import_optional

from .describe import financial_statement


def plot_financials(report: pd.DataFrame, backend: str = "plotly") -> Any:
    """Plot revenue, expense, and net from any summarized report."""

    statement = financial_statement(report)
    if backend == "plotly":
        go = try_import_optional(
            "plotly.graph_objects", extra="all", pkg="scitex-affairs"
        )
        if go is None:
            raise ImportError("Plotly rendering requires scitex-affairs[all]")

        figure = go.Figure()
        for column in ("revenue", "expense", "net"):
            figure.add_scatter(
                x=statement["period"].astype(str),
                y=statement[column],
                mode="lines+markers",
                name=column.title(),
            )
        figure.update_layout(
            title="Business scenario (exploratory)",
            xaxis_title="Period",
            yaxis_title="Amount",
            template="plotly_white",
        )
        return figure
    if backend == "figrecipe":
        fr = try_import_optional("figrecipe", extra="all", pkg="scitex-affairs")
        if fr is None:
            raise ImportError("FigRecipe rendering requires scitex-affairs[all]")

        figure, axes = fr.subplots(
            axes_width_mm=120,
            axes_height_mm=70,
            constrained_layout=False,
        )
        for column in ("revenue", "expense", "net"):
            axes.plot(
                statement["period"].astype(str).tolist(),
                statement[column].tolist(),
                marker="o",
                label=column.title(),
            )
        axes.set_xlabel("Period")
        axes.set_ylabel("Amount")
        axes.set_title("Business scenario (exploratory)")
        axes.legend()
        return figure
    raise ValueError("backend must be figrecipe or plotly")


def save_figure(figure: Any, path: str | Path, backend: str) -> Path:
    """Save a figure through its owning backend."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if backend == "plotly":
        if destination.suffix.lower() != ".html":
            raise ValueError(
                "Plotly output must use .html (no Kaleido dependency required)"
            )
        figure.write_html(destination, include_plotlyjs=True)
    elif backend == "figrecipe":
        fr = try_import_optional("figrecipe", extra="all", pkg="scitex-affairs")
        if fr is None:
            raise ImportError("FigRecipe rendering requires scitex-affairs[all]")

        fr.save(figure, destination, validate=False, verbose=False)
    else:
        raise ValueError("backend must be figrecipe or plotly")
    return destination
