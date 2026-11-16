from pathlib import Path

from scitex_affairs import load_config, monthly_report, summarize
from scitex_affairs.plot import plot_financials, save_figure
from scitex_affairs.render import render_frame

EXAMPLE = Path(__file__).parents[2] / "examples" / "example.yaml"


def _report():
    config = load_config(EXAMPLE)
    return summarize(monthly_report(config, "measured-growth"), "quarter")


def test_markdown_renderer_has_headers():
    # Arrange
    report = _report()
    # Act
    rendered = render_frame(report, "markdown")
    # Assert
    assert "| scenario_id |" in rendered


def test_plotly_writes_self_contained_html(tmp_path):
    # Arrange
    destination = tmp_path / "report.html"
    # Act
    save_figure(plot_financials(_report(), "plotly"), destination, "plotly")
    # Assert
    assert destination.stat().st_size > 1_000


def test_figrecipe_writes_png(tmp_path):
    # Arrange
    destination = tmp_path / "report.png"
    # Act
    save_figure(plot_financials(_report(), "figrecipe"), destination, "figrecipe")
    # Assert
    assert destination.stat().st_size > 1_000
