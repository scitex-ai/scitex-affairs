from pathlib import Path

import pytest

from scitex_affairs import load_config, monthly_report, summarize

EXAMPLE = Path(__file__).parents[2] / "examples" / "example.yaml"


@pytest.fixture(scope="module")
def monthly():
    config = load_config(EXAMPLE)
    return monthly_report(config, "measured-growth")


def test_year_end_target_is_not_applied_to_all_months(monthly):
    # Arrange
    item_rows = monthly.loc[monthly["item_id"].eq("membership"), "amount"]
    # Act
    membership = item_rows.sum()
    # Assert
    assert 70_000 < membership < 74_000


def test_flow_allocation_preserves_total(monthly):
    # Arrange
    item_rows = monthly.loc[monthly["item_id"].eq("workshop"), "units_flow"]
    # Act
    workshops = item_rows.sum()
    # Assert
    assert workshops == pytest.approx(3)


def test_quarterly_and_yearly_revenue_agree(monthly):
    # Arrange
    quarterly = summarize(monthly, "quarter")["amount"].sum()
    # Act
    yearly = summarize(monthly, "year")["amount"].sum()
    # Assert
    assert quarterly == pytest.approx(yearly)


def test_fiscal_quarter_labels_are_automatic(monthly):
    # Arrange
    fiscal_start = 9
    # Act
    labels = summarize(monthly, "quarter", fiscal_year_start_month=fiscal_start)[
        "period"
    ]
    # Assert
    assert labels.str.match(r"FY\d{4}-Q[1-4]").all()
