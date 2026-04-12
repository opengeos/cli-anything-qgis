"""cli-anything-qgis — Command-line interface for QGIS.

Provides both one-shot subcommands and an interactive REPL for operating
QGIS in headless mode. All commands support --json for machine-readable output.
"""

import json
import os
import shlex
import sys

import click

# ── Global state ──────────────────────────────────────────────────────

_json_mode = False
_session = None


def _output(data):
    """Output data in JSON or human-readable format."""
    if _json_mode:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        _pretty_print(data)


def _pretty_print(data):
    """Human-readable output for dict results."""
    if not isinstance(data, dict):
        click.echo(str(data))
        return

    action = data.get("action", "")

    # Skip internal keys in pretty output
    skip_keys = {"action"}

    for key, value in data.items():
        if key in skip_keys:
            continue
        if isinstance(value, list):
            click.echo(f"  {key}:")
            for item in value[:50]:
                if isinstance(item, dict):
                    parts = [f"{k}={v}" for k, v in item.items()]
                    click.echo(f"    - {', '.join(parts)}")
                else:
                    click.echo(f"    - {item}")
            if len(value) > 50:
                click.echo(f"    ... and {len(value) - 50} more")
        elif isinstance(value, dict):
            click.echo(f"  {key}:")
            for k, v in value.items():
                click.echo(f"    {k}: {v}")
        else:
            click.echo(f"  {key}: {value}")


def _error(message):
    """Output an error."""
    if _json_mode:
        click.echo(json.dumps({"error": str(message)}), err=True)
    else:
        click.echo(f"Error: {message}", err=True)


def _auto_save_project():
    """Auto-save project after mutation commands (when running in CLI mode).

    In CLI mode, each invocation is a separate process. If a project file
    was opened with -p, we auto-save after mutations so the next invocation
    can see the changes.
    """
    from qgis.core import QgsProject

    project = QgsProject.instance()
    if project.fileName():
        project.write()


# ── Main CLI group ────────────────────────────────────────────────────


@click.group(invoke_without_command=True)
@click.option("--json", "json_mode", is_flag=True, help="Output in JSON format.")
@click.option(
    "--project",
    "-p",
    "project_path",
    default=None,
    help="Project file to open (.qgs/.qgz).",
)
@click.option(
    "--session",
    "-s",
    "session_path",
    default=None,
    help="Session file for state persistence.",
)
@click.version_option(version="1.0.0", prog_name="cli-anything-qgis")
@click.pass_context
def cli(ctx, json_mode, project_path, session_path):
    """QGIS command-line interface — operate QGIS without a GUI."""
    global _json_mode, _session
    _json_mode = json_mode

    ctx.ensure_object(dict)
    ctx.obj["json_mode"] = json_mode
    ctx.obj["project_path"] = project_path
    ctx.obj["session_path"] = session_path

    # Initialize session
    from cli_anything.qgis.core.session import Session

    _session = Session(session_path)

    # Open project if specified
    if project_path and os.path.exists(project_path):
        try:
            from cli_anything.qgis.core.project import open_project

            open_project(project_path)
            _session.set_project(project_path)
        except Exception as e:
            _error(f"Failed to open project: {e}")

    # Enter REPL if no subcommand
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl, project_path=project_path)


# ── Project commands ──────────────────────────────────────────────────


@cli.group()
def project():
    """Project management — create, open, save, info."""
    pass


