from __future__ import annotations

import argparse
import json
from pathlib import Path


ALLOWED_PREFIXES = (
    "/page/",
    "/layers/",
    "/plots/",
    "/annotations/",
    "/style/",
)


def validate_patch(patch: dict) -> dict:
    operations = patch.get("operations")
    failures = []
    if not isinstance(operations, list) or not operations:
        failures.append({"code": "missing_operations"})
    else:
        for index, operation in enumerate(operations):
            path = str(operation.get("path", ""))
            if not path.startswith(ALLOWED_PREFIXES):
                failures.append({"code": "path_not_allowed", "index": index, "path": path})
            if operation.get("rollback_on_no_improvement") is not True:
                failures.append({"code": "missing_rollback_guard", "index": index})
    return {"schema": "originplot.patch_validation.v5", "status": "pass" if not failures else "fail", "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate bounded OriginPlot v5 patch operations.")
    parser.add_argument("patch", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = validate_patch(json.loads(args.patch.read_text(encoding="utf-8-sig")))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
