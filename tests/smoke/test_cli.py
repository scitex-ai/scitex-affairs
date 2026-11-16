"""Fast installed-CLI smoke checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.smoke
def test_module_cli_validates_example_configuration():
    """The module entry point validates a complete YAML document."""

    # Arrange
    example = Path(__file__).parents[2] / "examples" / "example.yaml"
    command = [
        sys.executable,
        "-m",
        "scitex_affairs",
        "config",
        "validate",
        "--config",
        str(example),
    ]
    # Act
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    # Assert
    assert completed.returncode == 0, completed.stderr