@project.command("new")
@click.option(
    "-o",
    "--output",
    "output_path",
    required=True,
    help="Output project file path (.qgs or .qgz).",
)
@click.option("--title", "-t", default="", help="Project title.")
@click.option("--crs", default="EPSG:4326", help="Coordinate reference system.")
def project_new(output_path, title, crs):
    """Create a new QGIS project."""
    try:
        from cli_anything.qgis.core.project import create_project

        result = create_project(output_path, title=title, crs=crs)
        if _session:
            _session.set_project(output_path)
            _session.save()
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@project.command("open")
@click.argument("project_path")
def project_open(project_path):
    """Open an existing QGIS project."""
    try:
        from cli_anything.qgis.core.project import open_project

        result = open_project(project_path)
        if _session:
            _session.set_project(project_path)
            _session.save()
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@project.command("save")
@click.option(
    "-o",
    "--output",
    "output_path",
    default=None,
    help="Save-as path. Omit to save in place.",
)
def project_save(output_path):
    """Save the current project."""
    try:
        from cli_anything.qgis.core.project import save_project

        result = save_project(output_path)
        if _session:
            _session.state["modified"] = False
            _session.save()
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@project.command("info")
@click.option(
    "-p",
    "--project",
    "project_path",
    default=None,
    help="Project file path. Omit to use current project.",
)
def project_info_cmd(project_path):
    """Show project information."""
    try:
        from cli_anything.qgis.core.project import project_info

        result = project_info(project_path)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@project.command("close")
def project_close():
    """Close the current project."""
    try:
        from cli_anything.qgis.core.project import close_project

        result = close_project()
        if _session:
            _session.set_project(None)
            _session.save()
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


# ── Layer commands ────────────────────────────────────────────────────


@cli.group()
def layer():
    """Layer management — add, remove, list, info."""
    pass


@layer.command("add-vector")
@click.argument("source")
@click.option("--name", "-n", default=None, help="Display name.")
@click.option("--provider", default="ogr", help="Data provider (ogr, postgres, etc.).")
def layer_add_vector(source, name, provider):
    """Add a vector layer from a data source."""
    try:
        from cli_anything.qgis.core.layer import add_vector_layer

        result = add_vector_layer(source, name=name, provider=provider)
        _auto_save_project()
        if _session:
            _session.add_layer(
                {
                    "id": result["id"],
                    "name": result["name"],
                    "type": "vector",
                    "source": result["source"],
                }
            )
            _session.save()
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@layer.command("add-raster")
@click.argument("source")
@click.option("--name", "-n", default=None, help="Display name.")
@click.option("--provider", default="gdal", help="Data provider (gdal, wms, etc.).")
def layer_add_raster(source, name, provider):
    """Add a raster layer from a data source."""
    try:
        from cli_anything.qgis.core.layer import add_raster_layer

        result = add_raster_layer(source, name=name, provider=provider)
        _auto_save_project()
        if _session:
            _session.add_layer(
                {
                    "id": result["id"],
                    "name": result["name"],
                    "type": "raster",
                    "source": result["source"],
                }
            )
            _session.save()
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@layer.command("remove")
@click.argument("layer_id")
def layer_remove(layer_id):
    """Remove a layer by its ID."""
    try:
        from cli_anything.qgis.core.layer import remove_layer

        result = remove_layer(layer_id)
        _auto_save_project()
        if _session:
            _session.remove_layer(layer_id)
            _session.save()
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@layer.command("list")
def layer_list():
    """List all layers in the current project."""
    try:
        from cli_anything.qgis.core.layer import list_layers

        result = list_layers()
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@layer.command("info")
@click.argument("layer_id")
def layer_info_cmd(layer_id):
    """Show detailed information about a layer."""
    try:
        from cli_anything.qgis.core.layer import layer_info

        result = layer_info(layer_id)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


# ── Vector commands ───────────────────────────────────────────────────


@cli.group()
def vector():
    """Vector operations — query features, statistics, filter."""
    pass


