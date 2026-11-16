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
