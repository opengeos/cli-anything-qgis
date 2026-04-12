"""Map rendering — headless map canvas rendering to images."""

import os

from cli_anything.qgis.utils.qgis_backend import ensure_qgis


def render_map(
    output_path,
    width=1920,
    height=1080,
    dpi=96,
    extent=None,
    crs=None,
    layers=None,
    background="white",
):
    """Render the current map to an image file.

    Args:
        output_path: Output image path (PNG, JPEG, TIFF, etc.).
        width: Image width in pixels.
        height: Image height in pixels.
        dpi: Resolution in DPI.
        extent: Optional extent dict {xmin, ymin, xmax, ymax}.
        crs: Optional CRS string (e.g., 'EPSG:4326').
        layers: Optional list of layer IDs to render. None = all layers.
        background: Background color name or hex.

    Returns:
        dict with render result.
    """
    ensure_qgis()
    from qgis.core import (
        QgsCoordinateReferenceSystem,
        QgsMapRendererSequentialJob,
        QgsMapSettings,
        QgsProject,
        QgsRectangle,
    )
    from qgis.PyQt.QtCore import QSize
    from qgis.PyQt.QtGui import QColor, QImage

    project = QgsProject.instance()
    output_path = os.path.abspath(output_path)
    (
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if os.path.dirname(output_path)
        else None
    )

    # Get layers to render
    if layers:
        render_layers = []
        for lid in layers:
            lyr = project.mapLayer(lid)
            if lyr:
                render_layers.append(lyr)
    else:
        render_layers = list(project.mapLayers().values())

    if not render_layers:
        raise RuntimeError("No layers available to render")

    # Configure map settings
    settings = QgsMapSettings()
    settings.setOutputSize(QSize(width, height))
    settings.setOutputDpi(dpi)
    settings.setLayers(render_layers)
    settings.setBackgroundColor(QColor(background))

    # Set CRS
    if crs:
        map_crs = QgsCoordinateReferenceSystem(crs)
        if map_crs.isValid():
            settings.setDestinationCrs(map_crs)
    else:
        settings.setDestinationCrs(project.crs())

    # Set extent
    if extent:
        settings.setExtent(
            QgsRectangle(
                extent["xmin"],
                extent["ymin"],
                extent["xmax"],
                extent["ymax"],
            )
        )
    else:
        # Compute full extent from all layers
        full_extent = render_layers[0].extent()
        for lyr in render_layers[1:]:
            full_extent.combineExtentWith(lyr.extent())
        settings.setExtent(full_extent)

    # Render
    job = QgsMapRendererSequentialJob(settings)
    job.start()
    job.waitForFinished()

    image = job.renderedImage()
    if image.isNull():
        raise RuntimeError("Rendering produced a null image")

    success = image.save(output_path)
    if not success:
        raise RuntimeError(f"Failed to save rendered image to: {output_path}")

    file_size = os.path.getsize(output_path)

    return {
        "action": "render_map",
        "output": output_path,
        "width": width,
        "height": height,
        "dpi": dpi,
        "layer_count": len(render_layers),
        "file_size": file_size,
    }
