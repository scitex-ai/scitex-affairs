---
description: "[TOPIC] CLI Reference [DETAILS] Commands for reports, actuals, and the app."
tags: [scitex-affairs-cli-reference]
---

# CLI reference

| Command | Purpose |
|---|---|
| `config validate` | Validate the resolved YAML |
| `catalog show` | Render catalog facts |
| `scenario report` | Aggregate an explicit scenario |
| `scenario plot` | Save FigRecipe or Plotly output |
| `observations list` | Read PostgreSQL observations |
| `observations add` | Append an immutable observation |
| `app serve` | Run the standalone Hub adapter |

Every config-reading command accepts `--config`; omit it for the canonical
SciTeX user path.
