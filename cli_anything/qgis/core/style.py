"""Styling operations — renderers, classification, labeling."""

from cli_anything.qgis.utils.qgis_backend import ensure_qgis


def _get_vector_layer(layer_id):
    """Get a vector layer by ID."""
    from qgis.core import QgsProject, QgsVectorLayer

    layer = QgsProject.instance().mapLayer(layer_id)
    if not layer:
        raise ValueError(f"Layer not found: {layer_id}")
    if not isinstance(layer, QgsVectorLayer):
        raise TypeError(f"Layer {layer_id} is not a vector layer")
    return layer


def apply_single_symbol(layer_id, color="blue", opacity=1.0):
    """Apply a single-symbol renderer to a vector layer.

    Args:
        layer_id: The layer ID.
        color: Color name or hex string (e.g., 'red', '#ff0000').
        opacity: Opacity from 0.0 to 1.0.

    Returns:
        dict confirming the style change.
    """
    ensure_qgis()
    from qgis.core import (
        QgsSimpleFillSymbolLayer,
        QgsSimpleLineSymbolLayer,
        QgsSimpleMarkerSymbolLayer,
        QgsSingleSymbolRenderer,
        QgsSymbol,
    )
    from qgis.PyQt.QtGui import QColor

    layer = _get_vector_layer(layer_id)
    geom_type = layer.geometryType()

    from qgis.core import Qgis

    if geom_type == Qgis.GeometryType.Point:
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    elif geom_type == Qgis.GeometryType.Line:
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    else:
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())

    symbol.setColor(QColor(color))
    symbol.setOpacity(opacity)

    renderer = QgsSingleSymbolRenderer(symbol)
    layer.setRenderer(renderer)
    layer.triggerRepaint()

    return {
        "action": "apply_single_symbol",
        "layer_id": layer_id,
        "color": color,
        "opacity": opacity,
    }


def apply_categorized(layer_id, field_name, color_ramp="Spectral"):
    """Apply a categorized renderer based on a field's unique values.

    Args:
        layer_id: The layer ID.
        field_name: The field to categorize by.
        color_ramp: Name of the color ramp to use.

    Returns:
        dict with category details.
    """
    ensure_qgis()
    from qgis.core import (
        QgsCategorizedSymbolRenderer,
        QgsRendererCategory,
        QgsStyle,
        QgsSymbol,
    )
    from qgis.PyQt.QtGui import QColor

    layer = _get_vector_layer(layer_id)

    # Get unique values
    field_idx = layer.fields().indexFromName(field_name)
    if field_idx < 0:
        raise ValueError(f"Field not found: {field_name}")

    unique_values = sorted(
        set(
            str(feat[field_name])
            for feat in layer.getFeatures()
            if feat[field_name] is not None and str(feat[field_name]) != "NULL"
        )
    )

    # Get color ramp
    style = QgsStyle.defaultStyle()
    ramp = style.colorRamp(color_ramp)
    if not ramp:
        available = style.colorRampNames()[:10]
        raise ValueError(
            f"Color ramp '{color_ramp}' not found. "
            f"Available: {', '.join(available)}..."
        )

    # Build categories
    categories = []
    for i, value in enumerate(unique_values):
        fraction = i / max(len(unique_values) - 1, 1)
        color = ramp.color(fraction)
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol.setColor(color)
        cat = QgsRendererCategory(value, symbol, str(value))
        categories.append(cat)

    renderer = QgsCategorizedSymbolRenderer(field_name, categories)
    layer.setRenderer(renderer)
    layer.triggerRepaint()

    return {
        "action": "apply_categorized",
        "layer_id": layer_id,
        "field": field_name,
        "color_ramp": color_ramp,
        "category_count": len(categories),
        "categories": [str(v) for v in unique_values],
    }


