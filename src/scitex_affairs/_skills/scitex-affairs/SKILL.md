---
name: scitex-affairs
description: |
  [WHAT] Business catalog, actual-observation, time-aware scenario, reporting primitives, procurement screening, contest preparation, and deck revision workflows.
  [WHEN] Use for service catalogs, pricing SSOTs, actual business reports, time-aware scenarios, public procurement screening, business contest applications, or presentation revision workflows.
  [HOW] Keep design in YAML, actuals in the resolved SciTeX PostgreSQL store, then use the Python API or `scitex-affairs` noun-verb CLI.
tags: [scitex-affairs]
primary_interface: python
interfaces:
  python: 1
  cli: 1
  skills: 1
  http: 0
---

# scitex-affairs

Use `scitex-affairs` when the source facts are simple but several consistent
representations are needed. The package deliberately separates:

- catalog and optional scenario design:
  `$SCITEX_DIR/affairs/config.yaml` (normally
  `~/.scitex/affairs/config.yaml`), or one explicit Git-tracked YAML file;
- actual observations: `scitex_dev.store` (PostgreSQL, no SQLite fallback);
- description: pandas DataFrames;
- rendering: text/CSV/JSON/Markdown/HTML, FigRecipe, or Plotly;
- browser UI: the thin `_django` SciTeX App adapter.

## Core workflow

```bash
scitex-affairs config validate --config affairs.yaml
scitex-affairs catalog show --config affairs.yaml --format markdown
scitex-affairs scenario report --config affairs.yaml \
  --scenario example --frequency quarter
```

When the canonical user config exists, omit `--config`. Resolution is shared
with other SciTeX packages through `scitex_config._ecosystem.local_state`;
do not add a second package-local path resolver.

Forecasts are optional. Do not add a scenario when a catalog and actuals answer
the decision. In a scenario, use `measure: stock` for point-in-time quantities
such as active subscriptions, and `measure: flow` for period totals such as
consulting hours or completed projects.

Never calculate annual recurring revenue as `year_end_count * monthly_price *
12`. `monthly_report()` interpolates a stock's daily path and bills its monthly
average before `summarize()` aggregates it.

## Reference

- [Installation](01_installation.md)
- [Quick start](02_quick-start.md)
- [Python API](03_python-api.md)
- [CLI reference](04_cli-reference.md)
- [Environment variables](20_env-vars.md)

## Business workflows

Read only the workflow needed for the request:

- [Public procurement](references/procurement.md): official notices, eligibility,
  scope/estimate risks, and evidence-backed opportunity reports.
- [Business contests](references/business-contests.md): entrant rules, judging
  criteria, application versions, and pitch preparation.
- [Presentations](references/presentations.md): native decks and semantic revision
  evidence, including the reusable deck snapshot/diff script.

These are reusable methods. Applicant qualifications, capacity, source exclusions,
company facts, templates, feedback, correspondence, submissions, prices, and
calendar/email identities belong to the user's private workspace. Obtain that
context for the requested task; do not copy it into this public package.
