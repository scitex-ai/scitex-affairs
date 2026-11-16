"""Thin noun-verb CLI over the public Python API."""

from __future__ import annotations

import json
import os
from pathlib import Path

import click

from . import __version__
from .actuals import actuals_frame, open_actuals_store, record_actual
from .config import ConfigError, load_config, resolve_config_path
from .describe import catalog_frame, summarize
from .fx import disclosure
from .plot import plot_financials, save_figure
from .render import render_frame, write_frame
from .scenario import monthly_report

_FORMATS = click.Choice(["table", "csv", "json", "html", "markdown"])
_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def _config_option(function):
    """Apply the shared optional business-config CLI argument."""

    return click.option(
        "--config",
        "config_path",
        type=click.Path(exists=True, dir_okay=False),
        help=(
            "Business YAML. Defaults to $SCITEX_AFFAIRS_CONFIG, then "
            "$SCITEX_DIR/affairs/config.yaml."
        ),
    )(function)


def _show_recursive_help(ctx: click.Context) -> None:
    """Print root and immediate noun-verb help without another dependency."""

    click.echo(ctx.get_help())
    group = ctx.command
    if not isinstance(group, click.Group):
        return
    for name in group.list_commands(ctx):
        command = group.get_command(ctx, name)
        if command is None:
            continue
        child = click.Context(command, parent=ctx, info_name=name)
        click.echo(f"\n=== {ctx.info_name} {name} ===")
        click.echo(child.get_help())


@click.group(
    context_settings=_CONTEXT_SETTINGS,
    invoke_without_command=True,
    help=(
        f"scitex-affairs (v{__version__}) — keep business facts simple and "
        "derive reports consistently.\n\n"
        "Config: --config -> $SCITEX_AFFAIRS_CONFIG -> "
        "$SCITEX_DIR/affairs/config.yaml."
    ),
)
@click.version_option(__version__, "-V", "--version", prog_name="scitex-affairs")
@click.option("--help-recursive", is_flag=True, help="Show all command help.")
@click.option("--json", "as_json", is_flag=True, help="Request JSON output.")
@click.pass_context
def main(ctx: click.Context, help_recursive: bool, as_json: bool) -> None:
    """Run the scitex-affairs noun-verb CLI."""

    ctx.ensure_object(dict)
    ctx.obj["as_json"] = as_json
    if help_recursive:
        _show_recursive_help(ctx)
        ctx.exit(0)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.group("config")
def config_group() -> None:
    """Validate resolved business design configuration."""


@config_group.command("validate")
@_config_option
def config_validate(config_path: str | None) -> None:
    """Validate the resolved business YAML file.

    \b
    Example:
      $ scitex-affairs config validate
    """

    config = _load(config_path)
    click.echo(
        f"OK: {config.organization}; {len(config.catalog)} catalog items; "
        f"{len(config.scenarios)} optional scenarios"
    )


@main.group("catalog")
def catalog_group() -> None:
    """Inspect service and price definitions."""


@catalog_group.command("show")
@_config_option
@click.option("--format", "output_format", type=_FORMATS, default="table")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON records.")
@click.option("--output", type=click.Path(dir_okay=False))
def catalog_show(
    config_path: str | None,
    output_format: str,
    as_json: bool,
    output: str | None,
) -> None:
    """Render the catalog from its single YAML source.

    \b
    Example:
      $ scitex-affairs catalog show --format markdown
    """

    frame = catalog_frame(_load(config_path))
    _emit(frame, "json" if as_json else output_format, output)


@main.group("scenario")
def scenario_group() -> None:
    """Run explicitly hypothetical scenarios."""


@scenario_group.command("report")
@_config_option
@click.option("--scenario", "scenario_id", required=True)
@click.option(
    "--frequency",
    type=click.Choice(["month", "quarter", "year"]),
    default="month",
)
@click.option("--format", "output_format", type=_FORMATS, default="table")
@click.option("--output", type=click.Path(dir_okay=False))
def scenario_report(
    config_path: str | None,
    scenario_id: str,
    frequency: str,
    output_format: str,
    output: str | None,
) -> None:
    """Calculate and render a scenario at any standard period.

    \b
    Example:
      $ scitex-affairs scenario report --scenario measured-growth --frequency quarter
    """

    config = _load(config_path)
    monthly = monthly_report(config, scenario_id)
    frame = summarize(monthly, frequency, config.fiscal_year_start_month)
    _emit(frame, output_format, output)
    # Converted figures are estimates; say how and that billing differs. On
    # stderr so CSV/JSON on stdout stay machine-readable.
    for rate in monthly.attrs.get("fx", []):
        click.echo(disclosure(rate), err=True)


@scenario_group.command("plot")
@_config_option
@click.option("--scenario", "scenario_id", required=True)
@click.option(
    "--frequency",
    type=click.Choice(["month", "quarter", "year"]),
    default="month",
)
@click.option("--backend", type=click.Choice(["figrecipe", "plotly"]), default="plotly")
@click.option("--output", type=click.Path(dir_okay=False), required=True)
def scenario_plot(
    config_path: str | None,
    scenario_id: str,
    frequency: str,
    backend: str,
    output: str,
) -> None:
    """Plot a scenario with FigRecipe or Plotly.

    \b
    Example:
      $ scitex-affairs scenario plot --scenario measured-growth --output report.html
    """

    config = _load(config_path)
    report = summarize(
        monthly_report(config, scenario_id),
        frequency,
        config.fiscal_year_start_month,
    )
    save_figure(plot_financials(report, backend), output, backend)
    click.echo(output)


