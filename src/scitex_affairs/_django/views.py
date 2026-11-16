"""Thin Django views over the public scitex-affairs Python API."""

from __future__ import annotations

from django.http import JsonResponse
from django.shortcuts import render
from scitex_app.embed import mount_prefix
from scitex_ui import get_component

from ..config import ConfigError, load_config
from ..describe import catalog_frame, financial_statement, summarize
from ..scenario import monthly_report


def dashboard(request):
    """Render a catalog and optional scenario summary."""

    prefix = mount_prefix(request)
    data_table = get_component("data-table")
    try:
        config = _config()
    except ConfigError as exc:
        return render(
            request,
            "scitex_affairs/dashboard.html",
            {"error": str(exc), "mount_prefix": prefix, "data_table": data_table},
            status=400,
        )
    scenario_id = request.GET.get("scenario", "")
    statement = None
    scenario = None
    if scenario_id:
        try:
            scenario = config.scenarios[scenario_id]
            report = summarize(
                monthly_report(config, scenario_id),
                "month",
                config.fiscal_year_start_month,
            )
            statement = financial_statement(report).to_dict(orient="records")
        except (ConfigError, KeyError) as exc:
            return render(
                request,
                "scitex_affairs/dashboard.html",
                {"error": str(exc), "mount_prefix": prefix, "data_table": data_table},
                status=400,
            )
    return render(
        request,
        "scitex_affairs/dashboard.html",
        {
            "organization": config.organization,
            "currency": config.currency,
            "catalog": catalog_frame(config).to_dict(orient="records"),
            "scenarios": config.scenarios.values(),
            "selected_scenario": scenario,
            "statement": statement,
            "mount_prefix": prefix,
            "data_table": data_table,
        },
    )


def report_api(request):
    """Return the same report DataFrame as JSON for richer frontends."""

    try:
        config = _config()
        scenario_id = request.GET.get("scenario", "")
        frequency = request.GET.get("frequency", "month")
        report = summarize(
            monthly_report(config, scenario_id),
            frequency,
            config.fiscal_year_start_month,
        )
    except (ConfigError, ValueError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"records": report.to_dict(orient="records")})


def _config():
    return load_config()
