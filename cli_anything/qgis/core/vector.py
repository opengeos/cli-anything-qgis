"""Vector layer operations — query features, filter, statistics, edit."""

import json
import os

from cli_anything.qgis.utils.qgis_backend import ensure_qgis


def _get_vector_layer(layer_id):
    """Get a vector layer by ID, raising if not found or wrong type."""
    from qgis.core import QgsProject, QgsVectorLayer

    project = QgsProject.instance()
    layer = project.mapLayer(layer_id)
    if not layer:
        raise ValueError(f"Layer not found: {layer_id}")
    if not isinstance(layer, QgsVectorLayer):
        raise TypeError(f"Layer {layer_id} is not a vector layer")
    return layer


def query_features(layer_id, expression=None, limit=100, fields=None):
    """Query features from a vector layer.

    Args:
        layer_id: The layer ID.
        expression: Optional QgsExpression filter string (e.g., '"name" = \'Paris\'').
        limit: Maximum features to return.
        fields: Optional list of field names to include. None = all fields.

    Returns:
        dict with feature list.
    """
    ensure_qgis()
    from qgis.core import QgsFeatureRequest

    layer = _get_vector_layer(layer_id)

    request = QgsFeatureRequest()
    if expression:
        request.setFilterExpression(expression)
    if limit:
        request.setLimit(limit)

    features = []
    for feat in layer.getFeatures(request):
        f = {"id": feat.id()}

        # Attributes
        attrs = {}
        for field in layer.fields():
            if fields and field.name() not in fields:
                continue
            val = feat[field.name()]
            # Convert QVariant NULL to None
            attrs[field.name()] = _sanitize_value(val)
        f["attributes"] = attrs

        # Geometry
        geom = feat.geometry()
        if not geom.isNull():
            f["geometry_type"] = (
                geom.type().name if hasattr(geom.type(), 'name') else str(geom.type())
            )
            f["geometry_wkt"] = geom.asWkt(precision=6)
        else:
            f["geometry_type"] = None
            f["geometry_wkt"] = None

        features.append(f)

    return {
        "action": "query",
        "layer_id": layer_id,
        "layer_name": layer.name(),
        "expression": expression,
        "count": len(features),
        "total_features": layer.featureCount(),
        "features": features,
    }


def field_statistics(layer_id, field_name):
    """Compute statistics for a field.

    Args:
        layer_id: The layer ID.
        field_name: Name of the field.

    Returns:
        dict with statistics.
    """
    ensure_qgis()
    from qgis.core import QgsStatisticalSummary

    layer = _get_vector_layer(layer_id)

    field_idx = layer.fields().indexFromName(field_name)
    if field_idx < 0:
        raise ValueError(f"Field not found: {field_name}")

    field = layer.fields().at(field_idx)

    # Collect values
    values = []
    for feat in layer.getFeatures():
        val = feat[field_name]
        if val is not None and str(val) != "NULL":
            values.append(val)

    result = {
        "action": "field_statistics",
        "layer_id": layer_id,
        "field_name": field_name,
        "field_type": field.typeName(),
        "total_count": layer.featureCount(),
        "non_null_count": len(values),
    }

    # Numeric statistics
    if field.isNumeric():
        numeric_vals = [float(v) for v in values if v is not None]
        if numeric_vals:
            result.update(
                {
                    "min": min(numeric_vals),
                    "max": max(numeric_vals),
                    "mean": sum(numeric_vals) / len(numeric_vals),
                    "sum": sum(numeric_vals),
                }
            )
    else:
        # String statistics: unique values
        unique = set(str(v) for v in values)
        result["unique_count"] = len(unique)
        if len(unique) <= 20:
            result["unique_values"] = sorted(unique)

    return result


def count_features(layer_id, expression=None):
    """Count features, optionally with a filter expression.

    Args:
        layer_id: The layer ID.
        expression: Optional filter expression.

    Returns:
        dict with count.
    """
    ensure_qgis()
    from qgis.core import QgsFeatureRequest

    layer = _get_vector_layer(layer_id)

    if expression:
        request = QgsFeatureRequest()
        request.setFilterExpression(expression)
        request.setFlags(QgsFeatureRequest.Flag.NoGeometry)
        count = 0
        for _ in layer.getFeatures(request):
            count += 1
    else:
        count = layer.featureCount()

    return {
        "action": "count",
        "layer_id": layer_id,
        "expression": expression,
        "count": count,
    }


def get_extent(layer_id):
    """Get the bounding box of a vector layer.

    Args:
        layer_id: The layer ID.

    Returns:
        dict with extent.
    """
    ensure_qgis()
    layer = _get_vector_layer(layer_id)
    extent = layer.extent()

    return {
        "action": "extent",
        "layer_id": layer_id,
        "xmin": extent.xMinimum(),
        "ymin": extent.yMinimum(),
        "xmax": extent.xMaximum(),
        "ymax": extent.yMaximum(),
        "crs": layer.crs().authid(),
    }


def _sanitize_value(val):
    """Convert QVariant / PyQt values to plain Python types."""
    if val is None:
        return None
    # Handle QVariant NULL
    try:
        from qgis.PyQt.QtCore import QVariant

        if isinstance(val, QVariant) and val.isNull():
            return None
    except ImportError:
        pass
    # Handle common types
    if isinstance(val, (int, float, str, bool)):
        return val
    return str(val)
