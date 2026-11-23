"""Make the modules beside the fiberswitch daemons importable, as the daemons see them."""

import sys
from pathlib import Path

DAEMON_DIR = str(Path(__file__).resolve().parents[2] / "daemons" / "hsfibers")
if DAEMON_DIR not in sys.path:
    sys.path.insert(0, DAEMON_DIR)