def apply_graduated(
    layer_id, field_name, classes=5, mode="equal_interval", color_ramp="Reds"
):
    """Apply a graduated renderer for numeric fields.

    Args:
        layer_id: The layer ID.
        field_name: Numeric field to classify.
        classes: Number of classes.
        mode: Classification mode: 'equal_interval', 'quantile', 'natural_breaks'.
        color_ramp: Color ramp name.

    Returns:
        dict with classification details.
    """
    ensure_qgis()
    from qgis.core import (
        QgsClassificationEqualInterval,
        QgsClassificationQuantile,
        QgsGraduatedSymbolRenderer,
        QgsRendererRange,
        QgsStyle,
        QgsSymbol,
    )

    layer = _get_vector_layer(layer_id)

    field_idx = layer.fields().indexFromName(field_name)
    if field_idx < 0:
        raise ValueError(f"Field not found: {field_name}")

    # Create graduated renderer
    renderer = QgsGraduatedSymbolRenderer(field_name)

    # Set classification method
    if mode == "quantile":
        method = QgsClassificationQuantile()
    else:
        method = QgsClassificationEqualInterval()

    renderer.setClassificationMethod(method)

    # Set color ramp
    style = QgsStyle.defaultStyle()
    ramp = style.colorRamp(color_ramp)
    if ramp:
        renderer.setSourceColorRamp(ramp)

    renderer.updateClasses(layer, classes)
    layer.setRenderer(renderer)
    layer.triggerRepaint()

    # Collect class info
    ranges = []
    for r in renderer.ranges():
        ranges.append(
            {
                "lower": r.lowerValue(),
                "upper": r.upperValue(),
                "label": r.label(),
            }
        )

    return {
        "action": "apply_graduated",
        "layer_id": layer_id,
        "field": field_name,
        "classes": classes,
        "mode": mode,
        "color_ramp": color_ramp,
        "ranges": ranges,
    }


def apply_labels(layer_id, field_name, font_size=10, color="black"):
    """Enable labeling on a vector layer.

    Args:
        layer_id: The layer ID.
        field_name: Field to use for label text.
        font_size: Font size in points.
        color: Label text color.

    Returns:
        dict confirming label setup.
    """
    ensure_qgis()
    from qgis.core import (
        QgsPalLayerSettings,
        QgsTextFormat,
        QgsVectorLayerSimpleLabeling,
    )
    from qgis.PyQt.QtGui import QColor, QFont

    layer = _get_vector_layer(layer_id)

    settings = QgsPalLayerSettings()
    settings.fieldName = field_name
    settings.isExpression = False

    text_format = QgsTextFormat()
    text_format.setFont(QFont("Arial", font_size))
    text_format.setSize(font_size)
    text_format.setColor(QColor(color))
    settings.setFormat(text_format)

    labeling = QgsVectorLayerSimpleLabeling(settings)
    layer.setLabeling(labeling)
    layer.setLabelsEnabled(True)
    layer.triggerRepaint()

    return {
        "action": "apply_labels",
        "layer_id": layer_id,
        "field": field_name,
        "font_size": font_size,
        "color": color,
    }


def load_style(layer_id, qml_path):
    """Load a QML style file onto a layer.

    Args:
        layer_id: The layer ID.
        qml_path: Path to .qml style file.

    Returns:
        dict confirming style load.
    """
    ensure_qgis()
    import os
    from qgis.core import QgsProject

    layer = QgsProject.instance().mapLayer(layer_id)
    if not layer:
        raise ValueError(f"Layer not found: {layer_id}")

    qml_path = os.path.abspath(qml_path)
    if not os.path.exists(qml_path):
        raise FileNotFoundError(f"Style file not found: {qml_path}")

    msg, success = layer.loadNamedStyle(qml_path)
    if not success:
        raise RuntimeError(f"Failed to load style: {msg}")

    layer.triggerRepaint()

    return {
        "action": "load_style",
        "layer_id": layer_id,
        "qml_path": qml_path,
    }


def save_style(layer_id, qml_path):
    """Save a layer's current style to a QML file.

    Args:
        layer_id: The layer ID.
        qml_path: Output path for .qml file.

    Returns:
        dict confirming style save.
    """
    ensure_qgis()
    import os
    from qgis.core import QgsProject

    layer = QgsProject.instance().mapLayer(layer_id)
    if not layer:
        raise ValueError(f"Layer not found: {layer_id}")

    qml_path = os.path.abspath(qml_path)
    msg, success = layer.saveNamedStyle(qml_path)
    if not success:
        raise RuntimeError(f"Failed to save style: {msg}")

    return {
        "action": "save_style",
        "layer_id": layer_id,
        "qml_path": qml_path,
        "file_size": os.path.getsize(qml_path),
    }
