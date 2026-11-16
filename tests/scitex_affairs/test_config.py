from datetime import date
from pathlib import Path

import pytest

from scitex_affairs import ConfigError, load_config, resolve_config_path

EXAMPLE = Path(__file__).parents[2] / "examples" / "example.yaml"


def test_example_configuration_loads_successfully():
    # Arrange
    path = EXAMPLE
    # Act
    config = load_config(path)
    # Assert
    assert config.organization == "Example Company"


def test_explicit_config_path_has_highest_precedence():
    # Arrange
    explicit = EXAMPLE
    # Act
    resolved = resolve_config_path(explicit)
    # Assert
    assert resolved == explicit


def test_scenarios_are_optional():
    # Arrange
    raw = {
        "schema_version": 1,
        "organization": "Today Co",
        "currency": "JPY",
        "catalog": [],
    }
    # Act
    config = load_config(raw)
    # Assert
    assert config.scenarios == {}


def test_derived_discount_price():
    # Arrange
    raw = {
        "schema_version": 1,
        "organization": "Price Co",
        "currency": "JPY",
        "catalog": [
            {
                "id": "plan",
                "name": "Plan",
                "direction": "revenue",
                "model": "recurring",
                "price": {
                    "kind": "fixed",
                    "list_amount": 1000,
                    "discount_percent": 40,
                    "interval": "month",
                    "unit": "person",
                },
            }
        ],
    }
    # Act
    config = load_config(raw)
    # Assert
    assert config.catalog["plan"].price.amount == 600


def test_tbd_item_cannot_be_forecast():
    # Arrange
    raw = {
        "schema_version": 1,
        "organization": "Unknown Co",
        "currency": "JPY",
        "catalog": [
            {
                "id": "api",
                "name": "API",
                "direction": "revenue",
                "model": "usage",
                "price": {
                    "kind": "tbd",
                    "interval": "usage",
                    "unit": "request",
                },
            }
        ],
        "scenarios": {
            "bad": {
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "series": [
                    {
                        "item_id": "api",
                        "measure": "flow",
                        "periods": [
                            {
                                "start": "2026-01-01",
                                "end": "2026-01-31",
                                "value": 10,
                            }
                        ],
                    }
                ],
            }
        },
    }
    # Act
    action = lambda: load_config(raw)  # noqa: E731
    # Assert
    with pytest.raises(ConfigError, match="numeric price"):
        action()


def test_shared_discount_policy_is_dated():
    # Arrange
    config = load_config(
        {
            "schema_version": 1,
            "organization": "Policy Co",
            "currency": "JPY",
            "pricing_policies": {
                "early": {
                    "discount_schedule": [
                        {
                            "start": "2026-08-01",
                            "end": "2027-07-31",
                            "percent": 50,
                            "status": "active",
                        },
                        {
                            "start": "2027-08-01",
                            "end": "2028-07-31",
                            "percent": 30,
                            "status": "proposed",
                        },
                    ]
                }
            },
            "catalog": [
                {
                    "id": "service",
                    "name": "Service",
                    "direction": "revenue",
                    "model": "recurring",
                    "price": {
                        "kind": "fixed",
                        "list_amount": 100,
                        "policy": "early",
                        "interval": "month",
                        "unit": "customer",
                    },
                }
            ],
        }
    )
    # Act
    price = config.catalog["service"].price
    # Assert
    assert price.amount_on(date(2027, 9, 1)) == 70
