"""Unit tests for cli-anything-qgis core modules.

These tests use synthetic data and do NOT require QGIS to be installed.
They test session management, utilities, and CLI interface structure.
"""

import json
import os
import tempfile
import shutil

import pytest

# ── Session Tests ─────────────────────────────────────────────────────


class TestSession:
    """Tests for the Session class (no QGIS dependency)."""

    def test_create_session_in_memory(self):
        from cli_anything.qgis.core.session import Session

        s = Session()
        assert s.state["project_path"] is None
        assert s.state["layers"] == []
        assert s.state["modified"] is False

    def test_create_session_with_file(self, tmp_path):
        from cli_anything.qgis.core.session import Session

        path = str(tmp_path / "session.json")
        s = Session(session_path=path)
        s.save()
        assert os.path.exists(path)

    def test_snapshot_and_undo(self):
        from cli_anything.qgis.core.session import Session

        s = Session()
        s.state["project_path"] = "before.qgz"
        s.snapshot("set project")
        s.state["project_path"] = "after.qgz"

        result = s.undo()
        assert result["success"] is True
        assert s.state["project_path"] == "before.qgz"

    def test_snapshot_and_redo(self):
        from cli_anything.qgis.core.session import Session

        s = Session()
        s.state["project_path"] = "before.qgz"
        s.snapshot("set project")
        s.state["project_path"] = "after.qgz"

        s.undo()
        assert s.state["project_path"] == "before.qgz"

        result = s.redo()
        assert result["success"] is True
        assert s.state["project_path"] == "after.qgz"

    def test_undo_empty_stack(self):
        from cli_anything.qgis.core.session import Session

        s = Session()
        result = s.undo()
        assert result["success"] is False

    def test_redo_empty_stack(self):
        from cli_anything.qgis.core.session import Session

        s = Session()
        result = s.redo()
        assert result["success"] is False

    def test_multiple_undo_redo(self):
        from cli_anything.qgis.core.session import Session

        s = Session()

        s.snapshot("step 1")
        s.state["project_path"] = "one.qgz"

        s.snapshot("step 2")
        s.state["project_path"] = "two.qgz"

        s.snapshot("step 3")
        s.state["project_path"] = "three.qgz"

        # Undo back to step 2
        s.undo()
        assert s.state["project_path"] == "two.qgz"

        s.undo()
        assert s.state["project_path"] == "one.qgz"

        # Redo forward
        s.redo()
        assert s.state["project_path"] == "two.qgz"

    def test_set_project(self):
        from cli_anything.qgis.core.session import Session

        s = Session()
        s.set_project("/path/to/project.qgz")
        assert s.state["project_path"] == "/path/to/project.qgz"
        assert s.state["modified"] is True

    def test_add_layer(self):
        from cli_anything.qgis.core.session import Session

        s = Session()
        s.add_layer(
            {"id": "lyr1", "name": "Test", "type": "vector", "source": "test.shp"}
        )
        assert len(s.state["layers"]) == 1
        assert s.state["layers"][0]["id"] == "lyr1"

    def test_remove_layer(self):
        from cli_anything.qgis.core.session import Session

        s = Session()
        s.add_layer(
            {"id": "lyr1", "name": "Test", "type": "vector", "source": "test.shp"}
        )
        s.remove_layer("lyr1")
        assert len(s.state["layers"]) == 0

    def test_set_extent(self):
        from cli_anything.qgis.core.session import Session

        s = Session()
        s.set_extent(-180, -90, 180, 90)
        assert s.state["extent"]["xmin"] == -180
        assert s.state["extent"]["ymax"] == 90

    def test_set_crs(self):
        from cli_anything.qgis.core.session import Session

        s = Session()
        s.set_crs("EPSG:4326")
        assert s.state["crs"] == "EPSG:4326"

    def test_get_status(self):
        from cli_anything.qgis.core.session import Session

        s = Session()
        s.set_project("test.qgz")
        s.add_layer({"id": "lyr1", "name": "A", "type": "vector", "source": "a.shp"})

        status = s.get_status()
        assert status["project_path"] == "test.qgz"
        assert status["layer_count"] == 1
        assert status["modified"] is True

    def test_get_history(self):
        from cli_anything.qgis.core.session import Session

        s = Session()
        s.set_project("one.qgz")
        s.set_project("two.qgz")

        history = s.get_history(limit=5)
        assert len(history) >= 2
        assert "set project" in history[0]["description"]

    def test_save_and_load(self, tmp_path):
        from cli_anything.qgis.core.session import Session

        path = str(tmp_path / "session.json")
        s1 = Session(session_path=path)
        s1.set_project("loaded.qgz")
        s1.add_layer({"id": "lyr1", "name": "L1", "type": "vector", "source": "l1.shp"})
        s1.save()

        s2 = Session(session_path=path)
        assert s2.state["project_path"] == "loaded.qgz"
        assert len(s2.state["layers"]) == 1

    def test_max_undo_limit(self):
        from cli_anything.qgis.core.session import Session

        s = Session()
        for i in range(60):
            s.snapshot(f"step {i}")
            s.state["project_path"] = f"project_{i}.qgz"

        assert len(s._undo_stack) <= s.MAX_UNDO

    def test_locked_save_json(self, tmp_path):
        from cli_anything.qgis.core.session import _locked_save_json

        path = str(tmp_path / "test.json")
        data = {"key": "value", "num": 42}
        _locked_save_json(path, data, indent=2)

        with open(path) as f:
            loaded = json.load(f)
        assert loaded == data

    def test_locked_save_json_overwrite(self, tmp_path):
        from cli_anything.qgis.core.session import _locked_save_json

        path = str(tmp_path / "test.json")

        _locked_save_json(path, {"version": 1})
        _locked_save_json(path, {"version": 2})

        with open(path) as f:
            loaded = json.load(f)
        assert loaded["version"] == 2

    def test_new_snapshot_clears_redo(self):
        from cli_anything.qgis.core.session import Session

        s = Session()
        s.snapshot("step 1")
        s.state["project_path"] = "one.qgz"
        s.snapshot("step 2")
        s.state["project_path"] = "two.qgz"

        s.undo()
        assert len(s._redo_stack) == 1

        # New action should clear redo
        s.snapshot("step 3")
        assert len(s._redo_stack) == 0