@vector.command("query")
@click.argument("layer_id")
@click.option("--expression", "-e", default=None, help="Filter expression.")
@click.option("--limit", "-l", default=100, help="Max features to return.")
@click.option("--fields", "-f", default=None, help="Comma-separated field names.")
def vector_query(layer_id, expression, limit, fields):
    """Query features from a vector layer."""
    try:
        from cli_anything.qgis.core.vector import query_features

        field_list = fields.split(",") if fields else None
        result = query_features(
            layer_id, expression=expression, limit=limit, fields=field_list
        )
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@vector.command("stats")
@click.argument("layer_id")
@click.argument("field_name")
def vector_stats(layer_id, field_name):
    """Compute statistics for a vector field."""
    try:
        from cli_anything.qgis.core.vector import field_statistics

        result = field_statistics(layer_id, field_name)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@vector.command("count")
@click.argument("layer_id")
@click.option("--expression", "-e", default=None, help="Filter expression.")
def vector_count(layer_id, expression):
    """Count features in a vector layer."""
    try:
        from cli_anything.qgis.core.vector import count_features

        result = count_features(layer_id, expression=expression)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@vector.command("extent")
@click.argument("layer_id")
def vector_extent(layer_id):
    """Get the bounding box of a vector layer."""
    try:
        from cli_anything.qgis.core.vector import get_extent

        result = get_extent(layer_id)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


# ── Raster commands ───────────────────────────────────────────────────


@cli.group()
def raster():
    """Raster operations — info, band statistics."""
    pass


@raster.command("info")
@click.argument("layer_id")
def raster_info_cmd(layer_id):
    """Show detailed raster layer information."""
    try:
        from cli_anything.qgis.core.raster import raster_info

        result = raster_info(layer_id)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@raster.command("stats")
@click.argument("layer_id")
@click.option("--band", "-b", default=1, help="Band number (1-based).")
def raster_stats(layer_id, band):
    """Compute statistics for a raster band."""
    try:
        from cli_anything.qgis.core.raster import band_statistics

        result = band_statistics(layer_id, band=band)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


# ── Style commands ────────────────────────────────────────────────────


@cli.group()
def style():
    """Styling — renderers, classification, labeling."""
    pass


@style.command("single-symbol")
@click.argument("layer_id")
@click.option("--color", "-c", default="blue", help="Symbol color.")
@click.option("--opacity", default=1.0, help="Opacity (0.0-1.0).")
def style_single(layer_id, color, opacity):
    """Apply a single-symbol renderer to a vector layer."""
    try:
        from cli_anything.qgis.core.style import apply_single_symbol

        result = apply_single_symbol(layer_id, color=color, opacity=opacity)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@style.command("categorized")
@click.argument("layer_id")
@click.argument("field_name")
@click.option("--color-ramp", default="Spectral", help="Color ramp name.")
def style_categorized(layer_id, field_name, color_ramp):
    """Apply a categorized renderer based on a field."""
    try:
        from cli_anything.qgis.core.style import apply_categorized

        result = apply_categorized(layer_id, field_name, color_ramp=color_ramp)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@style.command("graduated")
@click.argument("layer_id")
@click.argument("field_name")
@click.option("--classes", default=5, help="Number of classes.")
@click.option(
    "--mode",
    default="equal_interval",
    type=click.Choice(["equal_interval", "quantile", "natural_breaks"]),
)
@click.option("--color-ramp", default="Reds", help="Color ramp name.")
def style_graduated(layer_id, field_name, classes, mode, color_ramp):
    """Apply a graduated renderer for numeric fields."""
    try:
        from cli_anything.qgis.core.style import apply_graduated

        result = apply_graduated(
            layer_id, field_name, classes=classes, mode=mode, color_ramp=color_ramp
        )
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@style.command("labels")
@click.argument("layer_id")
@click.argument("field_name")
@click.option("--font-size", default=10, help="Font size in points.")
@click.option("--color", default="black", help="Label color.")
def style_labels(layer_id, field_name, font_size, color):
    """Enable labeling on a vector layer."""
    try:
        from cli_anything.qgis.core.style import apply_labels

        result = apply_labels(layer_id, field_name, font_size=font_size, color=color)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@style.command("load")
