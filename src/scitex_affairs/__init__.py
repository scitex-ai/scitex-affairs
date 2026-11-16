"""Business and personal affairs: catalogs, actuals, scenarios, reports, and plots."""

from __future__ import annotations

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

try:
    __version__ = version("scitex-affairs")
except PackageNotFoundError:
    __version__ = "0.0.0+local"

# PEP 562 lazy exports: `import scitex_affairs` stays cheap (pandas loads only
# when a name below is first used). Click runs the program once per Tab press,
# so an eager import made shell completion slow (audit-cli §10, 633ms > 500ms).
_LAZY: dict[str, str] = {
    "AffairsConfig": ".config",
    "CatalogItem": ".config",
    "ConfigError": ".config",
    "DiscountPhase": ".config",
    "Price": ".config",
    "Scenario": ".config",
    "load_config": ".config",
    "resolve_config_path": ".config",
    "catalog_frame": ".describe",
    "financial_statement": ".describe",
    "summarize": ".describe",
    "monthly_report": ".scenario",
    "FxError": ".fx",
    "FxRate": ".fx",
    "fetch_rate": ".fx",
}

if TYPE_CHECKING:
    from .config import (
        AffairsConfig,
        CatalogItem,
        ConfigError,
        DiscountPhase,
        Price,
        Scenario,
        load_config,
        resolve_config_path,
    )
    from .describe import catalog_frame, financial_statement, summarize
    from .fx import FxError, FxRate, fetch_rate
    from .scenario import monthly_report


def __getattr__(name: str) -> Any:
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module, __name__), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY))


__all__ = [
    "AffairsConfig",
    "CatalogItem",
    "ConfigError",
    "DiscountPhase",
    "FxError",
    "FxRate",
    "Price",
    "Scenario",
    "catalog_frame",
    "fetch_rate",
    "financial_statement",
    "load_config",
    "resolve_config_path",
    "monthly_report",
    "summarize",
    "__version__",
]
