# QGIS — Agent Harness SOP

## Software Overview

**QGIS** is a free, open-source Geographic Information System (GIS) for creating,
editing, visualizing, analysing, and publishing geospatial data. It runs on Linux,
macOS, and Windows.

## Backend Engine

- **Core library**: `libqgis_core` (C++ with SIP-generated Python bindings via PyQGIS)
- **Python API**: `qgis.core`, `qgis.gui`, `qgis.analysis`, `qgis.processing`
- **Headless mode**: `QgsApplication([], False)` — no GUI, full API access
- **Processing framework**: 200+ native algorithms plus GDAL, SAGA, GRASS providers
- **Existing CLI**: `qgis_process` — runs processing algorithms from command line

## GUI-to-API Mapping

| GUI Action | API Call |
|------------|----------|
| File > New Project | `QgsProject.instance().clear()` |
| File > Open Project | `QgsProject.instance().read(path)` |
| File > Save Project | `QgsProject.instance().write(path)` |
| Layer > Add Vector Layer | `QgsVectorLayer(uri, name, provider)` |
| Layer > Add Raster Layer | `QgsRasterLayer(uri, name, provider)` |
| Layer > Remove Layer | `QgsProject.instance().removeMapLayer(id)` |
| View > Zoom to Full Extent | `QgsMapSettings.setExtent(fullExtent)` |
| Processing > Run Algorithm | `processing.run(alg_id, params)` |
| Project > New Print Layout | `QgsLayout(QgsProject.instance())` |
| Layout > Export as PDF | `QgsLayoutExporter.exportToPdf(path, settings)` |
| Layout > Export as Image | `QgsLayoutExporter.exportToImage(path, settings)` |
| Map Canvas > Save as Image | `QgsMapRendererSequentialJob` → `QImage.save()` |
| Layer > Properties > Style | `QgsSymbol`, `QgsRenderer` classes |
| Layer > Properties > Labels | `QgsPalLayerSettings`, `QgsVectorLayerSimpleLabeling` |

## Data Model

- **Project file**: `.qgs` (XML) or `.qgz` (ZIP containing `.qgs` + auxiliary files)
- **Vector formats**: GeoPackage, Shapefile, GeoJSON, PostGIS, CSV, KML, etc.
- **Raster formats**: GeoTIFF, JPEG, PNG, NetCDF, GRIB, etc.
- **Styles**: QML (XML-based style definition files)
- **Processing models**: `.model3` (JSON-based model definitions)

## CLI Architecture

### Command Groups

1. **project** — Create, open, save, info, close projects
2. **layer** — Add, remove, list, info for vector/raster layers
3. **vector** — Query features, filter, statistics, edit attributes
4. **raster** — Band info, statistics, histogram
5. **style** — Apply renderers, classification, graduated/categorized styles
6. **processing** — List and run processing algorithms
7. **layout** — Create layouts, add map/legend/scalebar, export PDF/PNG/SVG
8. **render** — Render map to image (headless map canvas export)
9. **export** — General export pipeline (delegates to layout/render)
10. **session** — Undo/redo, status, history

### State Model

- Session JSON tracks: project path, loaded layers, current extent, modifications
- QgsApplication singleton managed per-process for REPL
- File-based session for CLI one-shot mode

### Backend Integration

The CLI uses QGIS's Python API directly (not a subprocess wrapper):
1. Initialize `QgsApplication` in headless mode
2. Use `QgsProject`, `QgsVectorLayer`, `QgsRasterLayer` for data operations
3. Use `processing.run()` for algorithm execution
4. Use `QgsLayoutExporter` for print layout exports
5. Use `QgsMapRendererSequentialJob` for map image rendering

**QGIS is a hard dependency.** The system must have QGIS installed with Python
bindings available (`import qgis.core` must work).

## Installation Requirements

- QGIS 3.x installed with Python bindings
- `apt install qgis qgis-plugin-grass` (Debian/Ubuntu)
- `brew install qgis` (macOS)
- Python 3.10+
