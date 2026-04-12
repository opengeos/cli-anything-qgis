"""End-to-end tests for cli-anything-qgis.

These tests require QGIS to be installed with Python bindings.
They test the full pipeline: create project → add layers → export.

No graceful degradation — if QGIS is not installed, tests fail.
"""

import json
import os
import subprocess
import sys
import tempfile

import pytest


# ── Helpers ───────────────────────────────────────────────────────────


def _resolve_cli(name):
    """Resolve installed CLI command; falls back to python -m for dev.

    Set env CLI_ANYTHING_FORCE_INSTALLED=1 to require the installed command.
    """
    import shutil

    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = (
        name.replace("cli-anything-", "cli_anything.")
        + "."
        + name.split("-")[-1]
        + "_cli"
    )
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


def _create_test_geojson(path):
    """Create a minimal GeoJSON file for testing."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
                "properties": {"name": "Origin", "value": 10.5},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [1.0, 1.0]},
                "properties": {"name": "NorthEast", "value": 20.3},
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-1.0, -1.0]},
                "properties": {"name": "SouthWest", "value": 5.1},
            },
        ],
    }
    with open(path, "w") as f:
        json.dump(geojson, f)
    return path


def _create_test_geotiff(path):
    """Create a minimal GeoTIFF for testing using GDAL."""
    try:
        from osgeo import gdal, osr
        import numpy as np
    except ImportError:
        pytest.skip("GDAL Python bindings required for raster tests")

    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(path, 10, 10, 1, gdal.GDT_Float32)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    ds.SetProjection(srs.ExportToWkt())
    ds.SetGeoTransform([0, 0.1, 0, 1, 0, -0.1])
    band = ds.GetRasterBand(1)
    data = np.arange(100, dtype=np.float32).reshape(10, 10)
    band.WriteArray(data)
    band.FlushCache()
    ds = None
    return path


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def qgis_app():
    """Initialize QGIS application for the test module."""
    from cli_anything.qgis.utils.qgis_backend import init_qgis

    app = init_qgis()
    yield app
    # Don't cleanup here — other tests might need QGIS


@pytest.fixture
def tmp_dir():
    """Create a temporary directory for test outputs."""
    d = tempfile.mkdtemp(prefix="qgis_test_")
    yield d
    import shutil

    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def geojson_path(tmp_dir):
    """Create a test GeoJSON file."""
    return _create_test_geojson(os.path.join(tmp_dir, "test.geojson"))


@pytest.fixture
def geotiff_path(tmp_dir):
    """Create a test GeoTIFF file."""
    return _create_test_geotiff(os.path.join(tmp_dir, "test.tif"))


# ── Project Tests ─────────────────────────────────────────────────────


class TestProject:
    """E2E tests for project operations."""

    def test_create_project_qgz(self, qgis_app, tmp_dir):
        from cli_anything.qgis.core.project import create_project

        output = os.path.join(tmp_dir, "test.qgz")
        result = create_project(output, title="Test Project", crs="EPSG:4326")
        assert result["action"] == "create"
        assert os.path.exists(output)
        assert result["file_size"] > 0
        print(f"\n  QGZ: {output} ({result['file_size']:,} bytes)")

    def test_create_project_qgs(self, qgis_app, tmp_dir):
        from cli_anything.qgis.core.project import create_project

        output = os.path.join(tmp_dir, "test.qgs")
        result = create_project(output, title="XML Project", crs="EPSG:3857")
        assert os.path.exists(output)
        assert result["crs"] == "EPSG:3857"
        print(f"\n  QGS: {output} ({result['file_size']:,} bytes)")

    def test_open_project(self, qgis_app, tmp_dir):
        from cli_anything.qgis.core.project import create_project, open_project

        path = os.path.join(tmp_dir, "open_test.qgz")
        create_project(path, title="Open Test")
        result = open_project(path)
        assert result["action"] == "open"
        assert result["title"] == "Open Test"

    def test_save_project(self, qgis_app, tmp_dir):
        from cli_anything.qgis.core.project import create_project, save_project

        path = os.path.join(tmp_dir, "save_test.qgz")
        create_project(path)
        path2 = os.path.join(tmp_dir, "save_as.qgz")
        result = save_project(path2)
        assert os.path.exists(path2)
        assert result["file_size"] > 0

    def test_project_info(self, qgis_app, tmp_dir):
        from cli_anything.qgis.core.project import create_project, project_info

        path = os.path.join(tmp_dir, "info_test.qgz")
        create_project(path, title="Info Test")
        result = project_info(path)
        assert result["title"] == "Info Test"
        assert result["crs"] == "EPSG:4326"

    def test_close_project(self, qgis_app, tmp_dir):
        from cli_anything.qgis.core.project import close_project, create_project

        path = os.path.join(tmp_dir, "close_test.qgz")
        create_project(path)
        result = close_project()
        assert result["action"] == "close"


# ── Layer Tests ───────────────────────────────────────────────────────


class TestLayers:
    """E2E tests for layer operations."""

    def test_add_vector_layer(self, qgis_app, tmp_dir, geojson_path):
        from cli_anything.qgis.core.layer import add_vector_layer
        from cli_anything.qgis.core.project import create_project

        create_project(os.path.join(tmp_dir, "layer_test.qgz"))
        result = add_vector_layer(geojson_path)
        assert result["action"] == "add_vector_layer"
        assert result["feature_count"] == 3
        assert result["geometry_type"] == "point"
        print(
            f"\n  Vector layer: {result['name']} ({result['feature_count']} features)"
        )

    def test_add_raster_layer(self, qgis_app, tmp_dir, geotiff_path):
        from cli_anything.qgis.core.layer import add_raster_layer
        from cli_anything.qgis.core.project import create_project

        create_project(os.path.join(tmp_dir, "raster_test.qgz"))
        result = add_raster_layer(geotiff_path)
        assert result["action"] == "add_raster_layer"
        assert result["width"] == 10
        assert result["height"] == 10
        assert result["band_count"] == 1
        print(
            f"\n  Raster layer: {result['name']} ({result['width']}x{result['height']})"
        )

    def test_list_layers(self, qgis_app, tmp_dir, geojson_path):
        from cli_anything.qgis.core.layer import add_vector_layer, list_layers
        from cli_anything.qgis.core.project import create_project

        create_project(os.path.join(tmp_dir, "list_test.qgz"))
        add_vector_layer(geojson_path, name="TestPoints")
        result = list_layers()
        assert result["count"] >= 1
        names = [l["name"] for l in result["layers"]]
        assert "TestPoints" in names

    def test_layer_info_vector(self, qgis_app, tmp_dir, geojson_path):
        from cli_anything.qgis.core.layer import add_vector_layer, layer_info
        from cli_anything.qgis.core.project import create_project

        create_project(os.path.join(tmp_dir, "info_test.qgz"))
        added = add_vector_layer(geojson_path)
        result = layer_info(added["id"])
        assert result["feature_count"] == 3
        assert len(result["fields"]) >= 2

    def test_remove_layer(self, qgis_app, tmp_dir, geojson_path):
        from cli_anything.qgis.core.layer import (
            add_vector_layer,
            list_layers,
            remove_layer,
        )
        from cli_anything.qgis.core.project import create_project

        create_project(os.path.join(tmp_dir, "remove_test.qgz"))
        added = add_vector_layer(geojson_path)
        result = remove_layer(added["id"])
        assert result["action"] == "remove_layer"
        layers = list_layers()
        assert layers["count"] == 0


# ── Vector Tests ──────────────────────────────────────────────────────


class TestVector:
    """E2E tests for vector operations."""

    def test_query_features(self, qgis_app, tmp_dir, geojson_path):
        from cli_anything.qgis.core.layer import add_vector_layer
        from cli_anything.qgis.core.project import create_project
        from cli_anything.qgis.core.vector import query_features

        create_project(os.path.join(tmp_dir, "query_test.qgz"))
        added = add_vector_layer(geojson_path)
        result = query_features(added["id"])
        assert result["count"] == 3
        assert result["features"][0]["attributes"]["name"] in (
            "Origin",
            "NorthEast",
            "SouthWest",
        )

    def test_query_with_expression(self, qgis_app, tmp_dir, geojson_path):
        from cli_anything.qgis.core.layer import add_vector_layer
        from cli_anything.qgis.core.project import create_project
        from cli_anything.qgis.core.vector import query_features

        create_project(os.path.join(tmp_dir, "expr_test.qgz"))
        added = add_vector_layer(geojson_path)
        result = query_features(added["id"], expression='"name" = \'Origin\'')
        assert result["count"] == 1
        assert result["features"][0]["attributes"]["name"] == "Origin"

    def test_count_features(self, qgis_app, tmp_dir, geojson_path):
        from cli_anything.qgis.core.layer import add_vector_layer
        from cli_anything.qgis.core.project import create_project
        from cli_anything.qgis.core.vector import count_features

        create_project(os.path.join(tmp_dir, "count_test.qgz"))
        added = add_vector_layer(geojson_path)
        result = count_features(added["id"])
        assert result["count"] == 3

    def test_field_statistics(self, qgis_app, tmp_dir, geojson_path):
        from cli_anything.qgis.core.layer import add_vector_layer
        from cli_anything.qgis.core.project import create_project
        from cli_anything.qgis.core.vector import field_statistics

        create_project(os.path.join(tmp_dir, "stats_test.qgz"))
        added = add_vector_layer(geojson_path)
        result = field_statistics(added["id"], "value")
        assert result["non_null_count"] == 3
        assert result["min"] == pytest.approx(5.1)
        assert result["max"] == pytest.approx(20.3)

    def test_get_extent(self, qgis_app, tmp_dir, geojson_path):
        from cli_anything.qgis.core.layer import add_vector_layer
        from cli_anything.qgis.core.project import create_project
        from cli_anything.qgis.core.vector import get_extent

        create_project(os.path.join(tmp_dir, "extent_test.qgz"))
        added = add_vector_layer(geojson_path)
        result = get_extent(added["id"])
        assert result["xmin"] <= -1.0
        assert result["xmax"] >= 1.0


# ── Raster Tests ──────────────────────────────────────────────────────


class TestRaster:
    """E2E tests for raster operations."""

    def test_raster_info(self, qgis_app, tmp_dir, geotiff_path):
        from cli_anything.qgis.core.layer import add_raster_layer
        from cli_anything.qgis.core.project import create_project
        from cli_anything.qgis.core.raster import raster_info

        create_project(os.path.join(tmp_dir, "raster_info_test.qgz"))
        added = add_raster_layer(geotiff_path)
        result = raster_info(added["id"])
        assert result["width"] == 10
        assert result["height"] == 10
        assert result["band_count"] == 1
        assert result["pixel_size_x"] > 0

    def test_band_statistics(self, qgis_app, tmp_dir, geotiff_path):
        from cli_anything.qgis.core.layer import add_raster_layer
        from cli_anything.qgis.core.project import create_project
        from cli_anything.qgis.core.raster import band_statistics

        create_project(os.path.join(tmp_dir, "band_stats_test.qgz"))
        added = add_raster_layer(geotiff_path)
        result = band_statistics(added["id"], band=1)
        assert result["min"] == pytest.approx(0.0)
        assert result["max"] == pytest.approx(99.0)
        assert result["mean"] == pytest.approx(49.5)


# ── Render & Export Tests ─────────────────────────────────────────────


class TestRenderExport:
    """E2E tests for rendering and export."""

    def test_render_map_png(self, qgis_app, tmp_dir, geojson_path):
        from cli_anything.qgis.core.layer import add_vector_layer
        from cli_anything.qgis.core.project import create_project
        from cli_anything.qgis.core.render import render_map

        create_project(os.path.join(tmp_dir, "render_test.qgz"))
        add_vector_layer(geojson_path)
        output = os.path.join(tmp_dir, "map.png")
        result = render_map(output, width=800, height=600)
        assert os.path.exists(output)
        assert result["file_size"] > 0
        # Verify PNG magic bytes
        with open(output, "rb") as f:
            magic = f.read(8)
        assert magic[:4] == b"\x89PNG"
        print(f"\n  PNG: {output} ({result['file_size']:,} bytes)")

    def test_layout_export_pdf(self, qgis_app, tmp_dir, geojson_path):
        from cli_anything.qgis.core.layer import add_vector_layer
        from cli_anything.qgis.core.layout import (
            add_map,
            create_layout,
            export_layout_pdf,
        )
        from cli_anything.qgis.core.project import create_project

        create_project(os.path.join(tmp_dir, "layout_pdf_test.qgz"))
        add_vector_layer(geojson_path)
        create_layout(name="PDF Test", page_size="A4", orientation="landscape")
        add_map("PDF Test")
        output = os.path.join(tmp_dir, "layout.pdf")
        result = export_layout_pdf("PDF Test", output, dpi=150)
        assert os.path.exists(output)
        assert result["file_size"] > 100
        # Verify PDF magic bytes
        with open(output, "rb") as f:
            magic = f.read(5)
        assert magic == b"%PDF-"
        print(f"\n  PDF: {output} ({result['file_size']:,} bytes)")

    def test_layout_export_image(self, qgis_app, tmp_dir, geojson_path):
        from cli_anything.qgis.core.layer import add_vector_layer
        from cli_anything.qgis.core.layout import (
            add_map,
            create_layout,
            export_layout_image,
        )
        from cli_anything.qgis.core.project import create_project

        create_project(os.path.join(tmp_dir, "layout_img_test.qgz"))
        add_vector_layer(geojson_path)
        create_layout(name="IMG Test", page_size="A4", orientation="portrait")
        add_map("IMG Test")
        output = os.path.join(tmp_dir, "layout.png")
        result = export_layout_image("IMG Test", output, dpi=96)
        assert os.path.exists(output)
        assert result["file_size"] > 0
        with open(output, "rb") as f:
            magic = f.read(4)
        assert magic == b"\x89PNG"
        print(f"\n  Layout PNG: {output} ({result['file_size']:,} bytes)")

    def test_unified_export(self, qgis_app, tmp_dir, geojson_path):
        from cli_anything.qgis.core.export import export
        from cli_anything.qgis.core.layer import add_vector_layer
        from cli_anything.qgis.core.project import create_project

        create_project(os.path.join(tmp_dir, "export_test.qgz"))
        add_vector_layer(geojson_path)
        output = os.path.join(tmp_dir, "exported.png")
        result = export(output, preset="png", width=640, height=480, overwrite=True)
        assert os.path.exists(output)
        assert result["file_size"] > 0


# ── CLI Subprocess Tests ──────────────────────────────────────────────


class TestCLISubprocess:
    """Tests that invoke the installed CLI command via subprocess."""

    CLI_BASE = _resolve_cli("cli-anything-qgis")

    def _run(self, args, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True,
            text=True,
            check=check,
        )

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "QGIS command-line interface" in result.stdout

    def test_version(self):
        result = self._run(["--version"])
        assert result.returncode == 0
        assert "1.0.0" in result.stdout

    def test_project_new_json(self, tmp_dir):
        out = os.path.join(tmp_dir, "subprocess_test.qgz")
        result = self._run(["--json", "project", "new", "-o", out])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["action"] == "create"
        assert os.path.exists(out)
        print(f"\n  Subprocess QGZ: {out}")

    def test_session_status_json(self, tmp_dir):
        session_file = os.path.join(tmp_dir, "session.json")
        result = self._run(
            ["--json", "--session", session_file, "session", "status"],
            check=False,
        )
        # Should succeed (session starts empty)
        assert result.returncode == 0

    def test_full_workflow(self, tmp_dir, geojson_path):
        """Full workflow: create project → add layer → render map."""
        project = os.path.join(tmp_dir, "workflow.qgz")
        output = os.path.join(tmp_dir, "workflow.png")
        session = os.path.join(tmp_dir, "workflow_session.json")

        # Create project
        r1 = self._run(
            [
                "--json",
                "--session",
                session,
                "project",
                "new",
                "-o",
                project,
            ]
        )
        assert r1.returncode == 0

        # Add vector layer and save project (each CLI invocation is a
        # separate process, so we must persist state via the project file)
        r2 = self._run(
            [
                "--json",
                "-p",
                project,
                "--session",
                session,
                "layer",
                "add-vector",
                geojson_path,
            ]
        )
        assert r2.returncode == 0
        layer_data = json.loads(r2.stdout)
        assert layer_data["feature_count"] == 3

        # Save project so the layer persists for the next invocation
        r2b = self._run(
            [
                "--json",
                "-p",
                project,
                "--session",
                session,
                "project",
                "save",
            ]
        )
        assert r2b.returncode == 0

        # Render map
        r3 = self._run(
            [
                "--json",
                "-p",
                project,
                "--session",
                session,
                "render",
                "map",
                output,
                "--width",
                "640",
                "--height",
                "480",
            ]
        )
        assert r3.returncode == 0
        assert os.path.exists(output)
        assert os.path.getsize(output) > 0

        # Verify PNG
        with open(output, "rb") as f:
            assert f.read(4) == b"\x89PNG"
        print(f"\n  Workflow PNG: {output} ({os.path.getsize(output):,} bytes)")


# ── Workflow Scenario Tests ───────────────────────────────────────────


class TestWorkflowScenarios:
    """Realistic multi-step workflow tests."""

    def test_gis_analysis_workflow(self, qgis_app, tmp_dir, geojson_path):
        """Simulates: analyst loads data, queries features, renders a map."""
        from cli_anything.qgis.core.layer import add_vector_layer
        from cli_anything.qgis.core.project import create_project
        from cli_anything.qgis.core.render import render_map
        from cli_anything.qgis.core.vector import field_statistics, query_features

        # Step 1: Create project
        project_path = os.path.join(tmp_dir, "analysis.qgz")
        create_project(project_path, title="Analysis", crs="EPSG:4326")

        # Step 2: Load data
        layer = add_vector_layer(geojson_path, name="Points")
        assert layer["feature_count"] == 3

        # Step 3: Analyze
        stats = field_statistics(layer["id"], "value")
        assert stats["mean"] > 0

        features = query_features(layer["id"], expression='"value" > 10')
        assert features["count"] == 2

        # Step 4: Render
        output = os.path.join(tmp_dir, "analysis.png")
        result = render_map(output, width=800, height=600)
        assert os.path.exists(output)
        with open(output, "rb") as f:
            assert f.read(4) == b"\x89PNG"
        print(f"\n  Analysis map: {output} ({result['file_size']:,} bytes)")

    def test_map_production_workflow(self, qgis_app, tmp_dir, geojson_path):
        """Simulates: cartographer creates a print-ready map with layout."""
        from cli_anything.qgis.core.layer import add_vector_layer
        from cli_anything.qgis.core.layout import (
            add_label,
            add_map,
            create_layout,
            export_layout_pdf,
        )
        from cli_anything.qgis.core.project import create_project

        # Step 1: Create project and add data
        project_path = os.path.join(tmp_dir, "cartography.qgz")
        create_project(project_path, title="Map Production")
        add_vector_layer(geojson_path, name="Cities")

        # Step 2: Create layout
        create_layout(name="City Map", page_size="A4", orientation="landscape")

        # Step 3: Add map and title
        add_map("City Map", x=10, y=20, width=260, height=170)
        add_label("City Map", "City Distribution Map", x=10, y=5, font_size=18)

        # Step 4: Export PDF
        pdf_path = os.path.join(tmp_dir, "city_map.pdf")
        result = export_layout_pdf("City Map", pdf_path, dpi=150)
        assert os.path.exists(pdf_path)
        assert result["file_size"] > 500

        with open(pdf_path, "rb") as f:
            assert f.read(5) == b"%PDF-"
        print(f"\n  Map PDF: {pdf_path} ({result['file_size']:,} bytes)")
