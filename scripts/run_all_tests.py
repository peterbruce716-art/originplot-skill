from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    tests = sorted(str(path.relative_to(ROOT)) for path in (ROOT / "tests").glob("test_v6_*.py"))
    if not tests:
        print("no v6 tests found", file=sys.stderr)
        return 2
    command = [sys.executable, "-m", "pytest", "-q", *tests]
    return subprocess.call(command, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
