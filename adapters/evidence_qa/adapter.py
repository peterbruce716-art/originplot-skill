from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.artifact_manifest import note_operation, read_artifacts, update_artifacts  # noqa: E402


class Adapter:
    route = "evidence_qa"

    OPERATIONS = {
        "qa.structure.compare",
        "qa.serialization.compare",
        "qa.image.compare",
        "qa.semantic_benchmark",
        "qa.deviation_ledger.generate",
        "manifest.finalize",
    }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def supports(self, operation: dict[str, Any]) -> bool:
        return operation.get("adapter_route") == self.route and operation.get("operation_id") in self.OPERATIONS

    def execute(self, operation: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        operation_id = str(operation.get("operation_id"))
        run_dir = Path(context.get("run_dir") or ".").resolve()
        artifacts_path = Path(context.get("artifact_manifest") or run_dir / "run_artifacts.json").resolve()
        run_id = str(context.get("run_id") or run_dir.name)
        artifacts = read_artifacts(artifacts_path, run_id=run_id)
        if operation_id == "qa.structure.compare":
            result = self._structure(artifacts)
        elif operation_id == "qa.serialization.compare":
            result = self._serialization(artifacts)
        elif operation_id == "qa.image.compare":
            result = self._image(artifacts)
        elif operation_id == "qa.semantic_benchmark":
            result = self._semantic_benchmark(operation, run_dir, artifacts_path, run_id)
        elif operation_id == "qa.deviation_ledger.generate":
            result = self._deviation_ledger(run_dir)
        else:
            result = self._finalize(run_dir)
        note_operation(context, operation, result["status"], result)
        report_path = run_dir / "qa_report.json"
        report = read_json(report_path) if report_path.exists() else {"schema": "originplot.qa_report.v1", "status": "incomplete", "checks": []}
        report.setdefault("checks", []).append({"operation_id": operation_id, **result})
        report["status"] = "failed" if any(item.get("status") == "failed" for item in report["checks"]) else "pass"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        update_artifacts(artifacts_path, run_id, {"qa_report": {"path": str(report_path), "exists": True, "size_bytes": report_path.stat().st_size}})
        return result

    def _structure(self, artifacts: dict[str, Any]) -> dict[str, Any]:
        inspection = artifacts.get("inspection") or {}
        payload = read_json(Path(str(inspection.get("path")))) if inspection.get("path") else {}
        status = "completed" if payload.get("status") == "pass" else "failed"
        return {"status": status, "inspection_status": payload.get("status"), "inspection": inspection}

    def _serialization(self, artifacts: dict[str, Any]) -> dict[str, Any]:
        pre = artifacts.get("pre_save_export") or {}
        post = artifacts.get("post_reopen_export") or {}
        pre_metrics = image_metrics(pre.get("path"))
        post_metrics = image_metrics(post.get("path"))
        comparison = compare_images(pre.get("path"), post.get("path"))
        ok = bool(pre.get("exists")) and bool(post.get("exists")) and comparison.get("status") == "pass"
        return {
            "status": "completed" if ok else "failed",
            "pre_save": pre,
            "post_reopen": post,
            "pre_metrics": pre_metrics,
            "post_metrics": post_metrics,
            "comparison": comparison,
        }

    def _image(self, artifacts: dict[str, Any]) -> dict[str, Any]:
        post = artifacts.get("post_reopen_export") or {}
        metrics = image_metrics(post.get("path"))
        ok = bool(post.get("exists")) and int(post.get("size_bytes") or 0) > 512 and metrics.get("nonwhite_bbox") is not None
        return {"status": "completed" if ok else "failed", "post_reopen": post, "post_metrics": metrics}

    def _semantic_benchmark(self, operation: dict[str, Any], run_dir: Path, artifacts_path: Path, run_id: str) -> dict[str, Any]:
        benchmark_value = ((operation.get("payload") or {}).get("benchmark") or {}).get("path")
        if not benchmark_value:
            return {"status": "failed", "error_code": "semantic_benchmark_path_missing"}
        benchmark_path = Path(str(benchmark_value))
        if not benchmark_path.is_absolute():
            benchmark_path = (run_dir / benchmark_path).resolve()
        report_path = run_dir / "semantic_benchmark_report.json"
        ledger_path = run_dir / "deviation_ledger.json"
        evidence_dir = run_dir / "semantic_benchmark_evidence"
        import subprocess

        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "semantic_figure_benchmark.py"),
                "--benchmark",
                str(benchmark_path),
                "--out-dir",
                str(evidence_dir),
                "--report-out",
                str(report_path),
                "--ledger-out",
                str(ledger_path),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        report = read_json(report_path) if report_path.exists() else {}
        update_artifacts(
            artifacts_path,
            run_id,
            {
                "semantic_benchmark_report": {"path": str(report_path), "exists": report_path.exists(), "size_bytes": report_path.stat().st_size if report_path.exists() else 0},
                "deviation_ledger": {"path": str(ledger_path), "exists": ledger_path.exists(), "size_bytes": ledger_path.stat().st_size if ledger_path.exists() else 0},
            },
        )
        return {
            "status": "completed" if completed.returncode == 0 else "failed",
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "semantic_status": report.get("status"),
            "report": str(report_path),
            "ledger": str(ledger_path),
        }

    def _deviation_ledger(self, run_dir: Path) -> dict[str, Any]:
        ledger_path = run_dir / "deviation_ledger.json"
        if not ledger_path.exists():
            return {"status": "failed", "error_code": "deviation_ledger_missing", "ledger": str(ledger_path)}
        ledger = read_json(ledger_path)
        blocking = ledger.get("blocking", []) if isinstance(ledger.get("blocking"), list) else []
        return {"status": "completed" if not blocking else "failed", "ledger": str(ledger_path), "blocking_failures": len(blocking)}

    def _finalize(self, run_dir: Path) -> dict[str, Any]:
        report_path = run_dir / "qa_report.json"
        report = read_json(report_path) if report_path.exists() else {"checks": []}
        failed = [item for item in report.get("checks", []) if item.get("status") == "failed"]
        return {"status": "completed" if not failed else "failed", "failed_checks": len(failed)}

    def close(self) -> None:
        return None


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def image_metrics(path_value: Any) -> dict[str, Any]:
    if not path_value:
        return {"exists": False}
    path = Path(str(path_value))
    if not path.exists():
        return {"exists": False, "path": str(path)}
    from PIL import Image

    with Image.open(path) as image:
        image_format = image.format
        rgba = image.convert("RGBA")
        width, height = rgba.size
        pixels = list(rgba.getdata())
    nonwhite = [
        (index % width, index // width)
        for index, (r, g, b, a) in enumerate(pixels)
        if a > 0 and (r < 250 or g < 250 or b < 250)
    ]
    bbox = None
    if nonwhite:
        xs = [item[0] for item in nonwhite]
        ys = [item[1] for item in nonwhite]
        bbox = [min(xs), min(ys), max(xs), max(ys)]
    return {
        "exists": True,
        "format": image_format,
        "width": width,
        "height": height,
        "mode": "RGBA",
        "nonwhite_ratio": len(nonwhite) / max(1, width * height),
        "nonwhite_bbox": bbox,
    }


def compare_images(pre_path: Any, post_path: Any) -> dict[str, Any]:
    if not pre_path or not post_path:
        return {"status": "failed", "reason": "missing image path"}
    pre = Path(str(pre_path))
    post = Path(str(post_path))
    if not pre.exists() or not post.exists():
        return {"status": "failed", "reason": "missing image file"}
    from PIL import Image

    with Image.open(pre) as pre_image, Image.open(post) as post_image:
        pre_rgb = pre_image.convert("RGB")
        post_rgb = post_image.convert("RGB")
        if pre_rgb.size != post_rgb.size:
            return {"status": "failed", "reason": "dimension_mismatch", "pre_size": pre_rgb.size, "post_size": post_rgb.size}
        pre_pixels = list(pre_rgb.getdata())
        post_pixels = list(post_rgb.getdata())
    total = len(pre_pixels) * 3
    mae = sum(abs(a - b) for pa, pb in zip(pre_pixels, post_pixels) for a, b in zip(pa, pb)) / max(1, total) / 255.0
    return {"status": "pass" if mae <= 0.02 else "failed", "mean_abs_error_0_1": mae, "pre_size": pre_rgb.size, "post_size": post_rgb.size}


def create_adapter(config: dict[str, Any]) -> Adapter:
    return Adapter(config)
