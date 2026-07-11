from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from validate_patch import validate_patch


def set_path(doc: dict, pointer: str, value) -> None:
    parts = [part for part in pointer.strip("/").split("/") if part]
    target = doc
    for part in parts[:-1]:
        target = target[int(part)] if isinstance(target, list) else target.setdefault(part, {})
    last = parts[-1]
    if isinstance(target, list):
        target[int(last)] = value
    else:
        target[last] = value


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a bounded OriginPlot v5 patch to a candidate FigureSpec.")
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--patch", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8-sig"))
    patch = json.loads(args.patch.read_text(encoding="utf-8-sig"))
    validation = validate_patch(patch)
    if validation["status"] != "pass":
        result = {"schema": "originplot.patch_apply_report.v5", "status": "rejected", "validation": validation}
    else:
        candidate = copy.deepcopy(spec)
        for operation in patch["operations"]:
            if operation.get("op") not in {"replace", "add"}:
                result = {"schema": "originplot.patch_apply_report.v5", "status": "rejected", "reason": "unsupported_op", "operation": operation}
                break
            set_path(candidate, operation["path"], operation.get("value"))
        else:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = {"schema": "originplot.patch_apply_report.v5", "status": "pass", "operation_count": len(patch["operations"])}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