# ── Backend Tests ─────────────────────────────────────────────────────


class TestBackend:
    """Tests for backend utility functions."""

    def test_find_qgis_raises_without_bindings(self, monkeypatch):
        """Test that find_qgis raises RuntimeError when qgis not importable."""
        import importlib

        def mock_import(name, *args, **kwargs):
            if name == "qgis.core":
                raise ImportError("No module named 'qgis'")
            return original_import(name, *args, **kwargs)

        from cli_anything.qgis.utils import qgis_backend

        # Reset state
        qgis_backend._initialized = False
        qgis_backend._qgis_app = None

        original_import = (
            __builtins__.__import__
            if hasattr(__builtins__, "__import__")
            else __import__
        )
        monkeypatch.setattr("builtins.__import__", mock_import)

        with pytest.raises(RuntimeError, match="QGIS Python bindings"):
            qgis_backend.find_qgis()

    def test_find_qgis_process_returns_path_or_raises(self):
        """Test find_qgis_process behavior."""
        from cli_anything.qgis.utils.qgis_backend import find_qgis_process

        try:
            path = find_qgis_process()
            assert os.path.exists(path)
        except RuntimeError as e:
            assert "qgis_process not found" in str(e)


# ── CLI Structure Tests ───────────────────────────────────────────────


class TestCLIStructure:
    """Tests for CLI interface structure (help, version, etc.)."""

    def test_cli_help(self):
        from click.testing import CliRunner
        from cli_anything.qgis.qgis_cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "QGIS command-line interface" in result.output

    def test_cli_version(self):
        from click.testing import CliRunner
        from cli_anything.qgis.qgis_cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "1.0.0" in result.output

    def test_project_help(self):
        from click.testing import CliRunner
        from cli_anything.qgis.qgis_cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["project", "--help"])
        assert result.exit_code == 0
        assert "new" in result.output
        assert "open" in result.output

    def test_layer_help(self):
        from click.testing import CliRunner
        from cli_anything.qgis.qgis_cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["layer", "--help"])
        assert result.exit_code == 0
        assert "add-vector" in result.output

    def test_processing_help(self):
        from click.testing import CliRunner
        from cli_anything.qgis.qgis_cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["processing", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "run" in result.output

    def test_vector_help(self):
        from click.testing import CliRunner
        from cli_anything.qgis.qgis_cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["vector", "--help"])
        assert result.exit_code == 0
        assert "query" in result.output

    def test_raster_help(self):
        from click.testing import CliRunner
        from cli_anything.qgis.qgis_cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["raster", "--help"])
        assert result.exit_code == 0
        assert "info" in result.output

    def test_layout_help(self):
        from click.testing import CliRunner
        from cli_anything.qgis.qgis_cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["layout", "--help"])
        assert result.exit_code == 0
        assert "new" in result.output
        assert "export-pdf" in result.output

    def test_render_help(self):
        from click.testing import CliRunner
        from cli_anything.qgis.qgis_cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["render", "--help"])
        assert result.exit_code == 0
        assert "map" in result.output

    def test_export_help(self):
        from click.testing import CliRunner
        from cli_anything.qgis.qgis_cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["export", "--help"])
        assert result.exit_code == 0
        assert "render" in result.output

    def test_session_help(self):
        from click.testing import CliRunner
        from cli_anything.qgis.qgis_cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["session", "--help"])
        assert result.exit_code == 0
        assert "undo" in result.output
        assert "redo" in result.output