@click.argument("layer_id")
@click.argument("qml_path")
def style_load(layer_id, qml_path):
    """Load a QML style file onto a layer."""
    try:
        from cli_anything.qgis.core.style import load_style

        result = load_style(layer_id, qml_path)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@style.command("save")
@click.argument("layer_id")
@click.argument("qml_path")
def style_save(layer_id, qml_path):
    """Save a layer's style to a QML file."""
    try:
        from cli_anything.qgis.core.style import save_style

        result = save_style(layer_id, qml_path)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


# ── Processing commands ───────────────────────────────────────────────


@cli.group("processing")
def processing_group():
    """Processing — list and run QGIS algorithms."""
    pass


@processing_group.command("list")
@click.option("--provider", default=None, help="Filter by provider ID.")
@click.option("--search", "-s", default=None, help="Search algorithms by name.")
def processing_list(provider, search):
    """List available processing algorithms."""
    try:
        from cli_anything.qgis.core.processing_ops import list_algorithms

        result = list_algorithms(provider=provider, search=search)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@processing_group.command("info")
@click.argument("algorithm_id")
def processing_info(algorithm_id):
    """Show detailed info about a processing algorithm."""
    try:
        from cli_anything.qgis.core.processing_ops import algorithm_info

        result = algorithm_info(algorithm_id)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@processing_group.command("run")
@click.argument("algorithm_id")
@click.option(
    "--param",
    "-P",
    multiple=True,
    help="Parameter as KEY=VALUE. Repeat for multiple params.",
)
def processing_run(algorithm_id, param):
    """Run a processing algorithm with given parameters."""
    try:
        from cli_anything.qgis.core.processing_ops import run_algorithm

        parameters = {}
        for p in param:
            if "=" not in p:
                _error(f"Invalid parameter format: {p}. Use KEY=VALUE.")
                sys.exit(1)
            key, value = p.split("=", 1)
            # Try to parse numeric values
            try:
                value = float(value)
                if value == int(value):
                    value = int(value)
            except ValueError:
                pass
            parameters[key] = value

        result = run_algorithm(algorithm_id, parameters)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@processing_group.command("providers")
def processing_providers():
    """List available processing providers."""
    try:
        from cli_anything.qgis.core.processing_ops import list_providers

        result = list_providers()
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


# ── Layout commands ───────────────────────────────────────────────────


@cli.group()
def layout():
    """Layout — create print layouts, add items, export."""
    pass


@layout.command("new")
@click.option("--name", "-n", default="Layout 1", help="Layout name.")
@click.option("--page-size", default="A4", help="Page size (A4, A3, Letter, etc.).")
@click.option(
    "--orientation", default="landscape", type=click.Choice(["landscape", "portrait"])
)
def layout_new(name, page_size, orientation):
    """Create a new print layout."""
    try:
        from cli_anything.qgis.core.layout import create_layout

        result = create_layout(name=name, page_size=page_size, orientation=orientation)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@layout.command("list")
def layout_list():
    """List all print layouts."""
    try:
        from cli_anything.qgis.core.layout import list_layouts

        result = list_layouts()
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@layout.command("add-map")
@click.argument("layout_name")
@click.option("--x", default=10.0, help="X position in mm.")
@click.option("--y", default=10.0, help="Y position in mm.")
@click.option("--width", default=None, type=float, help="Width in mm.")
@click.option("--height", default=None, type=float, help="Height in mm.")
def layout_add_map(layout_name, x, y, width, height):
    """Add a map item to a layout."""
    try:
        from cli_anything.qgis.core.layout import add_map

        result = add_map(layout_name, x=x, y=y, width=width, height=height)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@layout.command("add-legend")
@click.argument("layout_name")
@click.option("--x", default=10.0, help="X position in mm.")
@click.option("--y", default=10.0, help="Y position in mm.")
def layout_add_legend(layout_name, x, y):
    """Add a legend item to a layout."""
    try:
        from cli_anything.qgis.core.layout import add_legend

        result = add_legend(layout_name, x=x, y=y)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@layout.command("add-scalebar")
