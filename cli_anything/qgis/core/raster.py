"""Raster layer operations — info, statistics, band info."""

from cli_anything.qgis.utils.qgis_backend import ensure_qgis


def _get_raster_layer(layer_id):
    """Get a raster layer by ID."""
    from qgis.core import QgsProject, QgsRasterLayer

    project = QgsProject.instance()
    layer = project.mapLayer(layer_id)
    if not layer:
        raise ValueError(f"Layer not found: {layer_id}")
    if not isinstance(layer, QgsRasterLayer):
        raise TypeError(f"Layer {layer_id} is not a raster layer")
    return layer


def raster_info(layer_id):
    """Get detailed raster layer information.

    Args:
        layer_id: The layer ID.

    Returns:
        dict with raster details.
    """
    ensure_qgis()
    layer = _get_raster_layer(layer_id)

    bands = []
    provider = layer.dataProvider()
    for i in range(1, layer.bandCount() + 1):
        band_info = {
            "band": i,
            "name": provider.generateBandName(i) if provider else f"Band {i}",
        }
        bands.append(band_info)

    extent = layer.extent()
    return {
        "action": "raster_info",
        "id": layer_id,
        "name": layer.name(),
        "width": layer.width(),
        "height": layer.height(),
        "band_count": layer.bandCount(),
        "bands": bands,
        "crs": layer.crs().authid() if layer.crs().isValid() else None,
        "extent": {
            "xmin": extent.xMinimum(),
            "ymin": extent.yMinimum(),
            "xmax": extent.xMaximum(),
            "ymax": extent.yMaximum(),
        },
        "pixel_size_x": layer.rasterUnitsPerPixelX(),
        "pixel_size_y": layer.rasterUnitsPerPixelY(),
        "source": layer.source(),
    }


def band_statistics(layer_id, band=1):
    """Compute statistics for a raster band.

    Args:
        layer_id: The layer ID.
        band: Band number (1-based).

    Returns:
        dict with band statistics.
    """
    ensure_qgis()
    from qgis.core import QgsRasterBandStats

    layer = _get_raster_layer(layer_id)

    if band < 1 or band > layer.bandCount():
        raise ValueError(f"Band {band} out of range (1-{layer.bandCount()})")

    provider = layer.dataProvider()
    stats = provider.bandStatistics(band, stats=QgsRasterBandStats.Stats.All)

    return {
        "action": "band_statistics",
        "layer_id": layer_id,
        "band": band,
        "min": stats.minimumValue,
        "max": stats.maximumValue,
        "mean": stats.mean,
        "std_dev": stats.stdDev,
        "sum": stats.sum,
        "range": stats.range,
    }
