# Contributing to scitex-affairs

Thank you for helping make routine business reporting less repetitive.

## Quick start

```bash
uv pip install -e ".[all]"
ruff check .
python -m pytest
```

Sign the [CLA](CLA.md) when prompted on your first pull request.

## Standards

This package follows the SciTeX leaf-package conventions. Keep configuration,
PostgreSQL state, pandas descriptions, and rendering separated. New behavior
needs focused tests and documentation, and scenarios must distinguish stocks
from flows.

Use one logical change per pull request and explain why the change is needed.
