from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORT_TO_REQUIREMENT = {
    "cv2": "opencv-python-headless",
    "fitz": "PyMuPDF",
    "numpy": "numpy",
    "PIL": "Pillow",
    "skimage": "scikit-image",
    "yaml": "PyYAML",
    "pytest": "pytest",
    "pandas": "pandas",
    "originpro": "originpro",
}
REQUIREMENT_FILES = {
    "requirements-core.txt",
    "requirements-origin.txt",
    "requirements-dev.txt",
}
SKIP_PARTS = {"outputs", "tmp_v5_validation", "__pycache__", ".pytest_cache"}


def imported_modules() -> set[str]:
    modules: set[str] = set()
    for path in ROOT.rglob("*.py"):
        if any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module.split(".")[0])
    return modules


def declared_requirements() -> set[str]:
    declared: set[str] = set()
    for filename in REQUIREMENT_FILES:
        for raw in (ROOT / filename).read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith(("#", "-r")):
                continue
            name = line.split(";", 1)[0].split("[", 1)[0]
            for separator in ("<", ">", "=", "!", "~"):
                name = name.split(separator, 1)[0]
            declared.add(name.strip().lower())
    return declared


def audit() -> dict[str, object]:
    imports = imported_modules()
    declared = declared_requirements()
    required = {
        requirement.lower()
        for module, requirement in IMPORT_TO_REQUIREMENT.items()
        if module in imports
    }
    missing = sorted(required - declared)
    return {
        "schema": "originplot.dependency_audit.v1",
        "status": "ok" if not missing else "failed",
        "detected_external_imports": sorted(module for module in imports if module in IMPORT_TO_REQUIREMENT),
        "declared_requirements": sorted(declared),
        "missing_requirements": missing,
        "originext_policy": "Origin-provided module; not declared as a cross-platform pip package",
    }


def main() -> int:
    result = audit()
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