@click.argument("layout_name")
@click.option("--x", default=10.0, help="X position in mm.")
@click.option("--y", default=10.0, help="Y position in mm.")
def layout_add_scalebar(layout_name, x, y):
    """Add a scale bar to a layout."""
    try:
        from cli_anything.qgis.core.layout import add_scalebar

        result = add_scalebar(layout_name, x=x, y=y)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@layout.command("add-label")
@click.argument("layout_name")
@click.argument("text")
@click.option("--x", default=10.0, help="X position in mm.")
@click.option("--y", default=10.0, help="Y position in mm.")
@click.option("--font-size", default=12, help="Font size.")
def layout_add_label(layout_name, text, x, y, font_size):
    """Add a text label to a layout."""
    try:
        from cli_anything.qgis.core.layout import add_label

        result = add_label(layout_name, text, x=x, y=y, font_size=font_size)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@layout.command("export-pdf")
@click.argument("layout_name")
@click.argument("output_path")
@click.option("--dpi", default=300, help="Resolution in DPI.")
def layout_export_pdf(layout_name, output_path, dpi):
    """Export a layout to PDF."""
    try:
        from cli_anything.qgis.core.layout import export_layout_pdf

        result = export_layout_pdf(layout_name, output_path, dpi=dpi)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


@layout.command("export-image")
@click.argument("layout_name")
@click.argument("output_path")
@click.option("--dpi", default=300, help="Resolution in DPI.")
def layout_export_image(layout_name, output_path, dpi):
    """Export a layout to an image (PNG, JPEG, etc.)."""
    try:
        from cli_anything.qgis.core.layout import export_layout_image

        result = export_layout_image(layout_name, output_path, dpi=dpi)
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


# ── Render commands ───────────────────────────────────────────────────


@cli.group()
def render():
    """Render — export map canvas to image."""
    pass


@render.command("map")
@click.argument("output_path")
@click.option("--width", "-w", default=1920, help="Image width in pixels.")
@click.option("--height", "-h", default=1080, help="Image height in pixels.")
@click.option("--dpi", default=96, help="Resolution in DPI.")
@click.option("--background", default="white", help="Background color.")
def render_map(output_path, width, height, dpi, background):
    """Render the current map to an image file."""
    try:
        from cli_anything.qgis.core.render import render_map as do_render

        result = do_render(
            output_path, width=width, height=height, dpi=dpi, background=background
        )
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


# ── Export commands ───────────────────────────────────────────────────


@cli.group()
def export():
    """Export — unified export pipeline for maps and layouts."""
    pass


@export.command("render")
@click.argument("output_path")
@click.option(
    "--preset",
    "-p",
    default="png",
    type=click.Choice(["png", "pdf", "svg", "jpeg", "tiff"]),
)
@click.option(
    "--layout", "layout_name", default=None, help="Layout name (for layout export)."
)
@click.option("--dpi", default=300, help="Resolution in DPI.")
@click.option("--width", default=1920, help="Image width (for map render).")
@click.option("--height", default=1080, help="Image height (for map render).")
@click.option("--overwrite", is_flag=True, help="Overwrite existing files.")
def export_render(output_path, preset, layout_name, dpi, width, height, overwrite):
    """Export a map or layout to a file."""
    try:
        from cli_anything.qgis.core.export import export as do_export

        result = do_export(
            output_path,
            preset=preset,
            layout_name=layout_name,
            dpi=dpi,
            width=width,
            height=height,
            overwrite=overwrite,
        )
        _output(result)
    except Exception as e:
        _error(e)
        sys.exit(1)


# ── Session commands ──────────────────────────────────────────────────


@cli.group()
def session():
    """Session — state management, undo/redo, history."""
    pass


