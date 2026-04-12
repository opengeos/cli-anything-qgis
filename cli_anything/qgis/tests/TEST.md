# TEST.md — cli-anything-qgis Test Plan and Results

## Part 1: Test Plan

### Test Inventory

| Test File | Type | Estimated Tests |
|-----------|------|-----------------|
| `test_core.py` | Unit tests (synthetic data, no QGIS dependency) | ~30 tests |
| `test_full_e2e.py` | E2E tests (real QGIS backend, real files) | ~25 tests |

### Unit Test Plan (`test_core.py`)

Tests session management and utilities without requiring QGIS:

1. **Session Module** (~15 tests)
   - Create session with/without file path
   - Snapshot and undo
   - Snapshot and redo
   - Undo when stack empty
   - Redo when stack empty
   - Multiple undo/redo cycles
   - Set project path
   - Add/remove layers in session
   - Set extent and CRS
   - Get status
   - Get history with limit
   - Save and load session from file
   - MAX_UNDO limit enforcement
   - Locked save JSON (file locking)

2. **Backend Module** (~5 tests)
   - find_qgis() returns path or raises RuntimeError
   - find_qgis_process() returns path or raises RuntimeError

3. **CLI Help/Version** (~5 tests)
   - CLI --help output
   - CLI --version output
   - Subcommand help (project --help, layer --help, etc.)

### E2E Test Plan (`test_full_e2e.py`)

Tests that invoke the real QGIS backend and produce real output files:

1. **Project Operations** (~5 tests)
   - Create new .qgz project
   - Open existing project
   - Save project (save-as)
   - Project info
   - Close project

2. **Layer Operations** (~5 tests)
   - Add vector layer (GeoJSON)
   - Add raster layer (GeoTIFF)
   - List layers after adding
   - Layer info for vector layer
   - Remove layer

3. **Vector Operations** (~4 tests)
   - Query features from vector layer
   - Count features
   - Field statistics on numeric field
   - Get vector extent

4. **Raster Operations** (~2 tests)
   - Raster info
   - Band statistics

5. **Rendering & Export** (~4 tests)
   - Render map to PNG
   - Export layout to PDF
   - Export layout to PNG
   - Verify output files (magic bytes, size > 0)

6. **CLI Subprocess Tests** (~5 tests)
   - `cli-anything-qgis --help`
   - `cli-anything-qgis --json project new -o test.qgz`
   - `cli-anything-qgis --json layer list`
   - `cli-anything-qgis --json session status`
   - Full workflow: create project → add layer → render

### Realistic Workflow Scenarios

1. **GIS Analysis Workflow**
   - Simulates: A GIS analyst loading data, querying features, and producing a map
   - Operations: project new → layer add-vector → vector query → style categorized → render map
   - Verified: Output PNG exists, has correct format, size > 0

2. **Map Production Workflow**
   - Simulates: Cartographer creating a print-ready map
   - Operations: project new → layer add-vector → layout new → layout add-map → layout add-legend → layout export-pdf
   - Verified: PDF has %PDF- magic bytes, size > 1000

3. **Batch Processing Workflow**
   - Simulates: Running processing algorithms from scripts
   - Operations: project new → layer add-vector → processing run native:buffer → export render
   - Verified: Output layer created, result file exists

---

## Part 2: Test Results

### Full Test Output (`pytest -v --tb=no`)

