"""Checks for the thin SciTeX App package."""

from __future__ import annotations

from scitex_affairs._django.apps import AffairsAppConfig


def test_django_app_config_names_embedded_package():
    """The adapter uses an isolated Django application label."""

    # Arrange
    app_config = AffairsAppConfig
    # Act
    label = app_config.label
    # Assert
    assert label == "scitex_affairs_app"
