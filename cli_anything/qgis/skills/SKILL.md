---
name: >-
  cli-anything-qgis
description: >-
  Command-line interface for Qgis - Command-line interface for QGIS — operate QGIS GIS functionality without a GUI....
---

# cli-anything-qgis

Command-line interface for QGIS — operate QGIS GIS functionality without a GUI.

## Installation

This CLI is installed as part of the cli-anything-qgis package:

```bash
pip install cli-anything-qgis
```

**Prerequisites:**
- Python 3.10+
- qgis must be installed on your system


## Usage

### Basic Commands

```bash
# Show help
cli-anything-qgis --help

# Start interactive REPL mode
cli-anything-qgis

# Create a new project
cli-anything-qgis project new -o project.json

# Run with JSON output (for agent consumption)
cli-anything-qgis --json project info -p project.json
```

### REPL Mode

When invoked without a subcommand, the CLI enters an interactive REPL session:

```bash
cli-anything-qgis
# Enter commands interactively with tab-completion and history
```


## Command Groups


### Project

Project management — create, open, save, info.

| Command | Description |
|---------|-------------|

| `project-open` | Open an existing QGIS project. |

| `project-save` | Save the current project. |

| `project-info-cmd` | Show project information. |

| `project-close` | Close the current project. |



### Layer

Layer management — add, remove, list, info.

| Command | Description |
|---------|-------------|

| `layer-remove` | Remove a layer by its ID. |

| `layer-list` | List all layers in the current project. |

| `layer-info-cmd` | Show detailed information about a layer. |



### Vector

Vector operations — query features, statistics, filter.

| Command | Description |
|---------|-------------|

| `vector-query` | Query features from a vector layer. |

| `vector-stats` | Compute statistics for a vector field. |

| `vector-count` | Count features in a vector layer. |

| `vector-extent` | Get the bounding box of a vector layer. |



### Raster

Raster operations — info, band statistics.

| Command | Description |
|---------|-------------|

| `raster-info-cmd` | Show detailed raster layer information. |



### Style

Styling — renderers, classification, labeling.

| Command | Description |
|---------|-------------|

| `style-categorized` | Apply a categorized renderer based on a field. |

| `style-labels` | Enable labeling on a vector layer. |

| `style-load` | Load a QML style file onto a layer. |

| `style-save` | Save a layer's style to a QML file. |



### Processing Group

Processing — list and run QGIS algorithms.

| Command | Description |
|---------|-------------|

| `processing-list` | List available processing algorithms. |

| `processing-info` | Show detailed info about a processing algorithm. |

| `processing-run` | Run a processing algorithm with given parameters. |

| `processing-providers` | List available processing providers. |



### Layout

Layout — create print layouts, add items, export.

| Command | Description |
|---------|-------------|

| `layout-list` | List all print layouts. |

| `layout-add-map` | Add a map item to a layout. |

| `layout-add-legend` | Add a legend item to a layout. |

| `layout-add-scalebar` | Add a scale bar to a layout. |

| `layout-add-label` | Add a text label to a layout. |

| `layout-export-pdf` | Export a layout to PDF. |

| `layout-export-image` | Export a layout to an image (PNG, JPEG, etc.). |



### Render

Render — export map canvas to image.

| Command | Description |
|---------|-------------|

| `render-map` | Render the current map to an image file. |



### Export

Export — unified export pipeline for maps and layouts.

| Command | Description |
|---------|-------------|



### Session

Session — state management, undo/redo, history.

| Command | Description |
|---------|-------------|

| `session-status` | Show current session status. |

| `session-history` | Show recent operation history. |

| `session-undo` | Undo the last operation. |

| `session-redo` | Redo the last undone operation. |




## Examples


### Create a New QGIS Project

Create a new QGIS project file (.qgz or .qgs).

```bash
cli-anything-qgis project new -o myproject.qgz --title "My GIS Project" --crs EPSG:4326
# Or with JSON output for programmatic use
cli-anything-qgis --json project new -o myproject.qgz
```


### Load Data and Render a Map

Load vector/raster data and render to an image.

```bash
cli-anything-qgis -p myproject.qgz layer add-vector /path/to/cities.geojson
cli-anything-qgis -p myproject.qgz layer add-raster /path/to/elevation.tif
cli-anything-qgis -p myproject.qgz render map output.png --width 1920 --height 1080
```


### Create a Print Layout and Export PDF

Build a print-ready map with layout items.

```bash
cli-anything-qgis -p myproject.qgz layout new --name "City Map" --page-size A4
cli-anything-qgis -p myproject.qgz layout add-map "City Map"
cli-anything-qgis -p myproject.qgz layout add-label "City Map" "Population Map 2024"
cli-anything-qgis -p myproject.qgz layout export-pdf "City Map" output.pdf --dpi 300
```


### Run Processing Algorithms

List and run QGIS processing algorithms (buffer, clip, dissolve, etc.).

```bash
cli-anything-qgis --json processing list --search buffer
cli-anything-qgis --json -p myproject.qgz processing run native:buffer \
  -P INPUT=layer_id -P DISTANCE=1000 -P OUTPUT=/tmp/buffered.gpkg
```


### Interactive REPL Session

Start an interactive session with undo/redo support.

```bash
cli-anything-qgis
# Enter commands interactively
# Use 'help' to see available commands
# Use 'undo' and 'redo' for history navigation
```


## State Management

The CLI maintains session state with:

- **Undo/Redo**: Up to 50 levels of history
- **Project persistence**: Save/load project state as JSON
- **Session tracking**: Track modifications and changes

## Output Formats

All commands support dual output modes:

- **Human-readable** (default): Tables, colors, formatted text
- **Machine-readable** (`--json` flag): Structured JSON for agent consumption

```bash
# Human output
cli-anything-qgis project info -p project.json

# JSON output for agents
cli-anything-qgis --json project info -p project.json
```

## For AI Agents

When using this CLI programmatically:

1. **Always use `--json` flag** for parseable output
2. **Check return codes** - 0 for success, non-zero for errors
3. **Parse stderr** for error messages on failure
4. **Use absolute paths** for all file operations
5. **Verify outputs exist** after export operations

## More Information

- Full documentation: See README.md in the package
- Test coverage: See TEST.md in the package
- Methodology: See HARNESS.md in the cli-anything-plugin

## Version

1.0.0