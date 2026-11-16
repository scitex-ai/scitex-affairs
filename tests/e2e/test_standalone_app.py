"""Opt-in standalone app workflow."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest


@pytest.mark.e2e
@pytest.mark.skipif(os.environ.get("RUN_E2E") != "1", reason="set RUN_E2E=1")
def test_standalone_app_serves_configured_organization():
    """The packaged Django adapter serves the same resolved catalog."""

    # Arrange
    example = Path(__file__).parents[2] / "examples" / "example.yaml"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    command = [
        sys.executable,
        "-m",
        "scitex_affairs",
        "app",
        "serve",
        "--config",
        str(example),
        "--port",
        str(port),
        "--no-open-browser",
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    body = ""
    # Act
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as response:
                    body = response.read().decode("utf-8")
                    break
            except OSError:
                time.sleep(0.2)
    finally:
        process.terminate()
        process.wait(timeout=5)
    # Assert
    assert "Example Company" in body
