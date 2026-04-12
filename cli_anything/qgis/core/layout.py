"""Layout management — create print layouts, add items, export."""

import os

from cli_anything.qgis.utils.qgis_backend import ensure_qgis


def create_layout(name="Layout 1", page_size="A4", orientation="landscape"):
    """Create a new print layout.

    Args:
        name: Layout name.
        page_size: Page size (A4, A3, Letter, etc.).
        orientation: 'landscape' or 'portrait'.

    Returns:
        dict with layout info.
    """
    ensure_qgis()
    from qgis.core import QgsLayoutSize, QgsPrintLayout, QgsProject, QgsUnitTypes

    project = QgsProject.instance()
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName(name)

    # Set page size
    page_sizes = {
        "A4": (210, 297),
        "A3": (297, 420),
        "A2": (420, 594),
        "A1": (594, 841),
        "A0": (841, 1189),
        "Letter": (215.9, 279.4),
        "Legal": (215.9, 355.6),
        "Tabloid": (279.4, 431.8),
    }

    dims = page_sizes.get(page_size, page_sizes["A4"])
    if orientation == "landscape":
        w, h = max(dims), min(dims)
    else:
        w, h = min(dims), max(dims)

    page = layout.pageCollection().page(0)
    page.setPageSize(QgsLayoutSize(w, h, QgsUnitTypes.LayoutUnit.LayoutMillimeters))

    # Register with project
    project.layoutManager().addLayout(layout)

    return {
        "action": "create_layout",
        "name": name,
        "page_size": page_size,
        "orientation": orientation,
        "width_mm": w,
        "height_mm": h,
    }


def list_layouts():
    """List all print layouts in the current project.

    Returns:
        dict with layout list.
    """
    ensure_qgis()
    from qgis.core import QgsProject

    manager = QgsProject.instance().layoutManager()
    layouts = []

    for layout in manager.layouts():
        page = layout.pageCollection().page(0)
        layouts.append(
            {
                "name": layout.name(),
                "page_count": layout.pageCollection().pageCount(),
                "width_mm": page.pageSize().width() if page else 0,
                "height_mm": page.pageSize().height() if page else 0,
            }
        )

    return {
        "action": "list_layouts",
        "count": len(layouts),
        "layouts": layouts,
    }


def add_map(layout_name, x=10, y=10, width=None, height=None, extent=None):
    """Add a map item to a layout.

    Args:
        layout_name: Name of the layout.
        x: X position in mm.
        y: Y position in mm.
        width: Width in mm. Default: page width minus margins.
        height: Height in mm. Default: page height minus margins.
        extent: Optional extent dict {xmin, ymin, xmax, ymax}.

    Returns:
        dict with map item info.
    """
    ensure_qgis()
    from qgis.core import QgsLayout, QgsLayoutItemMap, QgsProject, QgsRectangle
    from qgis.PyQt.QtCore import QRectF

    layout = _get_layout(layout_name)
    page = layout.pageCollection().page(0)

    if width is None:
        width = page.pageSize().width() - 2 * x
    if height is None:
        height = page.pageSize().height() - 2 * y

    map_item = QgsLayoutItemMap(layout)
    map_item.attemptSetSceneRect(QRectF(x, y, width, height))

    if extent:
        map_item.setExtent(
            QgsRectangle(extent["xmin"], extent["ymin"], extent["xmax"], extent["ymax"])
        )
    else:
        # Use project full extent
        project = QgsProject.instance()
        layers = list(project.mapLayers().values())
        if layers:
            full_extent = layers[0].extent()
            for lyr in layers[1:]:
                full_extent.combineExtentWith(lyr.extent())
            map_item.setExtent(full_extent)

    layout.addLayoutItem(map_item)

    return {
        "action": "add_map",
        "layout": layout_name,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
    }


def add_legend(layout_name, x=10, y=10, width=40, height=60):
    """Add a legend item to a layout.

    Args:
        layout_name: Name of the layout.
        x, y: Position in mm.
        width, height: Size in mm.

    Returns:
        dict confirming legend addition.
    """
    ensure_qgis()
    from qgis.core import QgsLayoutItemLegend
    from qgis.PyQt.QtCore import QRectF

    layout = _get_layout(layout_name)

    legend = QgsLayoutItemLegend(layout)
    legend.attemptSetSceneRect(QRectF(x, y, width, height))
    layout.addLayoutItem(legend)

    return {
        "action": "add_legend",
        "layout": layout_name,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
    }


