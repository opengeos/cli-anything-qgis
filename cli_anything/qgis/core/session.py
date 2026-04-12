"""Session management with undo/redo and state persistence."""

import copy
import json
import os
import time
from pathlib import Path


def _locked_save_json(path, data, **dump_kwargs):
    """Atomically write JSON with exclusive file locking."""
    try:
        f = open(path, "r+")
    except FileNotFoundError:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        f = open(path, "w")
    with f:
        _locked = False
        try:
            import fcntl

            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            _locked = True
        except (ImportError, OSError):
            pass
        try:
            f.seek(0)
            f.truncate()
            json.dump(data, f, **dump_kwargs)
            f.flush()
        finally:
            if _locked:
                import fcntl

                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class Session:
    """Manages CLI session state with undo/redo support.

    Tracks the current project, loaded layers, and modification history.
    """

    MAX_UNDO = 50

    def __init__(self, session_path=None):
        """Initialize a session.

        Args:
            session_path: Path to session JSON file. If None, uses in-memory only.
        """
        self.session_path = session_path
        self.state = {
            "project_path": None,
            "layers": [],
            "extent": None,
            "crs": None,
            "modified": False,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self._undo_stack = []
        self._redo_stack = []

        if session_path and os.path.exists(session_path):
            self._load()

    def _load(self):
        """Load session from file."""
        with open(self.session_path, "r") as f:
            data = json.load(f)
        self.state = data.get("state", self.state)
        self._undo_stack = data.get("undo_stack", [])
        self._redo_stack = data.get("redo_stack", [])

    def save(self):
        """Save session to file."""
        if not self.session_path:
            return
        self.state["updated_at"] = time.time()
        data = {
            "state": self.state,
            "undo_stack": self._undo_stack[-self.MAX_UNDO :],
            "redo_stack": self._redo_stack[-self.MAX_UNDO :],
        }
        _locked_save_json(self.session_path, data, indent=2)

    def snapshot(self, description=""):
        """Take a snapshot of current state for undo."""
        snap = {
            "state": copy.deepcopy(self.state),
            "description": description,
            "timestamp": time.time(),
        }
        self._undo_stack.append(snap)
        if len(self._undo_stack) > self.MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        """Undo last operation.

        Returns:
            dict with 'success', 'description' keys.
        """
        if not self._undo_stack:
            return {"success": False, "description": "Nothing to undo"}

        current_snap = {
            "state": copy.deepcopy(self.state),
            "description": "before undo",
            "timestamp": time.time(),
        }
        self._redo_stack.append(current_snap)

        snap = self._undo_stack.pop()
        self.state = snap["state"]
        return {"success": True, "description": snap["description"]}

    def redo(self):
        """Redo last undone operation.

        Returns:
            dict with 'success', 'description' keys.
        """
        if not self._redo_stack:
            return {"success": False, "description": "Nothing to redo"}

        current_snap = {
            "state": copy.deepcopy(self.state),
            "description": "before redo",
            "timestamp": time.time(),
        }
        self._undo_stack.append(current_snap)

        snap = self._redo_stack.pop()
        self.state = snap["state"]
        return {"success": True, "description": snap["description"]}

    def set_project(self, path):
        """Update the current project path."""
        self.snapshot(f"set project to {path}")
        self.state["project_path"] = str(path) if path else None
        self.state["modified"] = True

    def add_layer(self, layer_info):
        """Record a layer being added.

        Args:
            layer_info: dict with 'id', 'name', 'type', 'source' keys.
        """
        self.snapshot(f"add layer {layer_info.get('name', 'unknown')}")
        self.state["layers"].append(layer_info)
        self.state["modified"] = True

    def remove_layer(self, layer_id):
        """Record a layer being removed."""
        self.snapshot(f"remove layer {layer_id}")
        self.state["layers"] = [
            l for l in self.state["layers"] if l.get("id") != layer_id
        ]
        self.state["modified"] = True

    def set_extent(self, xmin, ymin, xmax, ymax):
        """Update the current map extent."""
        self.state["extent"] = {
            "xmin": xmin,
            "ymin": ymin,
            "xmax": xmax,
            "ymax": ymax,
        }

    def set_crs(self, crs_string):
        """Update the current CRS."""
        self.state["crs"] = crs_string

    def get_status(self):
        """Get current session status.

        Returns:
            dict with session state summary.
        """
        return {
            "project_path": self.state["project_path"],
            "layer_count": len(self.state["layers"]),
            "layers": self.state["layers"],
            "extent": self.state["extent"],
            "crs": self.state["crs"],
            "modified": self.state["modified"],
            "undo_depth": len(self._undo_stack),
            "redo_depth": len(self._redo_stack),
        }

    def get_history(self, limit=10):
        """Get recent operation history.

        Args:
            limit: Maximum number of history entries.

        Returns:
            List of dicts with 'description', 'timestamp' keys.
        """
        entries = []
        for snap in reversed(self._undo_stack[-limit:]):
            entries.append(
                {
                    "description": snap["description"],
                    "timestamp": snap["timestamp"],
                }
            )
        return entries
