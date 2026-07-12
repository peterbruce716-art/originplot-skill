"""Read Fig12 axis font properties from the currently visible Origin session."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import originpro as op


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result: dict[str, object] = {"attached": False, "layers": []}
    op.attach()
    try:
        result["attached"] = True
        pages = list(op.pages("g"))
        if not pages:
            raise RuntimeError("No graph page is open in the visible Origin session")
        page = pages[-1]
        result["page"] = getattr(page, "lname", "")
        result["font_indices"] = {}
        for font_name in ("Arial", "Times New Roman", "Courier New"):
            try:
                result["font_indices"][font_name] = op.lt_float(f"font({font_name})")
            except Exception as exc:
                result["font_indices"][font_name] = {"error": type(exc).__name__}
        layer_records: list[dict[str, object]] = []
        for index, layer in enumerate(page):
            if index >= 3:
                break
            layer.activate()
            record: dict[str, object] = {"index": index}
            for expression in (
                "layer.x.label.font",
                "layer.y.label.font",
                "layer.x.label.fsize",
                "layer.y.label.fsize",
                "xb.font",
                "yl.font",
                "xb.fsize",
                "yl.fsize",
                "xb.x1",
                "xb.y1",
                "yl.x1",
                "yl.y1",
                "xb.rotate",
                "yl.rotate",
                "xb.attach",
                "yl.attach",
            ):
                try:
                    record[expression] = op.lt_float(expression)
                except Exception as exc:
                    record[expression] = {"error": type(exc).__name__}
            for object_name in ("xb", "yl"):
                variable = f"__fig12_{object_name}_{index}$"
                try:
                    op.lt_exec(f"string {variable}={object_name}.text$;")
                    record[f"{object_name}.text"] = op.get_lt_str(variable)
                except Exception as exc:
                    record[f"{object_name}.text"] = {"error": type(exc).__name__}
            layer_records.append(record)
        result["layers"] = layer_records
    finally:
        op.detach()
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
