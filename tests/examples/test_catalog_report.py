"""Smoke check for the documented catalog example."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_catalog_report_example_renders_markdown():
    """The runnable example resolves configuration and emits a table."""

    # Arrange
    root = Path(__file__).parents[2]
    environment = os.environ.copy()
    environment["SCITEX_AFFAIRS_CONFIG"] = str(root / "examples" / "example.yaml")
    command = [sys.executable, str(root / "examples" / "catalog_report.py")]
    # Act
    completed = subprocess.run(
        command, check=False, capture_output=True, text=True, env=environment
    )
    # Assert
    assert completed.returncode == 0, completed.stderr