```
cli_anything/qgis/tests/test_core.py::TestSession::test_create_session_in_memory PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_create_session_with_file PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_snapshot_and_undo PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_snapshot_and_redo PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_undo_empty_stack PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_redo_empty_stack PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_multiple_undo_redo PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_set_project PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_add_layer PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_remove_layer PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_set_extent PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_set_crs PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_get_status PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_get_history PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_save_and_load PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_max_undo_limit PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_locked_save_json PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_locked_save_json_overwrite PASSED
cli_anything/qgis/tests/test_core.py::TestSession::test_new_snapshot_clears_redo PASSED
cli_anything/qgis/tests/test_core.py::TestBackend::test_find_qgis_raises_without_bindings PASSED
cli_anything/qgis/tests/test_core.py::TestBackend::test_find_qgis_process_returns_path_or_raises PASSED
cli_anything/qgis/tests/test_core.py::TestCLIStructure::test_cli_help PASSED
cli_anything/qgis/tests/test_core.py::TestCLIStructure::test_cli_version PASSED
cli_anything/qgis/tests/test_core.py::TestCLIStructure::test_project_help PASSED
cli_anything/qgis/tests/test_core.py::TestCLIStructure::test_layer_help PASSED
cli_anything/qgis/tests/test_core.py::TestCLIStructure::test_processing_help PASSED
cli_anything/qgis/tests/test_core.py::TestCLIStructure::test_vector_help PASSED
cli_anything/qgis/tests/test_core.py::TestCLIStructure::test_raster_help PASSED
cli_anything/qgis/tests/test_core.py::TestCLIStructure::test_layout_help PASSED
cli_anything/qgis/tests/test_core.py::TestCLIStructure::test_render_help PASSED
cli_anything/qgis/tests/test_core.py::TestCLIStructure::test_export_help PASSED
cli_anything/qgis/tests/test_core.py::TestCLIStructure::test_session_help PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestProject::test_create_project_qgz PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestProject::test_create_project_qgs PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestProject::test_open_project PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestProject::test_save_project PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestProject::test_project_info PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestProject::test_close_project PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestLayers::test_add_vector_layer PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestLayers::test_add_raster_layer PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestLayers::test_list_layers PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestLayers::test_layer_info_vector PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestLayers::test_remove_layer PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestVector::test_query_features PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestVector::test_query_with_expression PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestVector::test_count_features PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestVector::test_field_statistics PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestVector::test_get_extent PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestRaster::test_raster_info PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestRaster::test_band_statistics PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestRenderExport::test_render_map_png PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestRenderExport::test_layout_export_pdf PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestRenderExport::test_layout_export_image PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestRenderExport::test_unified_export PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestCLISubprocess::test_version PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestCLISubprocess::test_project_new_json PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestCLISubprocess::test_session_status_json PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestCLISubprocess::test_full_workflow PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestWorkflowScenarios::test_gis_analysis_workflow PASSED
cli_anything/qgis/tests/test_full_e2e.py::TestWorkflowScenarios::test_map_production_workflow PASSED

======================== 61 passed, 3 warnings in 4.44s ========================
```

### Summary Statistics

- **Total tests**: 61
- **Passed**: 61
- **Failed**: 0
- **Pass rate**: 100%
- **Execution time**: 4.44s
- **Test mode**: `CLI_ANYTHING_FORCE_INSTALLED=1` (verified installed command)

### Coverage

| Module | Unit Tests | E2E Tests |
|--------|-----------|-----------|
| session.py | 19 tests | - |
| qgis_backend.py | 2 tests | Tested via all E2E tests |
| project.py | - | 6 tests |
| layer.py | - | 5 tests |
| vector.py | - | 5 tests |
| raster.py | - | 2 tests |
| render.py | - | 1 test |
| layout.py | - | 2 tests |
| export.py | - | 1 test |
| CLI structure | 11 tests | 5 subprocess tests |
| Workflows | - | 2 multi-step tests |

### Output Artifacts Verified

- **QGZ projects**: Created, opened, saved, verified (4,000+ bytes)
- **QGS projects**: Created, verified (13,000+ bytes)
- **PNG map renders**: Verified with `\x89PNG` magic bytes (3,700+ bytes)
- **PDF layout exports**: Verified with `%PDF-` magic bytes (4,200+ bytes)
- **PNG layout exports**: Verified with `\x89PNG` magic bytes (6,700+ bytes)
