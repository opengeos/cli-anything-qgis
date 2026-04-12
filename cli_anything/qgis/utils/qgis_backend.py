"""QGIS Backend — Initializes and manages headless QGIS environment.

This module handles QgsApplication lifecycle and provides utilities
for finding and verifying the QGIS installation.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Global reference to the QgsApplication instance
_qgis_app = None
_initialized = False


def find_qgis():
    """Find the QGIS installation and verify Python bindings are available.

    Returns:
        Path to the qgis_process executable (or None if only Python bindings exist).

    Raises:
        RuntimeError: If QGIS Python bindings are not importable.
    """
    try:
        import qgis.core  # noqa: F401
    except ImportError:
        raise RuntimeError(
            "QGIS Python bindings are not available. Install QGIS with:\n"
            "  apt install qgis python3-qgis   # Debian/Ubuntu\n"
            "  brew install qgis               # macOS\n"
            "  conda install -c conda-forge qgis  # Conda\n"
            "\n"
            "Ensure the QGIS Python path is on your PYTHONPATH."
        )
    return shutil.which("qgis_process")


def find_qgis_process():
    """Find the qgis_process CLI tool.

    Returns:
        Path to qgis_process executable.

    Raises:
        RuntimeError: If qgis_process is not found.
    """
    path = shutil.which("qgis_process")
    if path:
        return path
    raise RuntimeError(
        "qgis_process not found in PATH. Install QGIS with:\n"
        "  apt install qgis   # Debian/Ubuntu\n"
        "  brew install qgis  # macOS"
    )


def init_qgis(gui=False):
    """Initialize QgsApplication for headless use.

    Args:
        gui: If True, initialize with GUI support. Default False (headless).

    Returns:
        The QgsApplication instance.
    """
    global _qgis_app, _initialized

    if _initialized and _qgis_app is not None:
        return _qgis_app

    find_qgis()  # Verify bindings are available

    from qgis.core import QgsApplication

    # Set prefix path if QGIS_PREFIX_PATH is defined
    prefix = os.environ.get("QGIS_PREFIX_PATH", "")

    _qgis_app = QgsApplication([], gui)

    if prefix:
        QgsApplication.setPrefixPath(prefix, True)

    QgsApplication.setOrganizationName("QGIS")
    QgsApplication.setOrganizationDomain("qgis.org")
    QgsApplication.setApplicationName("QGIS3")

    QgsApplication.initQgis()
    _initialized = True

    return _qgis_app


def cleanup_qgis():
    """Clean up and shut down QgsApplication."""
    global _qgis_app, _initialized

    if _initialized:
        from qgis.core import QgsApplication

        QgsApplication.exitQgis()
        _initialized = False
        _qgis_app = None


def ensure_qgis():
    """Ensure QGIS is initialized. Call this before any QGIS API usage.

    Returns:
        The QgsApplication instance.
    """
    if not _initialized:
        return init_qgis()
    return _qgis_app


def run_qgis_process(args, json_output=True):
    """Run qgis_process as a subprocess.

    Args:
        args: List of arguments to pass to qgis_process.
        json_output: If True, add --json flag.

    Returns:
        dict with 'stdout', 'stderr', 'returncode' keys.
    """
    qgis_process = find_qgis_process()
    cmd = [qgis_process]
    if json_output:
        cmd.append("--json")
    cmd.extend(args)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }
