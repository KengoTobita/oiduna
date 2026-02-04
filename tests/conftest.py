"""Root conftest.py - Setup Python path for tests"""

import sys
from pathlib import Path

# Add packages to Python path
root_dir = Path(__file__).parent.parent
packages_dir = root_dir / "packages"

sys.path.insert(0, str(packages_dir / "oiduna_api"))
sys.path.insert(0, str(packages_dir / "oiduna_loop"))
sys.path.insert(0, str(packages_dir / "oiduna_core"))
sys.path.insert(0, str(packages_dir / "osc_protocol"))
