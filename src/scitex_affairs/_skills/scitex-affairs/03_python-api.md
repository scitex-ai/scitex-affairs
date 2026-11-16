---
description: "[TOPIC] Python API [DETAILS] Load catalogs, report, and append actuals."
tags: [scitex-affairs-python-api]
---

# Python API

```python
from scitex_affairs import catalog_frame, load_config

config = load_config()
catalog = catalog_frame(config)
```

Optional scenarios use `monthly_report(config, scenario_id)` and
`summarize(frame, "quarter", config.fiscal_year_start_month)`. Actual records
use `open_actuals_store()` and `record_actual()` from
`scitex_affairs.actuals`; the package does not resolve a database itself.

## Prices in another currency

Set `price.currency` (e.g. `USD`) and declare `fx.provider` (`open.er-api.com`). `monthly_report()` fetches the rate with `fetch_rate()` (or takes `rates={'USD': FxRate}`) and converts into `config.currency`.

Every converted row records `price_currency`, `fx_rate`, `fx_as_of` and `fx_source`. A price in another currency without `fx.provider` is a config error, and a rate that cannot be fetched raises `FxError`: there is no fallback rate. Converted figures are **estimates**: actual billing is in the price's own currency, and an amount charged in another currency is set by the card issuer's rate and fees at settlement. `scitex_affairs.fx.disclosure(rate, 'en' | 'ja')` renders that statement; `scitex-affairs scenario report` prints it whenever a conversion was used.
