"""Project management — create, open, save, info for QGIS projects."""

import json
import os
import time

from cli_anything.qgis.utils.qgis_backend import ensure_qgis


def create_project(output_path=None, title="", crs="EPSG:4326"):
    """Create a new QGIS project.

    Args:
        output_path: Path to save the project (.qgs or .qgz). If None, creates
                     in-memory only.
        title: Project title metadata.
        crs: Coordinate reference system (default EPSG:4326 / WGS 84).

    Returns:
        dict with project info.
    """
    ensure_qgis()
    from qgis.core import QgsCoordinateReferenceSystem, QgsProject

    project = QgsProject.instance()
    project.clear()

    if title:
        project.setTitle(title)

    project_crs = QgsCoordinateReferenceSystem(crs)
    if project_crs.isValid():
        project.setCrs(project_crs)

    result = {
        "action": "create",
        "title": title or "(untitled)",
        "crs": crs,
        "layer_count": 0,
    }

    if output_path:
        output_path = os.path.abspath(output_path)
        (
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            if os.path.dirname(output_path)
            else None
        )
        success = project.write(output_path)
        if not success:
            raise RuntimeError(f"Failed to write project to {output_path}")
        result["output"] = output_path
        result["file_size"] = os.path.getsize(output_path)

    return result


def open_project(project_path):
    """Open an existing QGIS project.

    Args:
        project_path: Path to .qgs or .qgz file.

    Returns:
        dict with project info.
    """
    ensure_qgis()
    from qgis.core import QgsProject

    project_path = os.path.abspath(project_path)
    if not os.path.exists(project_path):
        raise FileNotFoundError(f"Project not found: {project_path}")

    project = QgsProject.instance()
    success = project.read(project_path)
    if not success:
        raise RuntimeError(f"Failed to open project: {project_path}")

    layers = project.mapLayers()
    layer_list = []
    for layer_id, layer in layers.items():
        layer_list.append(
            {
                "id": layer_id,
                "name": layer.name(),
                "type": _layer_type_str(layer),
                "source": layer.source(),
                "valid": layer.isValid(),
            }
        )

    return {
        "action": "open",
        "path": project_path,
        "title": project.title() or "(untitled)",
        "crs": project.crs().authid(),
        "layer_count": len(layers),
        "layers": layer_list,
    }


def save_project(output_path=None):
    """Save the current project.

    Args:
        output_path: Path to save to. If None, saves to the current file.

    Returns:
        dict with save result.
    """
    ensure_qgis()
    from qgis.core import QgsProject

    project = QgsProject.instance()

    if output_path:
        output_path = os.path.abspath(output_path)
        (
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            if os.path.dirname(output_path)
            else None
        )
        success = project.write(output_path)
    else:
        if not project.fileName():
            raise RuntimeError("No project file set. Use --output to specify a path.")
        output_path = project.fileName()
        success = project.write()

    if not success:
        raise RuntimeError(f"Failed to save project to {output_path}")

    return {
        "action": "save",
        "output": output_path,
        "file_size": os.path.getsize(output_path),
    }


def project_info(project_path=None):
    """Get information about the current or specified project.

    Args:
        project_path: Optional path to a project file. If None, uses current.

    Returns:
        dict with detailed project info.
    """
    ensure_qgis()
    from qgis.core import QgsProject

    project = QgsProject.instance()

    if project_path:
        project_path = os.path.abspath(project_path)
        if not os.path.exists(project_path):
            raise FileNotFoundError(f"Project not found: {project_path}")
        project.read(project_path)

    layers = project.mapLayers()
    layer_list = []
    vector_count = 0
    raster_count = 0

    for layer_id, layer in layers.items():
        ltype = _layer_type_str(layer)
        if ltype == "vector":
            vector_count += 1
        elif ltype == "raster":
            raster_count += 1
        layer_list.append(
            {
                "id": layer_id,
                "name": layer.name(),
                "type": ltype,
                "source": layer.source(),
                "valid": layer.isValid(),
                "crs": layer.crs().authid() if layer.crs().isValid() else None,
            }
        )

    file_path = project.fileName() or project_path
    return {
        "action": "info",
        "path": file_path,
        "title": project.title() or "(untitled)",
        "crs": project.crs().authid(),
        "layer_count": len(layers),
        "vector_layers": vector_count,
        "raster_layers": raster_count,
        "layers": layer_list,
        "file_size": (
            os.path.getsize(file_path)
            if file_path and os.path.exists(file_path)
            else None
        ),
    }


def close_project():
    """Close the current project (clear all layers and state).

    Returns:
        dict confirming closure.
    """
    ensure_qgis()
    from qgis.core import QgsProject

    project = QgsProject.instance()
    prev_path = project.fileName()
    project.clear()

    return {
        "action": "close",
        "previous_path": prev_path or None,
    }


def _layer_type_str(layer):
    """Convert QgsMapLayer type to string."""
    from qgis.core import Qgis

    type_map = {
        Qgis.LayerType.Vector: "vector",
        Qgis.LayerType.Raster: "raster",
        Qgis.LayerType.Mesh: "mesh",
        Qgis.LayerType.PointCloud: "pointcloud",
        Qgis.LayerType.VectorTile: "vectortile",
        Qgis.LayerType.Group: "group",
    }
    try:
        return type_map.get(layer.type(), "unknown")
    except Exception:
        return "unknown"
