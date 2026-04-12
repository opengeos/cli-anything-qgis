"""Layer management — add, remove, list, info for map layers."""

import os

from cli_anything.qgis.utils.qgis_backend import ensure_qgis


def add_vector_layer(source, name=None, provider="ogr"):
    """Add a vector layer to the current project.

    Args:
        source: Data source URI (file path, database connection string, etc.).
        name: Display name for the layer. Defaults to filename.
        provider: Data provider key (ogr, postgres, spatialite, delimitedtext, etc.).

    Returns:
        dict with layer info.
    """
    ensure_qgis()
    from qgis.core import QgsProject, QgsVectorLayer

    source = os.path.abspath(source) if os.path.exists(source) else source

    if not name:
        name = os.path.splitext(os.path.basename(source.split("|")[0]))[0]

    layer = QgsVectorLayer(source, name, provider)
    if not layer.isValid():
        raise RuntimeError(
            f"Failed to load vector layer from: {source}\n" f"Provider: {provider}"
        )

    QgsProject.instance().addMapLayer(layer)

    return {
        "action": "add_vector_layer",
        "id": layer.id(),
        "name": layer.name(),
        "type": "vector",
        "geometry_type": _geometry_type_str(layer),
        "feature_count": layer.featureCount(),
        "crs": layer.crs().authid(),
        "source": layer.source(),
        "fields": [{"name": f.name(), "type": f.typeName()} for f in layer.fields()],
    }


def add_raster_layer(source, name=None, provider="gdal"):
    """Add a raster layer to the current project.

    Args:
        source: Data source path or URI.
        name: Display name. Defaults to filename.
        provider: Data provider (gdal, wms, etc.).

    Returns:
        dict with layer info.
    """
    ensure_qgis()
    from qgis.core import QgsProject, QgsRasterLayer

    source = os.path.abspath(source) if os.path.exists(source) else source

    if not name:
        name = os.path.splitext(os.path.basename(source.split("?")[0]))[0]

    layer = QgsRasterLayer(source, name, provider)
    if not layer.isValid():
        raise RuntimeError(
            f"Failed to load raster layer from: {source}\n" f"Provider: {provider}"
        )

    QgsProject.instance().addMapLayer(layer)

    return {
        "action": "add_raster_layer",
        "id": layer.id(),
        "name": layer.name(),
        "type": "raster",
        "width": layer.width(),
        "height": layer.height(),
        "band_count": layer.bandCount(),
        "crs": layer.crs().authid(),
        "extent": _extent_dict(layer.extent()),
        "source": layer.source(),
    }


def remove_layer(layer_id):
    """Remove a layer from the project by ID.

    Args:
        layer_id: The layer ID string.

    Returns:
        dict confirming removal.
    """
    ensure_qgis()
    from qgis.core import QgsProject

    project = QgsProject.instance()
    layer = project.mapLayer(layer_id)
    if not layer:
        raise ValueError(f"Layer not found: {layer_id}")

    name = layer.name()
    project.removeMapLayer(layer_id)

    return {
        "action": "remove_layer",
        "id": layer_id,
        "name": name,
    }


def list_layers():
    """List all layers in the current project.

    Returns:
        dict with layer list.
    """
    ensure_qgis()
    from qgis.core import QgsProject

    project = QgsProject.instance()
    layers = project.mapLayers()

    layer_list = []
    for layer_id, layer in layers.items():
        info = {
            "id": layer_id,
            "name": layer.name(),
            "type": _layer_type_str(layer),
            "valid": layer.isValid(),
            "crs": layer.crs().authid() if layer.crs().isValid() else None,
        }
        layer_list.append(info)

    return {
        "action": "list_layers",
        "count": len(layer_list),
        "layers": layer_list,
    }


def layer_info(layer_id):
    """Get detailed information about a specific layer.

    Args:
        layer_id: The layer ID string.

    Returns:
        dict with detailed layer info.
    """
    ensure_qgis()
    from qgis.core import QgsProject, QgsRasterLayer, QgsVectorLayer

    project = QgsProject.instance()
    layer = project.mapLayer(layer_id)
    if not layer:
        raise ValueError(f"Layer not found: {layer_id}")

    info = {
        "action": "layer_info",
        "id": layer_id,
        "name": layer.name(),
        "type": _layer_type_str(layer),
        "valid": layer.isValid(),
        "crs": layer.crs().authid() if layer.crs().isValid() else None,
        "extent": _extent_dict(layer.extent()),
        "source": layer.source(),
    }

    if isinstance(layer, QgsVectorLayer):
        info.update(
            {
                "geometry_type": _geometry_type_str(layer),
                "feature_count": layer.featureCount(),
                "fields": [
                    {"name": f.name(), "type": f.typeName(), "length": f.length()}
                    for f in layer.fields()
                ],
            }
        )
    elif isinstance(layer, QgsRasterLayer):
        info.update(
            {
                "width": layer.width(),
                "height": layer.height(),
                "band_count": layer.bandCount(),
            }
        )

    return info


def _layer_type_str(layer):
    """Convert layer type enum to string."""
    from qgis.core import Qgis

    type_map = {
        Qgis.LayerType.Vector: "vector",
        Qgis.LayerType.Raster: "raster",
        Qgis.LayerType.Mesh: "mesh",
        Qgis.LayerType.PointCloud: "pointcloud",
        Qgis.LayerType.VectorTile: "vectortile",
    }
    try:
        return type_map.get(layer.type(), "unknown")
    except Exception:
        return "unknown"


def _geometry_type_str(layer):
    """Get geometry type as string for a vector layer."""
    from qgis.core import Qgis

    geom_map = {
        Qgis.GeometryType.Point: "point",
        Qgis.GeometryType.Line: "line",
        Qgis.GeometryType.Polygon: "polygon",
        Qgis.GeometryType.Null: "null",
        Qgis.GeometryType.Unknown: "unknown",
    }
    try:
        return geom_map.get(layer.geometryType(), "unknown")
    except Exception:
        return "unknown"


def _extent_dict(extent):
    """Convert QgsRectangle to dict."""
    return {
        "xmin": extent.xMinimum(),
        "ymin": extent.yMinimum(),
        "xmax": extent.xMaximum(),
        "ymax": extent.yMaximum(),
    }
