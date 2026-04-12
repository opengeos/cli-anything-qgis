"""Root conftest.py — prevents sys.path pollution that shadows system qgis.

Pytest's default import mode walks up from test files through __init__.py
directories and adds them to sys.path. Since cli_anything/ is a namespace
package (no __init__.py), pytest can add cli_anything/ itself, causing
our cli_anything/qgis/ to shadow the system qgis package.

We fix this by pre-importing the system qgis package and caching it in
sys.modules BEFORE pytest has a chance to pollute sys.path.
"""

import sys

# Pre-import the system qgis package IMMEDIATELY at conftest load time,
# before pytest modifies sys.path during test collection. This caches
# the correct qgis module in sys.modules so later imports resolve to
# the system package even if cli_anything/ gets added to sys.path.
import qgis  # noqa: E402
import qgis.core  # noqa: E402
import qgis.PyQt  # noqa: E402
