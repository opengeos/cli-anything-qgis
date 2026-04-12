"""Export pipeline — unified export interface for maps and layouts."""

import os

from cli_anything.qgis.utils.qgis_backend import ensure_qgis


def export(
    output_path,
    preset="png",
    layout_name=None,
    dpi=300,
    width=1920,
    height=1080,
    extent=None,
    overwrite=False,
):
    """Unified export command — renders a map or layout to a file.

    Args:
        output_path: Output file path.
        preset: Export preset/format ('png', 'pdf', 'svg', 'jpeg', 'tiff').
        layout_name: If specified, exports the named layout. Otherwise renders
                     the map canvas.
        dpi: Resolution for layout exports.
        width: Image width for map renders (pixels).
        height: Image height for map renders (pixels).
        extent: Optional extent dict {xmin, ymin, xmax, ymax}.
        overwrite: If True, overwrite existing files.

    Returns:
        dict with export result.
    """
    output_path = os.path.abspath(output_path)

    if os.path.exists(output_path) and not overwrite:
        raise FileExistsError(
            f"Output file already exists: {output_path}. " "Use --overwrite to replace."
        )

    if layout_name:
        return _export_layout(layout_name, output_path, preset, dpi)
    else:
        return _export_map(output_path, preset, width, height, dpi, extent)


def _export_layout(layout_name, output_path, preset, dpi):
    """Export a print layout."""
    from cli_anything.qgis.core.layout import (
        export_layout_image,
        export_layout_pdf,
        export_layout_svg,
    )

    preset = preset.lower()
    if preset == "pdf":
        return export_layout_pdf(layout_name, output_path, dpi=dpi)
    elif preset == "svg":
        return export_layout_svg(layout_name, output_path, dpi=dpi)
    else:
        return export_layout_image(layout_name, output_path, dpi=dpi)


def _export_map(output_path, preset, width, height, dpi, extent):
    """Export the map canvas as an image."""
    from cli_anything.qgis.core.render import render_map

    return render_map(
        output_path,
        width=width,
        height=height,
        dpi=dpi,
        extent=extent,
    )
