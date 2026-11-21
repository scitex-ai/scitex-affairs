"""Runtime gate for every SciTeX package imported by scitex-affairs."""

from __future__ import annotations

import importlib

import pytest

CROSS_PACKAGE_IMPORTS = [
    "scitex_app.embed",
    "scitex_config._ecosystem",
    "scitex_dev",
    "scitex_dev.cli",
    "scitex_dev.store",
    "scitex_logging",
    "scitex_ui",
]


@pytest.mark.parametrize("module_name", CROSS_PACKAGE_IMPORTS)
def test_cross_package_module_imports_without_attribute_error(module_name):
    """Every installed cross-package module imports through its used path."""

    # Arrange
    pytest.importorskip(module_name.split(".")[0])
    # Act
    module = importlib.import_module(module_name)
    # Assert
    assert module is not None