@session.command("status")
def session_status():
    """Show current session status."""
    if _session:
        _output(_session.get_status())
    else:
        _error("No session active")


@session.command("history")
@click.option("--limit", "-l", default=10, help="Max entries to show.")
def session_history(limit):
    """Show recent operation history."""
    if _session:
        history = _session.get_history(limit=limit)
        _output({"action": "history", "entries": history})
    else:
        _error("No session active")


@session.command("undo")
def session_undo():
    """Undo the last operation."""
    if _session:
        result = _session.undo()
        _session.save()
        _output(result)
    else:
        _error("No session active")


@session.command("redo")
def session_redo():
    """Redo the last undone operation."""
    if _session:
        result = _session.redo()
        _session.save()
        _output(result)
    else:
        _error("No session active")


# ── REPL ──────────────────────────────────────────────────────────────


@cli.command(hidden=True)
@click.option("--project-path", default=None)
@click.pass_context
def repl(ctx, project_path):
    """Start an interactive REPL session."""
    from cli_anything.qgis.utils.repl_skin import ReplSkin

    skin = ReplSkin("qgis", version="1.0.0")
    skin.print_banner()

    pt_session = skin.create_prompt_session()

    # Commands available in REPL
    repl_commands = {
        "project new": "Create a new project",
        "project open": "Open an existing project",
        "project save": "Save the current project",
        "project info": "Show project information",
        "project close": "Close the current project",
        "layer add-vector": "Add a vector layer",
        "layer add-raster": "Add a raster layer",
        "layer remove": "Remove a layer",
        "layer list": "List all layers",
        "layer info": "Show layer details",
        "vector query": "Query features",
        "vector stats": "Compute field statistics",
        "vector count": "Count features",
        "raster info": "Show raster details",
        "raster stats": "Compute band statistics",
        "style single-symbol": "Apply single-symbol renderer",
        "style categorized": "Apply categorized renderer",
        "style graduated": "Apply graduated renderer",
        "style labels": "Enable labeling",
        "processing list": "List algorithms",
        "processing run": "Run an algorithm",
        "layout new": "Create a print layout",
        "layout list": "List layouts",
        "layout export-pdf": "Export layout to PDF",
        "render map": "Render map to image",
        "export render": "Unified export",
        "session status": "Show session status",
        "session undo": "Undo last operation",
        "session redo": "Redo last undone operation",
        "session history": "Show operation history",
        "help": "Show this help",
        "quit / exit": "Exit the REPL",
    }

    project_name = ""
    if project_path:
        project_name = os.path.basename(project_path)

    while True:
        try:
            modified = _session.state.get("modified", False) if _session else False
            line = skin.get_input(
                pt_session,
                project_name=project_name,
                modified=modified,
            )

            if not line:
                continue

            if line in ("quit", "exit", "q"):
                if _session:
                    _session.save()
                skin.print_goodbye()
                break

            if line == "help":
                skin.help(repl_commands)
                continue

            # Parse line as CLI args and invoke
            try:
                args = shlex.split(line)
            except ValueError as e:
                skin.error(f"Parse error: {e}")
                continue

            try:
                with cli.make_context("qgis", args, parent=ctx.parent) as sub_ctx:
                    cli.invoke(sub_ctx)
            except SystemExit:
                pass
            except click.UsageError as e:
                skin.error(str(e))
            except Exception as e:
                skin.error(str(e))

        except (KeyboardInterrupt, EOFError):
            if _session:
                _session.save()
            skin.print_goodbye()
            break


# ── Entry point ───────────────────────────────────────────────────────


def main():
    """Main entry point."""
    try:
        cli(standalone_mode=False)
    except SystemExit:
        pass
    except Exception as e:
        if _json_mode:
            click.echo(json.dumps({"error": str(e)}), err=True)
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    finally:
        from cli_anything.qgis.utils.qgis_backend import cleanup_qgis

        cleanup_qgis()


if __name__ == "__main__":
    main()
