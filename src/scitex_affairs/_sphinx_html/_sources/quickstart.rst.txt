Quick Start
===========

Configuration
-------------

The default config path is ``$SCITEX_DIR/affairs/config.yaml``, normally
``~/.scitex/affairs/config.yaml``. An explicit ``--config`` or the
``SCITEX_AFFAIRS_CONFIG`` environment variable overrides it.

Command line
------------

.. code-block:: bash

   scitex-affairs config validate
   scitex-affairs catalog show --format markdown
   scitex-affairs scenario report --scenario <id> --frequency year
   scitex-affairs app serve --no-open-browser

Python
------

.. code-block:: python

   from scitex_affairs import catalog_frame, load_config, monthly_report

   config = load_config()
   catalog = catalog_frame(config)

Scenarios are optional. Point-in-time customers or subscriptions are ``stock``
measures; projects and usage totals are ``flow`` measures. The engine
integrates daily values into monthly results before fiscal-quarter or
fiscal-year aggregation, so a year-end target is never billed for all twelve
months.

Prices in another currency
--------------------------

A price may carry its own ``currency`` (for example USD) while the plan stays
in the config's ``currency``; it is converted at a live rate from
``fx.provider`` (``open.er-api.com``, ExchangeRate-API). Converted figures are
estimates: billing happens in the price's own currency, and the amount charged
in another currency depends on the card issuer's rate and fees. Every converted
row records the rate, its as-of time and source; a rate that cannot be fetched
is an error, never a guess.

Actual observations
-------------------

``scitex_affairs.actuals`` registers the ``affairs_actuals`` store with
``scitex_dev.store``. ``scitex-dev`` resolves the PostgreSQL target through
``SCITEX_STORE_DSN`` or the host service; there is no SQLite fallback.
