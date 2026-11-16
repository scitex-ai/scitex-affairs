---
description: "[TOPIC] Environment Variables [DETAILS] Shared path and store variables."
tags: [scitex-affairs-env-vars]
---

# Environment variables

| Variable | Owner | Meaning |
|---|---|---|
| `SCITEX_DIR` | `scitex-config` | Ecosystem user-state root |
| `SCITEX_AFFAIRS_CONFIG` | `scitex-affairs` | Explicit YAML override |
| `SCITEX_STORE_DSN` | `scitex-dev` | PostgreSQL target override |

Do not introduce a second business-specific database variable. PostgreSQL
target resolution belongs to `scitex_dev.store` ecosystem-wide.
