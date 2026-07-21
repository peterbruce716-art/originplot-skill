from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from originplot.runtime.origin_session import attached_origin, is_administrator


def _nonblank(path: Path) -> bool:
    try:
        from PIL import Image, ImageStat

        with Image.open(path).convert("RGB") as image:
            stat = ImageStat.Stat(image)
            return image.width > 10 and image.height > 10 and sum(stat.mean) > 15.0
    except Exception:
        return False


def _no_demo_watermark(path: Path) -> bool:
    try:
        from PIL import Image

        with Image.open(path).convert("RGB") as image:
            resized = image.resize((160, 120))
            pixels = list(resized.get_flattened_data()) if hasattr(resized, "get_flattened_data") else list(resized.getdata())
        cyan = sum(1 for red, green, blue in pixels if red < 100 and green > 180 and blue > 200 and abs(green - blue) < 70)
        return cyan / max(len(pixels), 1) <= 0.0005
    except Exception:
        return False


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _result(profile: dict[str, Any]) -> dict[str, Any]:
    visual_required = profile.get("visual_qa") != "off"
    return {
        "schema": "originplot.origin_worker_result.v1",
        "profile": profile.get("name"),
        "mode": "live",
        "command_success": False,
        "structure_pass": False,
        "visual_pass": False,
        "live_origin_verified": False,
        "pass_eligible": False,
        "overall_status": "failed",
        "build_success": False,
        "reopen_success": False,
        "editable_plot_count": 0,
        "worksheet_binding_ok": False,
        "export_nonblank": False,
        "demo_watermark_detected": False,
        "warnings": [],
        "gate_results": {},
        "gates": {
            "opju_saved": "required",
            "opju_reopened": "required",
            "editable_plot_present": "required",
            "worksheet_binding": "required",
            "origin_export_nonblank": "required",
            "demo_watermark_absent": "required",
            "visual_comparison": "required" if visual_required else "not_required",
            "provenance": "required" if profile.get("name") == "release" else "not_required",
            "hash_chain": "required" if profile.get("name") == "release" else "not_required",
            "release_evidence": "required" if profile.get("name") == "release" else "not_required",
        },
    }


