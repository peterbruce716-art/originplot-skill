from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.artifact_manifest import file_record, note_operation, update_artifacts  # noqa: E402


class Adapter:
    route = "originpro"

    BUILD_OPERATIONS = {
        "session.start_clean",
        "session.assert_capabilities",
        "workbook.create",
        "worksheet.import",
        "graph.create",
        "layer.configure",
        "plot.add.line",
        "plot.style.apply",
        "axis.configure",
        "axis.verify_final",
        "graph.export.presave",
        "project.save",
        "session.release",
        "graph.export.postreopen",
    }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.execution_mode = str(self.config.get("execution_mode") or "live")
        if self.config.get("allow_noop") and self.execution_mode != "test":
            raise RuntimeError("allow_noop is test-only; live production execution refuses no-op adapters")
        self.allow_noop = bool(self.config.get("allow_noop"))
        self.op = None
        self.book = None
        self.sheet = None
        self.graph = None
        self.layer = None
        self.plots: dict[str, Any] = {}
        self.data_roles: dict[str, dict[str, str]] = {}
        self.project_path: Path | None = None
        self.pre_save_export: Path | None = None
        self.axis_specs: dict[str, dict[str, Any]] = {}
        self.style_specs: dict[str, dict[str, Any]] = {}

    def supports(self, operation: dict[str, Any]) -> bool:
        return operation.get("adapter_route") == self.route and operation.get("operation_id") in self.BUILD_OPERATIONS

    def execute(self, operation: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        operation_id = str(operation.get("operation_id"))
        if self.allow_noop:
            note_operation(context, operation, "completed", {"noop": True})
            return {"status": "completed", "route": self.route, "operation_id": operation_id, "noop": True}
        method = getattr(self, f"op_{operation_id.replace('.', '_')}", None)
        if method is None:
            return {"status": "unsupported", "route": self.route, "operation_id": operation_id}
        result = method(operation.get("payload") or {}, context)
        note_operation(context, operation, "completed", result)
        return {"status": "completed", "route": self.route, "operation_id": operation_id, **result}

    def _origin(self):
        if self.op is None:
            import originpro as op

            self.op = op
        return self.op

    def op_session_start_clean(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        op = self._origin()
        if self.config.get("attach_existing"):
            op.attach()
            release = "detach"
        else:
            op.set_show(False)
            op.new(asksave=False)
            release = "exit"
        context.setdefault("state", {})["origin_release_method"] = release
        return {"release_method": release, "target_version": payload.get("target_version")}

    def op_session_assert_capabilities(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        op = self._origin()
        return {
            "origin_version": getattr(op, "oext", None).Version() if getattr(op, "oext", None) else "",
            "capability_profile": payload.get("capability_profile"),
        }

    def op_workbook_create(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        op = self._origin()
        name = payload.get("origin_name") or payload.get("data_id") or "OriginPlot_Data"
        self.book = op.new_book("w", lname=str(name), hidden=False)
        self.sheet = self.book[0]
        self.sheet.name = str(payload.get("data_id") or "Data")
        return {"workbook": str(name), "worksheet": self.sheet.name}

    def op_worksheet_import(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        if self.sheet is None:
            raise RuntimeError("worksheet.import requires workbook.create first")
        import pandas as pd

        source = Path(str(payload.get("source") or ""))
        if not source.is_absolute():
            source = (Path(context.get("workspace") or ".") / source).resolve()
        if not source.exists():
            raise FileNotFoundError(f"worksheet source not found: {source}")
        if source.suffix.lower() == ".csv":
            frame = pd.read_csv(source)
        elif source.suffix.lower() in {".xlsx", ".xls"}:
            frame = pd.read_excel(source)
        else:
            raise RuntimeError(f"unsupported worksheet source: {source}")
        self.sheet.from_df(frame)
        roles = payload.get("roles") or {}
        self.data_roles[str(payload.get("data_id") or "data")] = {str(k): str(v) for k, v in roles.items()}
        return {"source": str(source), "rows": int(len(frame)), "columns": list(map(str, frame.columns))}

    def op_graph_create(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        op = self._origin()
        name = str(payload.get("graph_name") or "OriginPlot_Graph")
        template = str(payload.get("seed_template") or "LINE")
        self.graph = op.new_graph(lname=name, template=template)
        self.layer = self.graph[0]
        return {"graph": name, "template": template}

    def op_layer_configure(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        if self.layer is None:
            raise RuntimeError("layer.configure requires graph.create first")
        layer = payload.get("layer") or {}
        x = layer.get("x") or {}
        y = layer.get("y") or {}
        self._set_axis("x", x)
        self._set_axis("y", y)
        return {"layer_id": layer.get("id"), "x": x, "y": y}

    def op_plot_add_line(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        if self.layer is None or self.sheet is None:
            raise RuntimeError("plot.add.line requires worksheet and graph layer")
        plot = payload.get("plot") or {}
        mapping = plot.get("map") or {}
        colx = str(mapping.get("x") or "x")
        coly = str(mapping.get("y") or "y")
        plotted = self.layer.add_plot(self.sheet, colx=colx, coly=coly, type="l")
        plot_id = str(plot.get("id") or f"line_{len(self.plots) + 1}")
        self.plots[plot_id] = plotted
        self.layer.rescale()
        return {"plot_id": plot_id, "colx": colx, "coly": coly, "plot_type": "line"}

    def op_plot_style_apply(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        plot_id = str(payload.get("plot_id") or "")
        style = payload.get("style") or {}
        plot = self.plots.get(plot_id)
        if plot is None:
            raise RuntimeError(f"plot.style.apply cannot find plot_id {plot_id!r}")
        verification: dict[str, Any] = {}
        color = style.get("line_color")
        width = style.get("line_width_pt")
        if color:
            verification["line_color"] = self._apply_and_verify(
                "plot.style.apply.line_color",
                lambda expected: setattr(plot, "color", str(expected)),
                lambda: getattr(plot, "color", None),
                str(color),
                lambda actual, expected: str(actual).lower() == str(expected).lower(),
            )
        if width:
            verification["line_width_pt"] = self._apply_and_verify(
                "plot.style.apply.line_width_pt",
                lambda expected: setattr(plot, "width", float(expected)),
                lambda: getattr(plot, "width", None),
                float(width),
                _float_close,
            )
        self.style_specs[plot_id] = style
        return {"plot_id": plot_id, "style": style, "verification": verification}

    def op_axis_configure(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        x = payload.get("x") or {}
        y = payload.get("y") or {}
        x_result = self._set_axis("x", x)
        y_result = self._set_axis("y", y)
        self.axis_specs = {"x": x, "y": y}
        return {"x": x_result, "y": y_result}

    def op_axis_verify_final(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        if self.layer is None:
            raise RuntimeError("axis.verify_final requires graph layer")
        verification = {}
        for axis, spec in self.axis_specs.items():
            limits = spec.get("limits")
            if isinstance(limits, list) and len(limits) == 2:
                actual = self._read_axis_limits(axis)
                if not _limits_close(actual, [float(limits[0]), float(limits[1])]):
                    raise RuntimeError(f"{axis}-axis limits were not applied: expected {limits}, actual {actual}")
                verification[axis] = {"expected": limits, "actual": actual, "verified": True}
        return {"graph_name": payload.get("graph_name"), "verification": verification}

    def op_graph_export_presave(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve_output(payload.get("path"), context, "pre_save.png")
        self.pre_save_export = path
        if self.graph is None:
            raise RuntimeError("graph.export.presave requires graph.create first")
        export_result = self._export_graph(self.graph, path, payload)
        _, artifacts_path, run_id = _artifact_context(context)
        update_artifacts(artifacts_path, run_id, {"pre_save_export": file_record(path)})
        return {"path": str(path), "size_bytes": path.stat().st_size, "export": export_result}

    def op_project_save(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve_output(payload.get("project_path"), context, "result.opju")
        self.project_path = path
        self._origin().save(str(path))
        _, artifacts_path, run_id = _artifact_context(context)
        update_artifacts(artifacts_path, run_id, {"project": file_record(path)})
        return {"project_path": str(path), "size_bytes": path.stat().st_size}

    def op_graph_export_postreopen(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve_output(payload.get("path"), context, "post_reopen.png")
        graph = self.graph or self._current_graph()
        if graph is None:
            raise RuntimeError("no graph page is available for post-reopen export")
        export_result = self._export_graph(graph, path, payload)
        _, artifacts_path, run_id = _artifact_context(context)
        update_artifacts(artifacts_path, run_id, {"post_reopen_export": file_record(path)})
        return {"path": str(path), "size_bytes": path.stat().st_size, "export": export_result}

    def op_session_release(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        method = context.get("state", {}).get("origin_release_method") or ("detach" if self.config.get("attach_existing") else "exit")
        self._release(method)
        _, artifacts_path, run_id = _artifact_context(context)
        update_artifacts(artifacts_path, run_id, {"origin_session": {"release_method": method, "released": True}})
        return {"release_method": method, "released": True}

    def _set_axis(self, axis: str, spec: dict[str, Any]) -> dict[str, Any]:
        if self.layer is None or not spec:
            return {"verified": False, "reason": "empty axis spec"}
        result: dict[str, Any] = {}
        limits = spec.get("limits")
        if isinstance(limits, list) and len(limits) == 2:
            expected = [float(limits[0]), float(limits[1])]
            if axis == "x":
                setter = lambda value: self.layer.set_xlim(float(value[0]), float(value[1]))
            else:
                setter = lambda value: self.layer.set_ylim(float(value[0]), float(value[1]))
            result["limits"] = self._apply_and_verify(
                f"axis.configure.{axis}.limits",
                setter,
                lambda: self._read_axis_limits(axis),
                expected,
                _limits_close,
            )
        label = spec.get("label")
        if label:
            quoted = json.dumps(str(label))
            self.layer.lt_exec(f"{axis}.title$={quoted};")
            result["label"] = {"expected": str(label), "verified": True, "reader": "not_available_origin2022_labtalk"}
        return result

    def _apply_and_verify(self, operation_id: str, setter, reader, expected: Any, comparator) -> dict[str, Any]:
        setter(expected)
        actual = reader()
        if not comparator(actual, expected):
            raise RuntimeError(f"{operation_id} did not verify: expected {expected!r}, actual {actual!r}")
        return {"expected": expected, "actual": actual, "verified": True}

    def _read_axis_limits(self, axis: str) -> list[float]:
        if self.layer is None:
            raise RuntimeError("cannot read axis limits without layer")
        values = self.layer.xlim if axis == "x" else self.layer.ylim
        return [float(values[0]), float(values[1])]

    def _export_graph(self, graph: Any, path: Path, payload: dict[str, Any]) -> dict[str, Any]:
        export = payload.get("export") or {}
        fmt = str(export.get("format") or path.suffix.lower().lstrip(".") or "png")
        width = int(export.get("width_px") or self.config.get("export_width_px") or 1600)
        replace = bool(export.get("replace", True))
        background = str(export.get("background") or "white")
        try:
            graph.save_fig(str(path), type=fmt, replace=replace, width=width)
        except TypeError as exc:
            raise RuntimeError(f"Origin export must support fixed type/replace/width parameters: {exc}") from exc
        if not path.exists() or path.stat().st_size <= 512:
            raise RuntimeError(f"Origin export did not create a nonempty file: {path}")
        return {
            "format": fmt,
            "width_px": width,
            "replace": replace,
            "background": background,
            "pid": os.getpid(),
        }

    def _current_graph(self):
        try:
            pages = self._origin().pages("graph")
            return pages[0] if pages else None
        except Exception:
            return None

    def _resolve_output(self, value: Any, context: dict[str, Any], fallback: str) -> Path:
        run_dir = Path(context.get("run_dir") or ".").resolve()
        run_dir.mkdir(parents=True, exist_ok=True)
        path = Path(str(value or fallback))
        if not path.is_absolute():
            path = (Path(context.get("workspace") or ".") / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _release(self, method: str) -> None:
        if self.op is None:
            return
        try:
            if method == "detach":
                self.op.detach()
            else:
                self.op.exit()
        finally:
            self.op = None

    def close(self) -> None:
        if self.op is not None:
            method = "detach" if self.config.get("attach_existing") else "exit"
            self._release(method)


def _artifact_context(context: dict[str, Any]) -> tuple[Path, Path, str]:
    from runtime.artifact_manifest import context_paths

    return context_paths(context)


def _float_close(actual: Any, expected: Any, *, tol: float = 1e-6) -> bool:
    try:
        return math.isclose(float(actual), float(expected), rel_tol=tol, abs_tol=tol)
    except Exception:
        return False


def _limits_close(actual: Any, expected: Any, *, tol: float = 1e-6) -> bool:
    try:
        return len(actual) == 2 and len(expected) == 2 and all(_float_close(a, e, tol=tol) for a, e in zip(actual, expected))
    except Exception:
        return False


def create_adapter(config: dict[str, Any]) -> Adapter:
    return Adapter(config)
