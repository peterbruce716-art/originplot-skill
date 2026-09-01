from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _packages(path: Path) -> set[str]:
    result: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name = line.split(";", 1)[0].strip().split("[", 1)[0]
        for token in (">=", "<=", "==", "~=", ">", "<"):
            name = name.split(token, 1)[0]
        result.add(name.strip().lower())
    return result


def main() -> int:
    core = _packages(ROOT / "requirements-core.txt")
    origin = _packages(ROOT / "requirements-origin.txt")
    required_core = {"pillow", "openpyxl", "xlrd"}
    forbidden_core = {"pandas", "numpy", "opencv-python-headless", "scikit-image", "pymupdf"}
    errors: list[str] = []
    if not required_core <= core:
        errors.append("missing v6 core dependencies: " + ", ".join(sorted(required_core - core)))
    if core & forbidden_core:
        errors.append("heavy legacy dependencies remain in core: " + ", ".join(sorted(core & forbidden_core)))
    if "originpro" not in origin:
        errors.append("requirements-origin.txt must contain originpro")
    if "originpro" in core:
        errors.append("originpro must not be an offline core dependency")
    if errors:
        print("\n".join(errors))
        return 1
    print("dependency audit passed: compact offline core + separate Origin runtime")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
