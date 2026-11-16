# Changelog

All notable changes to `scitex-affairs` are documented here. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions
follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-11-16

- Prices in another currency: `price.currency` plus `fx.provider`; `monthly_report()` converts into `config.currency` at a live rate from ExchangeRate-API (`open.er-api.com`, the source scitex.ai uses) and records `price_currency`, `fx_rate`, `fx_as_of`, `fx_source` on converted rows.
- `scitex_affairs.fx`: `fetch_rate()`, `FxRate`, `FxError`, and `disclosure()` (EN/JA) stating that converted figures are estimates and that actual billing differs. `scenario report` prints it when a conversion was used.
- No fallback rate: a foreign-currency price without `fx.provider` is a config error, and an unreachable or malformed rate raises `FxError`.

## [0.1.0] - 2026-11-16

First public release. The package was developed privately as
`scitex-business` and renamed `scitex-affairs` before publication, because it
covers business and personal affairs.

- Add reusable catalog and dated pricing-policy validation.
- Add time-aware stock and flow scenario calculations with pandas reports.
- Add PostgreSQL actual-observation store through `scitex-dev` primitives.
- Add table, FigRecipe, Plotly, CLI, and SciTeX Hub rendering surfaces.
- Package the SciTeX skill under `src/scitex_affairs/_skills/`.
- Config at `$SCITEX_DIR/affairs/config.yaml` (override with `--config` or
  `SCITEX_AFFAIRS_CONFIG`); actual observations in the `affairs_actuals` store.
- Lazy package exports (PEP 562): `import scitex_affairs` no longer loads pandas.
- Sphinx documentation, with the HTML bundle shipped inside the wheel.
- Standard SciTeX CI: the org `ci.yml` caller, CLA, PyPI trusted publishing on
  tag, and syncing `main` to each release tag.
