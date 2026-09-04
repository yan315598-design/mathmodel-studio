"""pytest 根 conftest: 保证 runtime/ 在 sys.path, 使 tests 能直接 import mathmodel_agent。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