@main.group("observations")
def actual_group() -> None:
    """Record and inspect PostgreSQL-backed actual observations."""


@actual_group.command("list")
@click.option("--format", "output_format", type=_FORMATS, default="table")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON records.")
@click.option("--output", type=click.Path(dir_okay=False))
def actual_list(output_format: str, as_json: bool, output: str | None) -> None:
    """Render current actuals from the resolved SciTeX store.

    \b
    Example:
      $ scitex-affairs observations list --json
    """

    with open_actuals_store() as store:
        frame = actuals_frame(store)
    _emit(frame, "json" if as_json else output_format, output)


@actual_group.command("add")
@click.option("--date", "occurred_on", required=True)
@click.option("--item", "item_id", required=True)
@click.option("--metric", required=True)
@click.option("--value", type=float, required=True)
@click.option("--amount-minor", type=int)
@click.option("--currency")
@click.option("--source-ref")
@click.option("--note")
@click.option("--dimensions", help="JSON object with optional dimensions")
@click.option("--dry-run", is_flag=True, help="Validate without writing.")
@click.option("-y", "--yes", is_flag=True, help="Append without confirmation.")
def actual_add(
    occurred_on: str,
    item_id: str,
    metric: str,
    value: float,
    amount_minor: int | None,
    currency: str | None,
    source_ref: str | None,
    note: str | None,
    dimensions: str | None,
    dry_run: bool,
    yes: bool,
) -> None:
    """Append one immutable actual observation.

    \b
    Example:
      $ scitex-affairs observations add --date 2026-08-31 --item plan \
          --metric customers --value 1 --yes
    """

    try:
        parsed_dimensions = json.loads(dimensions) if dimensions else None
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"invalid --dimensions JSON: {exc}") from exc
    if parsed_dimensions is not None and not isinstance(parsed_dimensions, dict):
        raise click.ClickException("--dimensions must be a JSON object")
    if dry_run:
        click.echo("DRY RUN — actual observation is valid; no PostgreSQL write made")
        return
    if not yes:
        raise click.ClickException("refusing to write without --yes/-y")
    with open_actuals_store() as store:
        actual_id = record_actual(
            store,
            occurred_on=occurred_on,
            item_id=item_id,
            metric=metric,
            value=value,
            amount_minor=amount_minor,
            currency=currency,
            source_ref=source_ref,
            note=note,
            dimensions=parsed_dimensions,
        )
    click.echo(actual_id)


@main.group("app")
def app_group() -> None:
    """Run the SciTeX App browser adapter."""


@app_group.command("serve")
@_config_option
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8054, type=int, show_default=True)
@click.option("--open-browser/--no-open-browser", default=True)
def app_serve(
    config_path: str | None, host: str, port: int, open_browser: bool
) -> None:
    """Launch the same app plugin locally that SciTeX Hub mounts.

    \b
    Example:
      $ scitex-affairs app serve --no-open-browser
    """

    from scitex_app.embed import run_standalone

    _load(config_path)
    resolved = str(resolve_config_path(config_path).resolve())
    os.environ["SCITEX_AFFAIRS_CONFIG"] = resolved
    run_standalone(
        app_module="scitex_affairs._django",
        host=host,
        port=port,
        open_browser=open_browser,
        working_dir=str(Path(resolved).parent),
    )


@main.command("list-python-apis")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
def list_python_apis(as_json: bool) -> None:
    """List the stable public Python names.

    \b
    Example:
      $ scitex-affairs list-python-apis --json
    """

    import scitex_affairs

    names = sorted(scitex_affairs.__all__)
    if as_json:
        click.echo(json.dumps({"module": "scitex_affairs", "names": names}))
        return
    click.echo("\n".join(names))


@main.group("mcp")
def mcp_group() -> None:
    """Describe MCP integration for this parity-exempt package."""


@mcp_group.command("list-tools")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON.")
def mcp_list_tools(as_json: bool) -> None:
    """List MCP tools; this package currently exposes none.

    \b
    Example:
      $ scitex-affairs mcp list-tools --json
    """

    if as_json:
        click.echo(json.dumps({"total": 0, "tools": []}))
        return
    click.echo("scitex-affairs MCP: 0 tools (Python/CLI/App package)")


def _load(path: str | None):
    try:
        return load_config(path)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc


def _emit(frame, output_format: str, output: str | None) -> None:
    if output:
        write_frame(frame, output, output_format)
        click.echo(output)
    else:
        click.echo(render_frame(frame, output_format))


from scitex_dev.cli import attach_shell_completion, skills_click_group  # noqa: E402

main.add_command(skills_click_group(package="scitex-affairs"))
attach_shell_completion(main, prog_name="scitex-affairs")


if __name__ == "__main__":
    main()
