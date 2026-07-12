from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import struct
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check_import(module_name: str) -> dict[str, Any]:
    try:
        module = __import__(module_name)
        version = getattr(module, "__version__", None)
        return {"name": module_name, "status": "pass", "version": version}
    except Exception as exc:
        return {"name": module_name, "status": "not_available", "error": str(exc)}


def generated_capabilities(status: str, fingerprint: str, probes: dict[str, bool]) -> dict[str, Any]:
    source = "origin_doctor live_originpro operation probe" if status == "pass" else "origin_doctor did not verify route"

    def cap(op: str, probe_name: str) -> dict[str, Any]:
        verified = bool(probes.get(probe_name))
        return {"verified": verified, "source": source if verified else f"probe {probe_name} did not pass"}

    return {
        "schema": "originplot.capabilities.v5",
        "environment": {
            "origin_version": "2022",
            "fingerprint": fingerprint,
            "policy": "generated_by_origin_doctor_live_originpro" if status == "pass" else "fail_closed_until_live_doctor_passes",
        },
        "adapters": {
            "originpro": {
                "origin_version": "2022",
                "module": str((Path(__file__).resolve().parents[1] / "adapters" / "originpro" / "adapter.py").resolve()),
                "operations": {
                    "session.start_clean": cap("session.start_clean", "session"),
                    "session.assert_capabilities": cap("session.assert_capabilities", "session"),
                    "workbook.create": cap("workbook.create", "workbook"),
                    "worksheet.import": cap("worksheet.import", "import"),
                    "graph.create": cap("graph.create", "graph"),
                    "layer.configure": cap("layer.configure", "layer_geometry"),
                    "plot.add.line": cap("plot.add.line", "line_plot"),
                    "plot.style.apply": cap("plot.style.apply", "style_readback"),
                    "axis.configure": cap("axis.configure", "axis_readback"),
                    "axis.verify_final": cap("axis.verify_final", "axis_readback"),
                    "graph.export.presave": cap("graph.export.presave", "export"),
                    "project.save": cap("project.save", "save"),
                    "session.release": cap("session.release", "release"),
                },
            },
            "inspection": {
                "origin_version": "2022",
                "module": str((Path(__file__).resolve().parents[1] / "adapters" / "inspection" / "adapter.py").resolve()),
                "operations": {
                    "project.reopen.clean": cap("project.reopen.clean", "reopen"),
                    "project.inspect": cap("project.inspect", "inspect"),
                    "graph.export.postreopen": cap("graph.export.postreopen", "reopen"),
                },
            },
            "evidence_qa": {
                "module": str((Path(__file__).resolve().parents[1] / "adapters" / "evidence_qa" / "adapter.py").resolve()),
                "operations": {
                    op: {"verified": True, "source": "local deterministic QA adapter"}
                    for op in ["qa.structure.compare", "qa.serialization.compare", "qa.image.compare", "manifest.finalize"]
                },
            },
        },
    }


def run_doctor(output_dir: Path, *, mode: str = "offline") -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    offline = mode == "offline"
    checks: list[dict[str, Any]] = []
    checks.append({"name": "windows", "status": "pass" if platform.system() == "Windows" else "warning", "value": platform.platform()})
    checks.append({"name": "python_bitness", "status": "pass", "value": struct.calcsize("P") * 8})
    checks.append({"name": "output_dir_writable", "status": "pass" if output_dir.exists() else "fail", "path": str(output_dir)})
    checks.append(check_import("originpro"))
    checks.append(check_import("OriginExt"))
    checks.append({"name": "mcp_server", "status": "skipped" if mode != "live_mcp" else "not_checked", "reason": "configure endpoint before live probe"})
    checks.append({"name": "bridge", "status": "skipped" if mode != "live_mcp" else "not_checked", "reason": "configure bridge token before live probe"})
    probes = {
        "session": False,
        "graph": False,
        "export": False,
        "save": False,
        "release": False,
        "workbook": False,
        "import": False,
        "line_plot": False,
        "style_readback": False,
        "axis_readback": False,
        "layer_geometry": False,
        "reopen": False,
        "inspect": False,
    }
    if mode == "live_originpro":
        smoke_status = output_dir / "origin_attach_smoke_status.json"
        smoke = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parent / "origin_attach_smoke.py"),
                "--new-hidden",
                "--status-json",
                str(smoke_status),
                "--phase-timeout-seconds",
                "45",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=80,
        )
        checks.append(
            {
                "name": "opju_save_reopen_smoke",
                "status": "pass" if smoke.returncode == 0 else "fail",
                "returncode": smoke.returncode,
                "status_json": str(smoke_status),
            }
        )
        if smoke.returncode == 0 and smoke_status.exists():
            smoke_payload = json.loads(smoke_status.read_text(encoding="utf-8-sig"))
            steps = set(smoke_payload.get("steps") or [])
            probes["session"] = "new" in steps or "attach" in steps
            probes["graph"] = "new_graph" in steps
            probes["export"] = bool(smoke_payload.get("png_exists"))
            probes["save"] = bool(smoke_payload.get("opju_exists"))
            probes["release"] = bool(smoke_payload.get("release"))
    else:
        checks.append({"name": "opju_save_reopen_smoke", "status": "skipped", "reason": "offline mode only proves planning readiness"})
    critical = [item for item in checks if item["name"] in {"windows", "python_bitness", "output_dir_writable"}]
    live_checks = [item for item in checks if item["name"] == "opju_save_reopen_smoke"]
    if mode == "offline":
        status = "planning_ready" if all(item["status"] == "pass" for item in critical) else "fail"
    else:
        status = "pass" if all(item["status"] == "pass" for item in critical + live_checks) else "fail"
    imports = {item["name"]: item for item in checks if item.get("name") in {"originpro", "OriginExt"}}
    fingerprint_components = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "python_bitness": struct.calcsize("P") * 8,
        "mode": mode,
        "originpro_version": imports.get("originpro", {}).get("version"),
        "OriginExt_version": imports.get("OriginExt", {}).get("version"),
    }
    fingerprint_src = json.dumps(fingerprint_components, sort_keys=True)
    fingerprint = hashlib.sha256(fingerprint_src.encode("utf-8")).hexdigest()
    result = {
        "schema": "originplot.doctor.v2",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "mode": mode,
        "environment_fingerprint": fingerprint,
        "fingerprint_components": fingerprint_components,
        "checks": checks,
        "verified_routes": [key for key, value in probes.items() if value],
    }
    if mode == "live_originpro":
        caps = generated_capabilities(status, fingerprint, probes)
        caps_path = output_dir / "generated_capabilities.json"
        write_json(caps_path, caps)
        result["generated_capabilities"] = str(caps_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OriginPlot v5 doctor checks.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/origin_doctor"))
    parser.add_argument("--mode", choices=["offline", "live_originpro", "live_mcp", "live_hybrid"], default="offline")
    parser.add_argument("--offline", action="store_true", help="Run non-invasive planning checks without launching Origin.")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = run_doctor(args.output_dir, mode="offline" if args.offline else args.mode)
    if args.json_out:
        write_json(args.json_out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"pass", "planning_ready"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