def add_scalebar(layout_name, x=10, y=10, width=60, height=15):
    """Add a scale bar item to a layout.

    Args:
        layout_name: Name of the layout.
        x, y: Position in mm.
        width, height: Size in mm.

    Returns:
        dict confirming scalebar addition.
    """
    ensure_qgis()
    from qgis.core import QgsLayoutItemScaleBar
    from qgis.PyQt.QtCore import QRectF

    layout = _get_layout(layout_name)

    scalebar = QgsLayoutItemScaleBar(layout)
    scalebar.attemptSetSceneRect(QRectF(x, y, width, height))

    # Link to first map item if available
    map_items = [item for item in layout.items() if hasattr(item, 'setExtent')]
    if map_items:
        scalebar.setLinkedMap(map_items[0])

    layout.addLayoutItem(scalebar)

    return {
        "action": "add_scalebar",
        "layout": layout_name,
        "x": x,
        "y": y,
    }


def add_label(layout_name, text, x=10, y=10, width=100, height=20, font_size=12):
    """Add a text label to a layout.

    Args:
        layout_name: Name of the layout.
        text: Label text content.
        x, y: Position in mm.
        width, height: Size in mm.
        font_size: Font size in points.

    Returns:
        dict confirming label addition.
    """
    ensure_qgis()
    from qgis.core import QgsLayoutItemLabel
    from qgis.PyQt.QtCore import QRectF
    from qgis.PyQt.QtGui import QFont

    layout = _get_layout(layout_name)

    label = QgsLayoutItemLabel(layout)
    label.setText(text)
    label.attemptSetSceneRect(QRectF(x, y, width, height))
    label.setFont(QFont("Arial", font_size))
    layout.addLayoutItem(label)

    return {
        "action": "add_label",
        "layout": layout_name,
        "text": text,
        "x": x,
        "y": y,
    }


def export_layout_pdf(layout_name, output_path, dpi=300):
    """Export a layout to PDF.

    Args:
        layout_name: Name of the layout.
        output_path: Output PDF file path.
        dpi: Resolution in dots per inch.

    Returns:
        dict with export result.
    """
    ensure_qgis()
    from qgis.core import QgsLayoutExporter

    layout = _get_layout(layout_name)
    output_path = os.path.abspath(output_path)
    (
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if os.path.dirname(output_path)
        else None
    )

    exporter = QgsLayoutExporter(layout)
    settings = QgsLayoutExporter.PdfExportSettings()
    settings.dpi = dpi

    result = exporter.exportToPdf(output_path, settings)

    if result != QgsLayoutExporter.ExportResult.Success:
        raise RuntimeError(f"PDF export failed with code: {result}")

    file_size = os.path.getsize(output_path)
    return {
        "action": "export_pdf",
        "layout": layout_name,
        "output": output_path,
        "dpi": dpi,
        "file_size": file_size,
    }


def export_layout_image(layout_name, output_path, dpi=300):
    """Export a layout to an image (PNG, JPEG, etc.).

    Args:
        layout_name: Name of the layout.
        output_path: Output image file path.
        dpi: Resolution in dots per inch.

    Returns:
        dict with export result.
    """
    ensure_qgis()
    from qgis.core import QgsLayoutExporter

    layout = _get_layout(layout_name)
    output_path = os.path.abspath(output_path)
    (
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if os.path.dirname(output_path)
        else None
    )

    exporter = QgsLayoutExporter(layout)
    settings = QgsLayoutExporter.ImageExportSettings()
    settings.dpi = dpi

    result = exporter.exportToImage(output_path, settings)

    if result != QgsLayoutExporter.ExportResult.Success:
        raise RuntimeError(f"Image export failed with code: {result}")

    file_size = os.path.getsize(output_path)
    return {
        "action": "export_image",
        "layout": layout_name,
        "output": output_path,
        "dpi": dpi,
        "file_size": file_size,
    }


def export_layout_svg(layout_name, output_path, dpi=300):
    """Export a layout to SVG.

    Args:
        layout_name: Name of the layout.
        output_path: Output SVG file path.
        dpi: Resolution in dots per inch.

    Returns:
        dict with export result.
    """
    ensure_qgis()
    from qgis.core import QgsLayoutExporter

    layout = _get_layout(layout_name)
    output_path = os.path.abspath(output_path)
    (
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if os.path.dirname(output_path)
        else None
    )

    exporter = QgsLayoutExporter(layout)
    settings = QgsLayoutExporter.SvgExportSettings()
    settings.dpi = dpi

    result = exporter.exportToSvg(output_path, settings)

    if result != QgsLayoutExporter.ExportResult.Success:
        raise RuntimeError(f"SVG export failed with code: {result}")

    file_size = os.path.getsize(output_path)
    return {
        "action": "export_svg",
        "layout": layout_name,
        "output": output_path,
        "dpi": dpi,
        "file_size": file_size,
    }


def _get_layout(name):
    """Get a layout by name."""
    from qgis.core import QgsProject

    manager = QgsProject.instance().layoutManager()
    layout = manager.layoutByName(name)
    if not layout:
        available = [l.name() for l in manager.layouts()]
        raise ValueError(
            f"Layout not found: {name}. "
            f"Available: {', '.join(available) if available else '(none)'}"
        )
    return layout