def run(
    task_path: Path,
    *,
    op_module: Any | None = None,
    session_factory: Callable[[Any], Any] | None = None,
    admin_check: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    task = json.loads(task_path.read_text(encoding="utf-8-sig"))
    if task.get("schema") != "originplot.origin_worker_task.v1":
        raise ValueError("unsupported origin worker task schema")
    profile = task.get("profile") or {}
    output_dir = Path(task["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result = _result(profile)
    if str(profile.get("name")) == "release":
        result.update({"error_code": "E440_RELEASE_ROUTE_MISMATCH", "message": "release is executed by the strict legacy worker"})
    elif str(task.get("builder")) != "generic_line":
        result.update({"error_code": "E440_PLOT_FAMILY_NOT_IMPLEMENTED", "message": "profile worker currently supports builder generic_line only"})
    elif not isinstance(task.get("data_payload"), dict):
        result.update({"error_code": "E305_DATA_ROLES_MISSING", "message": "controller must provide validated data_payload"})
    elif not (admin_check or is_administrator)():
        result.update({"error_code": "E120_ENVIRONMENT_MISMATCH", "message": "Origin worker requires an administrator process; controller remains non-admin", "origin_attach_not_attempted": True})
    else:
        try:
            if op_module is None:
                import originpro as op_module
            session = session_factory or attached_origin
            data = task["data_payload"]
            if len(data.get("x", [])) < 2 or len(data.get("x", [])) != len(data.get("y", [])):
                raise RuntimeError("E301_FIGURE_DATA_INVALID: x/y arrays must have equal length and at least two rows")
            figure_id = str(data["figure_id"])
            book_name = f"{figure_id}_Data"
            opju = output_dir / "candidate.opju"
            export = output_dir / "candidate_export.png"
            with session(op_module) as identity:
                op_module.new(asksave=False)
                book = op_module.new_book("w", lname=book_name)
                sheet = book[0]
                sheet.from_list(0, list(data["x"]), lname=str(data["x_name"]), axis="X")
                sheet.from_list(1, list(data["y"]), lname=str(data["y_name"]), axis="Y")
                selected_template = (task.get("template_decision") or {}).get("selected") or {}
                template = str(selected_template.get("path") or "LINE")
                page = op_module.new_graph(lname=figure_id, template=template, hidden=True)
                layer = page[0]
                plot = layer.add_plot(sheet, colx=0, coly=1, type="line")
                style = data.get("style") or {}
                if style.get("line_color"):
                    try:
                        plot.color = str(style["line_color"])
                    except Exception:
                        pass
                if style.get("line_width_pt") is not None:
                    for prop in ("line.width", "linewidth", "width"):
                        try:
                            plot.set_float(prop, float(style["line_width_pt"]))
                            break
                        except Exception:
                            continue
                result["build_success"] = True
                result["template_used"] = template
                try:
                    layer.rescale()
                except Exception:
                    pass
                try:
                    page.show = True
                except Exception:
                    pass
                op_module.save(str(opju))
                result["gate_results"]["opju_saved"] = "pass" if opju.is_file() else "failed"
                if not opju.is_file():
                    raise RuntimeError("E501_OPJU_SAVE_FAILED: Origin did not create the OPJU")
                try:
                    page.save_fig(str(export), type="png", replace=True, width=1600)
                except TypeError:
                    page.save_fig(str(export), type="png", replace=True)
                if not op_module.open(str(opju), readonly=False, asksave=False):
                    raise RuntimeError("E502_OPJU_REOPEN_FAILED: Origin could not reopen the OPJU")
                result["gate_results"]["opju_reopened"] = "pass"
                result["reopen_success"] = True
                pages = list(op_module.pages("g"))
                reopened_page = next((item for item in pages if str(getattr(item, "lname", "")) == figure_id or str(getattr(item, "name", "")) == figure_id), None)
                if reopened_page is None:
                    raise RuntimeError("E503_GRAPH_PAGE_MISSING: reopened graph page is absent")
                result["gate_results"]["editable_plot_present"] = "pass"
                reopened_layer = reopened_page[0]
                plots = list(reopened_layer.plot_list())
                result["editable_plot_count"] = len(plots)
                if not plots:
                    raise RuntimeError("E504_PLOT_MISSING: reopened graph has no editable plot")
                binding = getattr(plots[0], "lt_range", "")
                if callable(binding):
                    binding = binding()
                binding = str(binding or "").strip()
                result["gate_results"]["worksheet_binding"] = "pass" if binding and f"[{book_name}]" in binding and "!" in binding else "failed"
                result["worksheet_binding_ok"] = result["gate_results"]["worksheet_binding"] == "pass"
                if not result["gate_results"]["worksheet_binding"] == "pass":
                    raise RuntimeError("E505_WORKSHEET_BINDING_MISSING: plot has no direct worksheet binding")
                try:
                    reopened_page.save_fig(str(export), type="png", replace=True, width=1600)
                except TypeError:
                    reopened_page.save_fig(str(export), type="png", replace=True)
                result["gate_results"]["origin_export_nonblank"] = "pass" if _nonblank(export) else "failed"
                result["gate_results"]["demo_watermark_absent"] = "pass" if _no_demo_watermark(export) else "failed"
                result["export_nonblank"] = result["gate_results"]["origin_export_nonblank"] == "pass"
                result["demo_watermark_detected"] = result["gate_results"]["demo_watermark_absent"] != "pass"
                op_module.save(str(opju))
                result["origin_session"] = identity
                result["readback"] = {"graph_pages": len(pages), "plot_count": len(plots), "binding": binding, "export": str(export)}
            result["live_origin_verified"] = True
            result["structure_pass"] = all(result["gate_results"].get(name) == "pass" for name in ("opju_saved", "opju_reopened", "editable_plot_present", "worksheet_binding"))
            result["visual_pass"] = False
            result["command_success"] = result["structure_pass"] and result["gate_results"].get("origin_export_nonblank") == "pass" and result["gate_results"].get("demo_watermark_absent") == "pass"
            result["overall_status"] = "completed" if result["command_success"] else "failed"
            _write(output_dir / "candidate_readback.json", result.get("readback") or {})
        except Exception as exc:
            result.update({"error_code": getattr(exc, "code", "E525_ORIGIN_WORKER_FAILED"), "message": str(exc)})
    _write(output_dir / "candidate_summary.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Administrator-only OriginPlot worker protocol endpoint.")
    parser.add_argument("--task", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = run(args.task)
    except Exception as exc:
        result = {"status": "failed", "overall_status": "failed", "error_code": "E525_ORIGIN_WORKER_FAILED", "message": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("command_success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
