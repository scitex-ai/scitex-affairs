---
description: "[TOPIC] Installation [DETAILS] Base and complete installation through uv or pip."
tags: [scitex-affairs-installation]
---

# Installation

Install the complete package when tables, plots, and the browser app are
required:

```bash
uv pip install scitex-affairs[all]
```

For development, install the working tree through the target environment:

```bash
uv pip install --python .venv/bin/python -e "$HOME/proj/scitex-affairs[all]"
```

The base install retains the catalog, pandas, configuration, and PostgreSQL
store primitives. Plotly and FigRecipe are in the single `[all]` feature
bucket.
