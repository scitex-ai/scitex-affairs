---
description: "[TOPIC] Quick Start [DETAILS] Validate and render the canonical user config."
tags: [scitex-affairs-quick-start]
---

# Quick start

Place company-specific facts at the canonical user path and validate them:

```bash
mkdir -p "${SCITEX_DIR:-$HOME/.scitex}/business"
scitex-affairs config validate
scitex-affairs catalog show --format markdown
```

Keep forecasts absent unless they answer a current decision. If needed, use
`stock` for point-in-time subscriber counts and `flow` for period totals.
