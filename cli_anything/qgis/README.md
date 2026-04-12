# cli-anything-qgis

Command-line interface for QGIS — operate QGIS GIS functionality without a GUI.

## Prerequisites

- **Python 3.10+**
- **QGIS 3.x** with Python bindings installed:
  ```bash
  # Debian/Ubuntu
  apt install qgis python3-qgis

  # macOS
  brew install qgis

  # Conda
  conda install -c conda-forge qgis
  ```
- Verify Python bindings work: `python -c "from qgis.core import QgsApplication; print('OK')"`

## Installation

```bash
cd agent-harness
pip install -e .
```

Verify the CLI is available:

```bash
which cli-anything-qgis
cli-anything-qgis --version
```

## Usage

### Interactive REPL

```bash
cli-anything-qgis
```

When launched with no subcommand, the CLI enters an interactive REPL with
command history, tab-completion, and a styled prompt. The startup banner
displays the absolute path to the SKILL.md file for AI agent discovery.

### One-shot Commands

```bash
# Create a new project
cli-anything-qgis project new -o myproject.qgz --title "My Map" --crs EPSG:4326

# Open an existing project
cli-anything-qgis project open myproject.qgz

# Add layers
cli-anything-qgis -p myproject.qgz layer add-vector /path/to/data.shp
cli-anything-qgis -p myproject.qgz layer add-raster /path/to/dem.tif

# List layers
cli-anything-qgis -p myproject.qgz layer list

# Query vector features
cli-anything-qgis -p myproject.qgz vector query LAYER_ID --expression '"name" = '\''Paris'\'''

# Run processing algorithms
cli-anything-qgis -p myproject.qgz processing list --search buffer
cli-anything-qgis -p myproject.qgz processing run native:buffer -P INPUT=layer_id -P DISTANCE=100

# Create and export a print layout
cli-anything-qgis -p myproject.qgz layout new --name "My Map" --page-size A4
cli-anything-qgis -p myproject.qgz layout add-map "My Map"
cli-anything-qgis -p myproject.qgz layout export-pdf "My Map" output.pdf

# Render map to image
cli-anything-qgis -p myproject.qgz render map output.png --width 1920 --height 1080

# JSON output for programmatic use
cli-anything-qgis --json -p myproject.qgz project info
```

## Using Skills (AI Agent Integration)

The CLI ships with a **SKILL.md** file that makes it discoverable and usable
by AI agents (Claude Code, Codex, etc.). The skill file is installed inside
the Python package at:

```
cli_anything/qgis/skills/SKILL.md
```

### How agents discover the skill

1. **REPL banner** — When the REPL starts, the banner prints the absolute
   path to SKILL.md. An agent can read this path to learn all available
   commands:

   ```
   ╭──────────────────────────────────────────────────────╮
   │ ◆  cli-anything · Qgis                              │
   │    v1.0.0                                            │
   │ ◇    Skill: /path/to/cli_anything/qgis/skills/SKILL.md │
   │                                                      │
   │    Type help for commands, quit to exit               │
   ╰──────────────────────────────────────────────────────╯
   ```

2. **Direct read** — An agent can locate the installed SKILL.md
   programmatically:

   ```bash
   python -c "from pathlib import Path; import cli_anything.qgis; print(Path(cli_anything.qgis.__file__).parent / 'skills' / 'SKILL.md')"
   ```

3. **`--help` flags** — Every command and subcommand supports `--help`:

   ```bash
   cli-anything-qgis --help
   cli-anything-qgis project --help
   cli-anything-qgis processing run --help
   ```

### How agents use the CLI

Agents should always use **`--json`** mode for machine-readable output:

```bash
# Create a project and capture the result
cli-anything-qgis --json project new -o /tmp/analysis.qgz

# Add a vector layer and parse the layer ID from JSON output
cli-anything-qgis --json -p /tmp/analysis.qgz layer add-vector /data/cities.geojson
# stdout: {"action": "add_vector_layer", "id": "cities_abc123", "name": "cities", ...}

# Use the layer ID in subsequent commands
cli-anything-qgis --json -p /tmp/analysis.qgz vector query cities_abc123 --limit 5
cli-anything-qgis --json -p /tmp/analysis.qgz vector stats cities_abc123 population

# Render the map
cli-anything-qgis --json -p /tmp/analysis.qgz render map /tmp/output.png --width 1920 --height 1080
```

### Key rules for agents

| Rule | Details |
|------|---------|
| Always use `--json` | Every command returns structured JSON to stdout |
| Use absolute paths | All file arguments should be absolute paths |
| Check return codes | 0 = success, non-zero = error |
| Parse stderr for errors | Error JSON is written to stderr |
| Verify output files | After render/export, check the file exists and has correct magic bytes |
| Use `-p` for project | Pass `-p /path/to/project.qgz` to load a project for each invocation |
| Layer IDs are ephemeral | Each CLI invocation loads the project fresh; layer IDs may change between runs |

### Typical agent workflow

```bash
# 1. Create project
cli-anything-qgis --json project new -o /tmp/map.qgz --title "Population Analysis"

# 2. Add data layers
cli-anything-qgis --json -p /tmp/map.qgz layer add-vector /data/countries.geojson
cli-anything-qgis --json -p /tmp/map.qgz layer add-raster /data/elevation.tif

# 3. Inspect the data
cli-anything-qgis --json -p /tmp/map.qgz layer list
cli-anything-qgis --json -p /tmp/map.qgz vector stats LAYER_ID population

# 4. Apply styling
cli-anything-qgis --json -p /tmp/map.qgz style graduated LAYER_ID population --classes 5 --color-ramp Reds

# 5. Run a processing algorithm
cli-anything-qgis --json -p /tmp/map.qgz processing run native:buffer \
  -P INPUT=LAYER_ID -P DISTANCE=50000 -P OUTPUT=/tmp/buffered.gpkg

# 6. Create a print layout and export
cli-anything-qgis --json -p /tmp/map.qgz layout new --name "Final Map" --page-size A3
cli-anything-qgis --json -p /tmp/map.qgz layout add-map "Final Map"
cli-anything-qgis --json -p /tmp/map.qgz layout add-label "Final Map" "Population by Country"
cli-anything-qgis --json -p /tmp/map.qgz layout export-pdf "Final Map" /tmp/map.pdf --dpi 300

# 7. Or render the map canvas directly
cli-anything-qgis --json -p /tmp/map.qgz render map /tmp/map.png --width 3840 --height 2160
```

### Session persistence for REPL agents

For agents that maintain a multi-turn conversation, use `--session` to persist
undo/redo history and state across REPL commands:

```bash
cli-anything-qgis --session /tmp/my_session.json
```

The session file tracks the current project, loaded layers, extent, CRS, and
up to 50 levels of undo/redo history.

## Command Groups

| Group | Description |
|-------|-------------|
| `project` | Create, open, save, info, close projects |
| `layer` | Add, remove, list, info for vector/raster layers |
| `vector` | Query features, statistics, filter, extent |
| `raster` | Band info and statistics |
| `style` | Single-symbol, categorized, graduated renderers, labeling |
| `processing` | List providers/algorithms, run algorithms |
| `layout` | Create print layouts, add map/legend/scalebar/label, export |
| `render` | Render map canvas to image |
| `export` | Unified export pipeline |
| `session` | Undo/redo, status, history |

## Running Tests

```bash
cd agent-harness
python -m pytest cli_anything/qgis/tests/ -v -s
```

Force-installed mode (verifies the `cli-anything-qgis` command is in PATH):

```bash
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest cli_anything/qgis/tests/ -v -s
```
