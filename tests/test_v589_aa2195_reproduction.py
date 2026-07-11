from __future__ import annotations

import ast
import unittest
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


class FakeOrigin:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def attach(self) -> None:
        self.calls.append(("attach", None))

    def detach(self) -> None:
        self.calls.append(("detach", None))

    def set_show(self, value: bool) -> None:
        self.calls.append(("set_show", value))

    def new(self, asksave: bool = False) -> None:
        self.calls.append(("new", asksave))

    def exit(self) -> None:
        self.calls.append(("exit", None))


class FakePage:
    def __init__(self) -> None:
        self.save_kwargs: dict[str, object] = {}
        self.commands: list[str] = []

    def lt_exec(self, command: str) -> None:
        self.commands.append(command)

    def save_fig(self, path: str, **kwargs: object) -> str:
        self.save_kwargs = dict(kwargs)
        Path(path).write_bytes(b"fake-png")
        return path


class FakePlot:
    def __init__(self) -> None:
        self.properties: dict[str, object] = {}

    def set_int(self, name: str, value: int) -> None:
        self.properties[name] = value

    def set_float(self, name: str, value: float) -> None:
        self.properties[name] = value

    def set_str(self, name: str, value: str) -> None:
        self.properties[name] = value

    def set_cmd(self, *commands: str) -> None:
        self.properties["commands"] = commands


class FakeLabel(FakePlot):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text


class FakeSheet:
    def __init__(self) -> None:
        self.columns: list[tuple[int, list[object], str, str]] = []
        self.matrix = None
        self.xymap = None

    def from_list(self, column: int, values: list[object], lname: str = "", axis: str = "") -> None:
        self.columns.append((column, values, lname, axis))

    def from_np(self, matrix: object) -> None:
        self.matrix = matrix

    def cols_axis(self, axes: str, start: int = 0, end: int = 0, repeat: bool = False) -> None:
        self.axes = (axes, start, end, repeat)

    def lt_range(self, include_book: bool = False) -> str:
        return "[Book1]Sheet1" if include_book else "[Book1]Sheet1"

    @property
    def shape(self) -> tuple[int, int]:
        rows = max((len(values) for _, values, _, _ in self.columns), default=0)
        return rows, len(self.columns)


class FakeBook:
    def __init__(self, book_type: str = "w", lname: str = "") -> None:
        self.sheet = FakeSheet()
        self.book_type = book_type
        self.lname = lname
        self.name = lname

    def __getitem__(self, index: int) -> FakeSheet:
        return self.sheet

    def __iter__(self):
        return iter([self.sheet])


class FakeRawGraphObject:
    def __init__(self, object_type: int) -> None:
        self.object_type = object_type
        self.name = ""
        self.properties: dict[str, float] = {}

    def SetName(self, name: str) -> None:
        self.name = name

    def SetNumProp(self, name: str, value: float) -> None:
        self.properties[name] = value

    def SetX(self, value: float) -> None:
        self.properties["x"] = value

    def SetY(self, value: float) -> None:
        self.properties["y"] = value

    def SetDX(self, value: float) -> None:
        self.properties["dx"] = value

    def SetDY(self, value: float) -> None:
        self.properties["dy"] = value


class FakeGraphObjects:
    def __init__(self) -> None:
        self.created: list[FakeRawGraphObject] = []

    def Add(self, object_type: int) -> FakeRawGraphObject:
        obj = FakeRawGraphObject(object_type)
        self.created.append(obj)
        return obj


class FakeLayer:
    def __init__(self) -> None:
        self.plots: list[FakePlot] = []
        self.labels: list[FakeLabel] = []
        self.commands: list[str] = []
        self.properties: dict[str, object] = {}
        self.obj = type("LayerObject", (), {"GraphObjects": FakeGraphObjects()})()

    def add_plot(self, *args: object, **kwargs: object) -> FakePlot:
        plot = FakePlot()
        self.plots.append(plot)
        if kwargs.get("type") == "column" and isinstance(args[0] if args else None, str) and ":" in str(args[0]):
            self.plots.append(FakePlot())
        return plot

    def plot_list(self) -> list[FakePlot]:
        return self.plots

    def add_mplot(self, *args: object, **kwargs: object) -> FakePlot:
        return self.add_plot(*args, **kwargs)

    def add_label(self, text: str, x: float, y: float) -> FakeLabel:
        label = FakeLabel(text)
        label.properties.update({"x": x, "y": y})
        self.labels.append(label)
        return label

    def set_xlim(self, low: float, high: float) -> None:
        self.properties["xlim"] = (low, high)

    def set_ylim(self, low: float, high: float) -> None:
        self.properties["ylim"] = (low, high)

    def set_float(self, name: str, value: float) -> None:
        self.properties[name] = value

    def lt_exec(self, command: str) -> None:
        self.commands.append(command)

    def activate(self) -> None:
        self.properties["active"] = True

    def rescale(self) -> None:
        self.properties["rescaled"] = True

    def group(self, group: bool = True, begin: int = -1, end: int = -1) -> None:
        self.properties["plot_group"] = (group, begin, end)


class FakeGraphPage:
    def __init__(self) -> None:
        self.layers = [FakeLayer()]
        self.commands: list[str] = []
        self.show_history: list[bool] = []
        self._show = True

    def __getitem__(self, index: int) -> FakeLayer:
        return self.layers[index]

    def add_layer(self) -> FakeLayer:
        layer = FakeLayer()
        self.layers.append(layer)
        return layer

    def lt_exec(self, command: str) -> None:
        self.commands.append(command)

    def activate(self) -> None:
        self.commands.append("activate")

    @property
    def show(self) -> bool:
        return self._show

    @show.setter
    def show(self, value: bool) -> None:
        self._show = bool(value)
        self.show_history.append(bool(value))

    def get_float(self, name: str) -> float:
        if name in {"resx", "resy"}:
            return 600.0
        raise KeyError(name)


class FakeBuilderOrigin:
    def __init__(self) -> None:
        self.page = FakeGraphPage()
        self.books: list[FakeBook] = []
        self.new_book_calls: list[dict[str, object]] = []
        self.new_graph_calls: list[dict[str, object]] = []

    def new_graph(self, **kwargs: object) -> FakeGraphPage:
        self.new_graph_calls.append(dict(kwargs))
        return self.page

    def new_book(self, *args: object, **kwargs: object) -> FakeBook:
        book_type = str(args[0]) if args else "w"
        lname = str(kwargs.get("lname", ""))
        book = FakeBook(book_type=book_type, lname=lname)
        self.books.append(book)
        self.new_book_calls.append({"book_type": book_type, "lname": lname})
        return book


class FakeBuildOrigin(FakeOrigin):
    def save(self, path: str) -> None:
        self.calls.append(("save", path))
        Path(path).write_bytes(b"fake-opju")

    def open(self, path: str, **kwargs: object) -> bool:
        self.calls.append(("open", {"path": path, "kwargs": dict(kwargs)}))
        return True


class FakeInspectOrigin(FakeBuildOrigin):
    def pages(self, *args: object, **kwargs: object) -> list[object]:
        self.calls.append(("pages", {"args": args, "kwargs": dict(kwargs)}))
        return []


class FakeWorksheetReadbackOrigin:
    def __init__(self, worksheet_names: list[str]) -> None:
        self.workbooks = [FakeBook(book_type="w", lname=name) for name in worksheet_names]

    def pages(self, page_type: str) -> list[FakeBook]:
        return self.workbooks if page_type == "w" else []

    def find_book(self, book_type: str, name: str) -> FakeBook | None:
        if book_type != "w":
            return None
        return next((book for book in self.workbooks if name in {book.name, book.lname}), None)


class WorksheetReadbackGateTests(unittest.TestCase):
    def test_required_worksheet_gate_passes_only_when_every_book_is_found(self) -> None:
        from builders.aa2195 import _validate_required_worksheet_books

        origin = FakeWorksheetReadbackOrigin(["Fig12_PSC_data", "Fig12_UC_data"])

        passed = _validate_required_worksheet_books(
            origin,
            ["Fig12_PSC_data", "Fig12_UC_data"],
        )
        failed = _validate_required_worksheet_books(
            origin,
            ["Fig12_PSC_data", "Fig12_UC_data", "Fig12_TR_data"],
        )

        self.assertEqual("ok", passed["status"])
        self.assertEqual([], passed["missing"])
        self.assertEqual("failed", failed["status"])
        self.assertEqual(["Fig12_TR_data"], failed["missing"])

    def test_worksheet_row_budget_is_global_and_fails_above_five_thousand(self) -> None:
        from builders.aa2195 import _validate_worksheet_row_budget

        origin = FakeWorksheetReadbackOrigin(["A", "B"])
        origin.workbooks[0].sheet.from_list(0, list(range(3000)))
        origin.workbooks[1].sheet.from_list(0, list(range(2001)))
        failed = _validate_worksheet_row_budget(origin, ["A", "B"])
        origin.workbooks[1].sheet.columns[0] = (0, list(range(2000)), "", "")
        passed = _validate_worksheet_row_budget(origin, ["A", "B"])

        self.assertEqual("failed", failed["status"])
        self.assertEqual(5001, failed["total_rows"])
        self.assertEqual("ok", passed["status"])
        self.assertEqual(5000, passed["total_rows"])

    def test_direct_worksheet_gate_rejects_matrix_or_unbound_plots(self) -> None:
        from builders.aa2195.readback import validate_direct_worksheet_plot_bindings

        readback = {"layers": [{"index": 0, "plot_details": [{"index": 0, "plot_type_code": 226}]}]}
        result = validate_direct_worksheet_plot_bindings(readback, [])
        self.assertEqual("failed", result["status"])
        self.assertTrue(any(item["property"] == "data_workbook" for item in result["mismatches"]))

    def test_direct_worksheet_gate_requires_xyz_for_type243(self) -> None:
        from builders.aa2195.readback import validate_direct_worksheet_plot_bindings

        plot = {"index": 0, "plot_type_code": 243, "data_workbook": "Book1", "data_worksheet": "Sheet1", "x_column": "A", "y_column": "B"}
        result = validate_direct_worksheet_plot_bindings({"layers": [{"index": 0, "plot_details": [plot]}]}, [])
        self.assertEqual("failed", result["status"])
        self.assertTrue(any(item["property"] == "z_column" for item in result["mismatches"]))


class FakeOpenFailureOrigin(FakeBuildOrigin):
    def open(self, path: str, **kwargs: object) -> bool:
        self.calls.append(("open", {"path": path, "kwargs": dict(kwargs)}))
        return False


class AuthorizedSessionTests(unittest.TestCase):
    def test_authorized_session_attaches_and_detaches_without_hidden_api(self) -> None:
        from builders.aa2195.session import origin_session

        op = FakeOrigin()
        with patch("builders.aa2195.session.is_administrator_python", return_value=True):
            with origin_session(op, attach_existing_authorized=True) as evidence:
                self.assertEqual("administrator_attach_existing_authorized", evidence["strategy"])

        self.assertEqual([("attach", None), ("detach", None)], op.calls)

    def test_authorized_session_detaches_when_body_raises(self) -> None:
        from builders.aa2195.session import origin_session

        op = FakeOrigin()
        with patch("builders.aa2195.session.is_administrator_python", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "boom"):
                with origin_session(op, attach_existing_authorized=True):
                    raise RuntimeError("boom")

        self.assertEqual([("attach", None), ("detach", None)], op.calls)

    def test_formal_session_rejects_hidden_by_default(self) -> None:
        from builders.aa2195.session import origin_session

        op = FakeOrigin()
        with patch("builders.aa2195.session.is_administrator_python", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "E121_ATTACH_POLICY_VIOLATION"):
                with origin_session(op, attach_existing_authorized=False):
                    pass

        self.assertEqual([], op.calls)

    def test_diagnostic_hidden_session_requires_explicit_opt_in(self) -> None:
        from builders.aa2195.session import origin_session

        op = FakeOrigin()
        with origin_session(
            op,
            attach_existing_authorized=False,
            require_administrator=False,
            allow_diagnostic_hidden=True,
        ) as evidence:
            self.assertEqual("diagnostic_new_hidden_not_pass_eligible", evidence["strategy"])

        self.assertEqual(
            [("set_show", False), ("new", False), ("exit", None)],
            op.calls,
        )

    def test_authorized_session_rejects_non_admin_before_origin_calls(self) -> None:
        from builders.aa2195.session import origin_session

        op = FakeOrigin()
        with patch("builders.aa2195.session.is_administrator_python", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "E120_ENVIRONMENT_MISMATCH"):
                with origin_session(op, attach_existing_authorized=True):
                    pass

        self.assertEqual([], op.calls)

    def test_build_origin_figure_attaches_for_build_and_reopen(self) -> None:
        from builders import aa2195

        op = FakeBuildOrigin()
        page = FakePage()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {"originpro": op}), patch.dict(
            aa2195.BUILDERS,
            {"fig15": lambda origin, params: {"page_name": "Fig15", "expected_plot_count": 1, "canvas_size": (850, 335)}},
        ), patch.object(aa2195, "find_graph", return_value=page), patch.object(
            aa2195,
            "inspect_page",
            return_value={"plot_count": 1, "layer_count": 1, "layers": []},
        ), patch.object(aa2195, "is_administrator_python", return_value=True), patch.object(
            aa2195, "has_visible_origin_process", return_value=True
        ):
            result = aa2195.build_origin_figure(
                "fig15",
                output_dir=Path(tmp),
                attach_existing_authorized=True,
            )

        names = [name for name, _ in op.calls]
        self.assertEqual(2, names.count("attach"))
        self.assertEqual(2, names.count("detach"))
        self.assertEqual(2, names.count("new"))
        self.assertNotIn("set_show", names)
        self.assertNotIn("exit", names)
        open_calls = [payload for name, payload in op.calls if name == "open"]
        self.assertEqual(1, len(open_calls))
        self.assertEqual(False, open_calls[0]["kwargs"].get("readonly"))
        self.assertEqual(False, open_calls[0]["kwargs"].get("asksave"))
        save_calls = [payload for name, payload in op.calls if name == "save"]
        self.assertEqual(3, len(save_calls))
        self.assertEqual(save_calls[0], save_calls[1])
        self.assertEqual(save_calls[1], save_calls[2])
        self.assertEqual(["win -z0;", "win -z0;"], page.commands)
        editable = result["per_figure"]["fig15"]["editable_open_evidence"]
        self.assertFalse(editable["origin_open_readonly_requested"])
        self.assertTrue(editable["same_path_save_verified_after_reopen"])
        self.assertTrue(editable["writable_after"])
        editable_view = result["per_figure"]["fig15"]["editable_view_evidence"]
        self.assertEqual("applied", editable_view["pre_save"]["status"])
        self.assertEqual("applied", editable_view["post_reopen"]["status"])
        self.assertEqual("administrator_attach_existing_authorized_two_phase", result["session_mode"])
        self.assertEqual(850, page.save_kwargs["width"])
        exports = result["per_figure"]["fig15"]["origin_rendered_exports"]
        self.assertEqual(["pre_save", "post_reopen"], [item["phase"] for item in exports])
        self.assertEqual(
            ["fig15_builder_pre_save.png", "fig15_builder_post_reopen.png"],
            [Path(item["path"]).name for item in exports],
        )

    def test_inspection_reopen_uses_editable_same_path_save(self) -> None:
        from adapters.inspection import adapter

        op = FakeInspectOrigin()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {"originpro": op}):
            opju = Path(tmp) / "candidate.opju"
            opju.write_bytes(b"fake-opju")
            opju.chmod(0o444)
            result = adapter.Adapter().op_project_reopen_clean(
                {"project_path": str(opju)},
                {"workspace": tmp},
            )

        names = [name for name, _ in op.calls]
        self.assertIn("set_show", names)
        self.assertIn("new", names)
        open_calls = [payload for name, payload in op.calls if name == "open"]
        self.assertEqual(1, len(open_calls))
        self.assertEqual(False, open_calls[0]["kwargs"].get("readonly"))
        self.assertEqual(False, open_calls[0]["kwargs"].get("asksave"))
        save_calls = [payload for name, payload in op.calls if name == "save"]
        self.assertEqual([str(opju)], save_calls)
        editable = result["editable_open_evidence"]
        self.assertTrue(editable["readonly_before"])
        self.assertFalse(editable["readonly_after"])
        self.assertTrue(editable["readonly_attribute_cleared"])
        self.assertFalse(editable["origin_open_readonly_requested"])
        self.assertTrue(editable["same_path_save_verified_after_reopen"])

    def test_shared_editable_opju_helper_never_requests_readonly_open(self) -> None:
        from runtime.editable_opju import open_opju_editable

        op = FakeBuildOrigin()
        with tempfile.TemporaryDirectory() as tmp:
            opju = Path(tmp) / "candidate.opju"
            opju.write_bytes(b"fake-opju")
            opju.chmod(0o444)
            evidence = open_opju_editable(op, opju)

        open_calls = [payload for name, payload in op.calls if name == "open"]
        self.assertEqual(1, len(open_calls))
        self.assertEqual(False, open_calls[0]["kwargs"].get("readonly"))
        self.assertEqual(False, open_calls[0]["kwargs"].get("asksave"))
        self.assertTrue(evidence["readonly_attribute_cleared"])
        self.assertFalse(evidence["origin_open_readonly_requested"])
        self.assertTrue(evidence["same_path_save_verified_after_reopen"])

    def test_shared_editable_opju_helper_does_not_mark_failed_open_as_save_verified(self) -> None:
        from runtime.editable_opju import open_opju_editable

        op = FakeOpenFailureOrigin()
        with tempfile.TemporaryDirectory() as tmp:
            opju = Path(tmp) / "candidate.opju"
            opju.write_bytes(b"fake-opju")
            evidence = open_opju_editable(op, opju, raise_on_failure=False)

        names = [name for name, _ in op.calls]
        self.assertEqual(["open"], names)
        self.assertFalse(evidence["origin_open_result"])
        self.assertFalse(evidence["origin_open_readonly_requested"])
        self.assertFalse(evidence["same_path_save_verified_after_reopen"])

    def test_production_code_never_requests_readonly_opju_open(self) -> None:
        root = Path(__file__).resolve().parents[1]
        production_roots = [root / name for name in ("adapters", "builders", "runtime", "scripts")]
        violations: list[str] = []
        for production_root in production_roots:
            for source in production_root.rglob("*.py"):
                tree = ast.parse(source.read_text(encoding="utf-8-sig"), filename=str(source))
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    for keyword in node.keywords:
                        if keyword.arg not in {"readonly", "read_only"}:
                            continue
                        if isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                            violations.append(f"{source.relative_to(root)}:{node.lineno} {keyword.arg}=True")
        self.assertEqual([], violations)

    def test_build_origin_figure_refuses_hidden_formal_route_before_import(self) -> None:
        from builders import aa2195

        result = aa2195.build_origin_figure("fig15", attach_existing_authorized=False)

        self.assertEqual("failed", result["status"])
        self.assertEqual("E121_ATTACH_POLICY_VIOLATION", result["error_code"])
        self.assertFalse(result["opju_generation_allowed"])

    def test_build_origin_figure_refuses_non_admin_before_originpro_import(self) -> None:
        from builders import aa2195

        with patch.object(aa2195, "is_administrator_python", return_value=False):
            result = aa2195.build_origin_figure("fig15")

        self.assertEqual("failed", result["status"])
        self.assertEqual("E120_ENVIRONMENT_MISMATCH", result["error_code"])
        self.assertTrue(result["origin_attach_not_attempted"])

    def test_build_origin_figure_refuses_missing_visible_origin_before_originpro_import(self) -> None:
        from builders import aa2195

        with patch.object(aa2195, "is_administrator_python", return_value=True), patch.object(
            aa2195, "has_visible_origin_process", return_value=False
        ):
            result = aa2195.build_origin_figure("fig15")

        self.assertEqual("failed", result["status"])
        self.assertEqual("E121_ATTACH_POLICY_VIOLATION", result["error_code"])
        self.assertTrue(result["origin_attach_not_attempted"])
        self.assertEqual("administrator_opened_visible_origin", result["required_origin_process"])

    def test_graphobject_only_figure_fails_direct_worksheet_structure_gate(self) -> None:
        from builders import aa2195

        op = FakeBuildOrigin()
        page = FakePage()
        readback = {
            "plot_count": 0,
            "layer_count": 1,
            "layers": [{"graph_object_readback": {"object_count": 24, "status": "ok"}}],
        }
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {"originpro": op}), patch.dict(
            aa2195.BUILDERS,
            {
                "fig16": lambda origin, params: {
                    "page_name": "Fig16",
                    "expected_plot_count": 0,
                    "expected_graphobject_count": 24,
                }
            },
        ), patch.object(aa2195, "find_graph", return_value=page), patch.object(
            aa2195,
            "inspect_page",
            return_value=readback,
        ), patch.object(aa2195, "is_administrator_python", return_value=True), patch.object(
            aa2195, "has_visible_origin_process", return_value=True
        ):
            result = aa2195.build_origin_figure(
                "fig16",
                output_dir=Path(tmp),
                attach_existing_authorized=True,
            )

        figure = result["per_figure"]["fig16"]
        self.assertEqual("structure_readback_failed", figure["status"])
        self.assertEqual("failed", figure["origin_object_readback_validation"]["status"])
        self.assertEqual("failed", figure["origin_object_readback_validation"]["worksheet_binding_validation"]["status"])
        self.assertEqual(24, figure["origin_object_readback_validation"]["actual_graphobject_count"])

    def test_structure_gate_requires_exact_per_layer_plot_counts(self) -> None:
        from builders import aa2195

        op = FakeBuildOrigin()
        page = FakePage()
        readback = {
            "plot_count": 10,
            "layer_count": 2,
            "layers": [
                {"index": 0, "plot_count": 6, "graph_object_readback": {"object_count": 0}},
                {"index": 1, "plot_count": 4, "graph_object_readback": {"object_count": 0}},
            ],
        }
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {"originpro": op}), patch.dict(
            aa2195.BUILDERS,
            {
                "fig15": lambda origin, params: {
                    "page_name": "Fig15",
                    "expected_plot_count": 10,
                    "expected_plot_count_by_layer": {0: 5, 1: 5},
                }
            },
        ), patch.object(aa2195, "find_graph", return_value=page), patch.object(
            aa2195,
            "inspect_page",
            return_value=readback,
        ), patch.object(aa2195, "is_administrator_python", return_value=True), patch.object(
            aa2195, "has_visible_origin_process", return_value=True
        ):
            result = aa2195.build_origin_figure(
                "fig15",
                output_dir=Path(tmp),
                attach_existing_authorized=True,
            )

        figure = result["per_figure"]["fig15"]
        validation = figure["origin_object_readback_validation"]["layer_plot_count_validation"]
        self.assertEqual("structure_readback_failed", figure["status"])
        self.assertEqual("failed", validation["status"])
        self.assertEqual(6, validation["actual"][0])
        self.assertEqual(4, validation["actual"][1])

    def test_graphobject_contract_rejects_extra_fig_prefixed_objects(self) -> None:
        from builders.aa2195.readback import validate_graphobject_contracts

        readback = {
            "layers": [
                {
                    "graph_object_readback": {
                        "object_count": 3,
                        "objects": [
                            {"name": "fig15_label_01", "attach": 2},
                            {"name": "fig15_caption", "attach": 2, "text": "Fig. 15."},
                        ],
                        "enumerated_objects": [
                            {"name": "fig15_label_01"},
                            {"name": "fig15_caption"},
                            {"name": "fig15_stray_duplicate"},
                        ],
                        "missing_names": [],
                    }
                }
            ]
        }
        result = validate_graphobject_contracts(
            readback,
            {
                "fig15_label_01": {"attach": 2},
                "fig15_caption": {"attach": 2, "text_contains": "Fig. 15."},
            },
        )

        self.assertEqual("failed", result["status"])
        self.assertIn("fig15_stray_duplicate", result["unexpected_fig_prefixed_names"])

    def test_graphobject_contract_rejects_duplicate_required_names_without_total_count_gate(self) -> None:
        from builders.aa2195.readback import validate_graphobject_contracts

        readback = {
            "layers": [
                {
                    "graph_object_readback": {
                        "object_count": 4,
                        "objects": [
                            {"name": "fig15_label_01", "attach": 2},
                            {"name": "fig15_caption", "attach": 2, "text": "Fig. 15."},
                        ],
                        "enumerated_objects": [
                            {"name": "fig15_label_01"},
                            {"name": "fig15_label_01"},
                            {"name": "fig15_caption"},
                            {"name": "legend"},
                        ],
                        "missing_names": [],
                    }
                }
            ]
        }
        result = validate_graphobject_contracts(
            readback,
            {
                "fig15_label_01": {"attach": 2},
                "fig15_caption": {"attach": 2, "text_contains": "Fig. 15."},
            },
        )

        self.assertEqual("failed", result["status"])
        self.assertEqual(["fig15_label_01"], result["duplicate_names"])
        self.assertNotIn("legend", result["unexpected_fig_prefixed_names"])

    def test_graphobject_contract_allows_cross_layer_origin_internal_duplicates(self) -> None:
        from builders.aa2195.readback import validate_graphobject_contracts

        readback = {
            "layers": [
                {
                    "graph_object_readback": {
                        "objects": [{"name": "fig15_label_01", "attach": 2}],
                        "enumerated_objects": [
                            {"name": "fig15_label_01"},
                            {"name": "_202"},
                            {"name": "__BCO2"},
                        ],
                        "missing_names": [],
                    }
                },
                {
                    "graph_object_readback": {
                        "objects": [{"name": "fig15_caption", "attach": 2, "text": "Fig. 15."}],
                        "enumerated_objects": [
                            {"name": "fig15_caption"},
                            {"name": "_202"},
                            {"name": "__BCO2"},
                        ],
                        "missing_names": [],
                    }
                },
            ]
        }
        result = validate_graphobject_contracts(
            readback,
            {
                "fig15_label_01": {"attach": 2},
                "fig15_caption": {"attach": 2, "text_contains": "Fig. 15."},
            },
        )

        self.assertEqual("ok", result["status"])
        self.assertEqual([], result["duplicate_names"])


class GeometryContractTests(unittest.TestCase):
    def test_fig12_matrix_rows_match_native_worksheet_log_y_coordinates(self) -> None:
        import numpy as np

        from builders.aa2195.geometry import _fig12_rate_axis

        rates = _fig12_rate_axis("PSC", 75)
        self.assertAlmostEqual(0.01, float(rates[0]))
        self.assertAlmostEqual(10.0, float(rates[-1]))
        self.assertFalse(np.allclose(np.diff(rates), np.diff(rates)[0]))
        self.assertTrue(np.allclose(np.diff(np.log10(rates)), np.diff(np.log10(rates))[0]))

    def test_fig12_source_palette_digitization_builds_editable_three_region_matrix(self) -> None:
        import numpy as np
        from PIL import Image, ImageDraw

        from builders.aa2195.geometry import _fig12_source_matrix

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "fig12.png"
            image = Image.new("RGB", (805, 590), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((98, 53, 210, 269), fill=(252, 191, 110))
            draw.rectangle((211, 53, 265, 269), fill=(177, 223, 137))
            draw.rectangle((266, 53, 321, 269), fill=(198, 223, 236))
            image.save(source)
            matrix = _fig12_source_matrix("PSC", [27.90, 35.55, 41.08, 54.00], source)

        self.assertEqual((75, 95), matrix.shape)
        self.assertTrue(np.isfinite(matrix).all())
        self.assertEqual(3, len(np.unique(matrix)))
        self.assertGreater(float(matrix.max()), 41.08)
        self.assertLess(float(matrix.min()), 35.55)
        self.assertGreater(float(np.median(matrix[:, 0])), 41.08)
        self.assertLess(float(np.median(matrix[:, -1])), 35.55)

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "fig12_y.png"
            image = Image.new("RGB", (805, 590), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((98, 53, 321, 160), fill=(252, 191, 110))
            draw.rectangle((98, 161, 321, 269), fill=(198, 223, 236))
            image.save(source)
            y_matrix = _fig12_source_matrix("PSC", [27.90, 35.55, 41.08, 54.00], source)
        self.assertLess(float(np.median(y_matrix[0, :])), 35.55)
        self.assertGreater(float(np.median(y_matrix[-1, :])), 41.08)

    def test_page_dot_command_converts_inches_using_page_resolution(self) -> None:
        from builders.aa2195.common_origin_utils import page_dot_command

        command = page_dot_command(8.5, 3.35, 600.0, 600.0)
        self.assertIn("page.width=5100", command)
        self.assertIn("page.height=2010", command)

        with self.assertRaisesRegex(ValueError, "E540_PAGE_UNIT_SCALE_MISMATCH"):
            page_dot_command(8.5, 3.35, 0.0, 600.0)

    def test_fit_page_to_window_uses_origin_whole_page_view(self) -> None:
        from builders.aa2195.common_origin_utils import fit_page_to_window

        class FakePage:
            def __init__(self) -> None:
                self.commands: list[str] = []

            def lt_exec(self, command: str) -> None:
                self.commands.append(command)

        page = FakePage()
        evidence = fit_page_to_window(page)

        self.assertEqual(page.commands, ["win -z0;"])
        self.assertEqual(evidence["status"], "applied")
        self.assertEqual(evidence["command"], "win -z0;")

    def test_page_percent_layer_command_uses_official_unit_one(self) -> None:
        from builders.aa2195.common_origin_utils import page_percent_layer_command

        command = page_percent_layer_command((0.0, 0.0, 50.0, 100.0))
        self.assertIn("layer.unit=1", command)
        self.assertIn("layer.width=50", command)

        with self.assertRaisesRegex(ValueError, "E541_LAYER_UNIT_SCALE_MISMATCH"):
            page_percent_layer_command((60.0, 0.0, 50.0, 100.0))

    def test_origin_font_size_preserves_point_units(self) -> None:
        from builders.aa2195.common_origin_utils import origin_font_size

        self.assertAlmostEqual(6.0, origin_font_size(6.0))
        self.assertAlmostEqual(10.0, origin_font_size(10.0))
        self.assertAlmostEqual(18.0, origin_font_size(20.0))

    def test_source_canvas_sizes_are_fixed(self) -> None:
        from builders.aa2195.geometry import FIGURE_CANVAS

        self.assertEqual(
            {
                "fig12": (805, 590),
                "fig15": (850, 335),
                "fig16": (720, 375),
            },
            FIGURE_CANVAS,
        )

    def test_fig12_has_three_calibrated_finite_panels(self) -> None:
        import numpy as np

        from builders.aa2195.geometry import fig12_panels

        panels = fig12_panels()
        self.assertEqual(["PSC", "UC", "TR"], [panel["name"] for panel in panels])
        for panel in panels:
            matrix = panel["matrix"]
            self.assertEqual(4, len(panel["levels"]))
            self.assertTrue(np.isfinite(matrix).all())
            self.assertGreater(matrix.shape[0], 20)
            self.assertGreater(matrix.shape[1], 30)
            self.assertEqual("reconstructed_approximate", panel["provenance"])

    def test_fig15_has_two_panels_and_complete_semantic_inventory(self) -> None:
        from builders.aa2195.geometry import fig15_geometry

        geometry = fig15_geometry()
        self.assertEqual((850, 335), geometry["canvas"])
        self.assertEqual(["PSC", "UC_TR"], [panel["name"] for panel in geometry["panels"]])
        self.assertEqual(5, sum(len(panel["stage_circles"]) for panel in geometry["panels"]))
        self.assertEqual(5, sum(len(panel["header_circles"]) for panel in geometry["panels"]))
        self.assertGreaterEqual(len(geometry["labels"]), 20)
        self.assertIn("Fig. 15.", geometry["caption"])
        texts = [record["text"] for record in geometry["labels"]]
        self.assertIn(r"\g(s)\-(p)", texts)
        self.assertIn(r"\g(e)", texts)
        self.assertFalse(any("sigma" in text or "epsilon" in text for text in texts))
        right_curve = geometry["panels"][1]["curve"]
        self.assertEqual("digitized_source_centerline", right_curve["method"])
        self.assertGreater(right_curve["y"][8] - right_curve["y"][0], 0.45)
        self.assertEqual(42, geometry["labels"][18]["y"])
        self.assertEqual("reconstructed_approximate", geometry["provenance"])

    def test_fig16_has_source_calibrated_object_inventory(self) -> None:
        from builders.aa2195.geometry import fig16_geometry

        geometry = fig16_geometry()
        self.assertEqual((720, 375), geometry["canvas"])
        self.assertEqual(21, len(geometry["bars"]))
        self.assertEqual(3, len(geometry["group_boxes"]))
        self.assertEqual(7, len(geometry["stage_labels"]))
        self.assertEqual({"WH", "DRV", "DRX"}, {item["label"] for item in geometry["legend"]})
        self.assertEqual((601, 0, 639, 10), geometry["legend"][0]["bbox"])
        self.assertEqual("reconstructed_approximate", geometry["provenance"])


class FigureBuilderContractTests(unittest.TestCase):
    def test_formal_builders_construct_hidden_graph_page_then_reveal(self) -> None:
        from builders.aa2195 import fig12_builder, fig15_builder, fig16_builder

        for figure_id, builder in {
            "fig12": fig12_builder,
            "fig15": fig15_builder,
            "fig16": fig16_builder,
        }.items():
            with self.subTest(figure_id=figure_id):
                op = FakeBuilderOrigin()
                result = builder.build(op, {})

                self.assertEqual(True, op.new_graph_calls[0].get("hidden"))
                self.assertEqual([False, True], op.page.show_history)
                self.assertEqual(
                    {
                        "status": "applied",
                        "graph_page_created_hidden": True,
                        "revealed_after_styling": True,
                    },
                    result["construction_visibility"],
                )

    def test_axis_readback_maps_native_y_title_properties_to_contract_keys(self) -> None:
        from builders.aa2195.readback import inspect_axis_state

        class AxisOrigin:
            values = {"yl.rotate": 90, "layer.y.minorTicks": 1}

            def lt_int(self, expression: str) -> int:
                return self.values.get(expression, 1)

        class Activatable:
            def activate(self) -> None:
                return None

        result = inspect_axis_state(AxisOrigin(), Activatable(), Activatable())

        self.assertEqual(90, result["values"]["y_title_rotation"])
        self.assertEqual(1, result["values"]["y.minorTicks"])

    def test_fig12_contour_palette_matches_low_blue_high_orange_colorbar(self) -> None:
        from builders.aa2195.fig12_builder import (
            _apply_contour_line_style,
            _apply_three_region_palette,
        )

        layer = FakeLayer()
        _apply_three_region_palette(layer)
        commands = " ".join(layer.commands)
        self.assertIn("color1=color(198,223,236)", commands)
        self.assertIn("color2=color(177,223,137)", commands)
        self.assertIn("color3=color(252,191,110)", commands)
        self.assertIn("colorBelow=color(198,223,236)", commands)
        self.assertIn("colorAbove=color(252,191,110)", commands)
        self.assertNotIn("lineWidth1=", commands)
        self.assertNotIn("showLines(1)", commands)

        _apply_contour_line_style(layer)
        final_commands = " ".join(layer.commands)
        self.assertIn("lineColor1=color(86,107,68)", final_commands)
        self.assertIn("lineWidth1=0.05", final_commands)
        self.assertIn("showLines(1)", final_commands)
        self.assertNotIn("showLines(3)", final_commands)

    def test_fig15_builder_uses_source_calibrated_two_panel_contract(self) -> None:
        from builders.aa2195 import fig15_builder

        op = FakeBuilderOrigin()
        result = fig15_builder.build(op, {})

        self.assertEqual((850, 335), result["canvas_size"])
        self.assertEqual("worksheet_backed_source_calibrated_two_layer", result["route"])
        self.assertEqual(2, len(op.page.layers))
        self.assertEqual(10, result["expected_plot_count"])
        self.assertEqual({0: 5, 1: 5}, result["expected_plot_count_by_layer"])
        self.assertEqual(
            [
                "Fig15_PSC_source_calibrated_paths",
                "Fig15_UC_TR_source_calibrated_paths",
            ],
            result["required_worksheet_books"],
        )
        self.assertEqual(2, len(result["worksheet_binding_inventory"]))
        self.assertTrue(
            all(
                record["association_mode"] == "direct_worksheet_plot_binding"
                for record in result["worksheet_binding_inventory"]
            )
        )
        self.assertGreaterEqual(len(result["label_inventory"]), 20)
        self.assertEqual("reconstructed_approximate", result["reproduction_mode"])
        self.assertEqual(0, result["unexpected_legend_expected"])
        self.assertEqual("worksheet_arrowhead_paths", result["axis_route"])
        self.assertEqual(2, len(result["axis_contract"]))
        self.assertEqual(2, result["required_graphobject_contracts"]["fig15_caption"]["attach"])
        self.assertEqual(len(result["required_graphobject_contracts"]), result["expected_graphobject_count"])
        self.assertTrue(any("page.width=5100" in command and "page.height=2010" in command for command in op.page.commands))
        self.assertTrue(any("page.speedMode=0" in command for command in op.page.commands))
        self.assertTrue(all(any("layer.unit=1" in command for command in layer.commands) for layer in op.page.layers))
        self.assertTrue(all(any("layer.speedMode=0" in command for command in layer.commands) for layer in op.page.layers))
        self.assertTrue(all(any("layer.x.showAxes=0" in command for command in layer.commands) for layer in op.page.layers))
        self.assertTrue(all(any("layer.x.showLabels=0" in command for command in layer.commands) for layer in op.page.layers))
        self.assertTrue(all(any("layer.x.ticks=0" in command for command in layer.commands) for layer in op.page.layers))
        self.assertTrue(all(any("layer.x.arrow.show=0" in command for command in layer.commands) for layer in op.page.layers))
        self.assertTrue(all(0.0 <= layer.properties["left"] <= 100.0 for layer in op.page.layers))
        self.assertTrue(all(0.0 < layer.properties["width"] <= 100.0 for layer in op.page.layers))
        self.assertTrue(all(5.0 <= label.properties["fsize"] <= 18.0 for layer in op.page.layers for label in layer.labels))
        self.assertTrue(all(label.properties["attach"] == 2 for layer in op.page.layers for label in layer.labels))
        self.assertTrue(any(getattr(label, "name", "") == "fig15_caption" for label in op.page.layers[0].labels))
        self.assertEqual(9.0, result["text_calibration"]["caption_font_size"])

    def test_fig15_builder_applies_candidate_text_calibration(self) -> None:
        from builders.aa2195 import fig15_builder

        op = FakeBuilderOrigin()
        result = fig15_builder.build(
            op,
            {
                "text_role_scales": {"panel": 1.25, "description": 1.2},
                "caption_font_size": 11.0,
                "caption_text": r"\b(Fig. 15.) Flow stress curve diagram",
            },
        )

        inventory = {record["name"]: record for record in result["label_inventory"]}
        self.assertAlmostEqual(13.75, inventory["fig15_label_01"]["effective_font_size"])
        self.assertAlmostEqual(9.6, inventory["fig15_label_20"]["effective_font_size"])
        self.assertAlmostEqual(11.0, inventory["fig15_caption"]["effective_font_size"])
        self.assertEqual(r"\b(Fig. 15.) Flow stress curve diagram", inventory["fig15_caption"]["text"])
        self.assertEqual(11.0, result["text_calibration"]["caption_font_size"])

    def test_fig12_builder_uses_calibrated_matrices_and_layout(self) -> None:
        import numpy as np

        from builders.aa2195 import fig12_builder

        op = FakeBuilderOrigin()
        result = fig12_builder.build(op, {})

        self.assertEqual((805, 590), result["canvas_size"])
        self.assertEqual("worksheet_xyz_source_calibrated_three_panel_contour", result["route"])
        self.assertEqual(4, len(op.page.layers))
        self.assertEqual(3, result["expected_plot_count"])
        self.assertEqual({0: 1, 1: 1, 2: 1, 3: 0}, result["expected_plot_count_by_layer"])
        self.assertEqual(
            ["Fig12_PSC_worksheet_data", "Fig12_UC_worksheet_data", "Fig12_TR_worksheet_data"],
            result["required_worksheet_books"],
        )
        self.assertEqual(3, len(result["worksheet_binding_inventory"]))
        self.assertEqual(3, len(op.books))
        self.assertTrue(all(book.book_type == "w" for book in op.books))
        self.assertTrue(all(len(book.sheet.columns) == 3 for book in op.books))
        self.assertTrue(all(book.sheet.axes == ("XYZ", 0, 2, False) for book in op.books))
        self.assertTrue(all(record["association_mode"] == "direct_worksheet_xyz_plot_binding" for record in result["worksheet_binding_inventory"]))
        self.assertTrue(all(record["plot_type_code"] == 243 for record in result["direct_worksheet_plot_contracts"]))
        self.assertEqual(3, len(result["panel_inventory"]))
        self.assertEqual(3, len(result["colorbar_inventory"]))
        self.assertEqual((12.2, 9.0, 27.8, 36.5), result["panel_inventory"][0]["layout_percent"])
        self.assertEqual((60.7, 9.0, 27.8, 36.5), result["panel_inventory"][1]["layout_percent"])
        self.assertEqual((333.0, 82.0, 367.0, 188.0), result["colorbar_inventory"][0]["bbox"])
        self.assertEqual((720.0, 82.0, 754.0, 188.0), result["colorbar_inventory"][1]["bbox"])
        self.assertEqual(
            {0: {"dx": 0.0, "dy": 0.0}, 1: {"dx": 0.0, "dy": 0.0}, 2: {"dx": 0.0, "dy": 0.0}},
            result["fig12_colorbar_offsets"],
        )
        self.assertEqual(
            {0: {"dx": 0.0, "dy": 0.0}, 1: {"dx": 0.0, "dy": 0.0}, 2: {"dx": 0.0, "dy": 0.0}},
            result["fig12_panel_layout_offsets"],
        )
        self.assertEqual({0: -1.5, 1: 0.0, 2: 0.0}, result["fig12_matrix_biases"])
        self.assertEqual({0: 1.0, 1: 1.0, 2: 1.0}, result["fig12_matrix_contrasts"])
        self.assertEqual(0.5, result["fig12_matrix_resolution_scale"])
        self.assertEqual(4968, result["declared_direct_plot_worksheet_rows"])
        self.assertEqual(5000, result["max_direct_plot_worksheet_rows"])
        self.assertTrue(result["fig12_levels_reapplied_after_palette"])
        self.assertEqual(
            {"panel": 2.6, "contour": 2.6, "mechanism": 2.4},
            result["fig12_origin_label_size_scales"],
        )
        self.assertTrue(result["fig12_contour_line_style_reapplied_after_levels"])
        self.assertEqual([86, 107, 68], result["fig12_contour_line_color"])
        self.assertEqual(0.05, result["fig12_contour_line_width"])
        self.assertEqual(26.0, result["fig12_axis_tick_fsize"])
        self.assertEqual({"x": 28.0, "y": 23.0}, result["fig12_axis_title_fsize"])
        self.assertEqual("Temperature/\u2103", result["fig12_axis_title_text"]["x"])
        self.assertEqual(
            "Strain rate/s\\+(-1)",
            result["fig12_axis_title_text"]["y_origin_rich_text"],
        )
        self.assertEqual(
            "Strain rate/s\u207b\u00b9",
            result["fig12_axis_title_text"]["y_rendered_semantics"],
        )
        self.assertEqual(
            {
                "panel": 10.0,
                "contour": 8.4,
                "mechanism": 11.2,
                "colorbar_title": 10.0,
                "colorbar_tick": 8.0,
            },
            result["fig12_label_sizes"],
        )
        self.assertTrue(all(len(panel["levels"]) == 4 for panel in result["panel_inventory"]))
        self.assertGreaterEqual(len(result["label_inventory"]), 20)
        self.assertGreater(result["expected_graphobject_count"], len(result["label_inventory"]))
        self.assertIn("fig12_cb_a_b1", result["required_graphobject_contracts"])
        self.assertIn("fig12_cb_c_k4", result["required_graphobject_contracts"])
        self.assertEqual(3, len(result["axis_contract"]))
        self.assertTrue(all(item["y.type"] == 2 for item in result["axis_contract"]))
        self.assertTrue(
            all(record["name"].startswith("fig12_label_") for record in result["label_inventory"])
        )
        self.assertEqual("reconstructed_approximate", result["reproduction_mode"])
        self.assertTrue(any("page.width=4830" in command and "page.height=3540" in command for command in op.page.commands))
        self.assertTrue(all(any("layer.unit=1" in command for command in layer.commands) for layer in op.page.layers))
        self.assertTrue(any("page.speedMode=0" in command for command in op.page.commands))
        self.assertTrue(all(any("layer.speedMode=0" in command for command in layer.commands) for layer in op.page.layers))
        self.assertTrue(any("speedmode index:=page sm:=off" in command for command in op.page.commands))
        self.assertTrue(all(any("speedmode index:=layer sm:=off" in command for command in layer.commands) for layer in op.page.layers))
        self.assertTrue(all(any("layer.speed.matrix=0" in command for command in layer.commands) for layer in op.page.layers))
        self.assertTrue(
            all(
                any("yl.rotate=90" in command for command in layer.commands)
                for layer in op.page.layers[:3]
            )
        )
        self.assertTrue(all(item["y_title_rotation"] == 90 for item in result["axis_contract"]))

    def test_fig12_builder_applies_explicit_colorbar_offset_without_changing_default(self) -> None:
        from builders.aa2195 import fig12_builder

        op = FakeBuilderOrigin()
        result = fig12_builder.build(
            op,
            {
                "fig12_colorbar_offsets": {
                    "PSC": {"dx": 4.0, "dy": 0.0},
                    "ignored": {"dx": 99.0, "dy": 99.0},
                }
            },
        )

        self.assertEqual({"dx": 4.0, "dy": 0.0}, result["fig12_colorbar_offsets"][0])
        self.assertEqual((337.0, 82.0, 371.0, 188.0), result["colorbar_inventory"][0]["bbox"])
        self.assertEqual((720.0, 82.0, 754.0, 188.0), result["colorbar_inventory"][1]["bbox"])
        self.assertEqual((520.0, 358.0, 554.0, 470.0), result["colorbar_inventory"][2]["bbox"])

    def test_fig12_builder_applies_explicit_panel_layout_offset_without_changing_default(self) -> None:
        from builders.aa2195 import fig12_builder

        op = FakeBuilderOrigin()
        result = fig12_builder.build(
            op,
            {
                "fig12_panel_layout_offsets": {
                    "PSC": {"dx": 0.0, "dy": -4.0},
                    "TR": {"dx": 1.5, "dy": -2.0},
                    "ignored": {"dx": 99.0, "dy": 99.0},
                }
            },
        )

        self.assertEqual({"dx": 0.0, "dy": -4.0}, result["fig12_panel_layout_offsets"][0])
        self.assertEqual({"dx": 0.0, "dy": 0.0}, result["fig12_panel_layout_offsets"][1])
        self.assertEqual({"dx": 1.5, "dy": -2.0}, result["fig12_panel_layout_offsets"][2])
        self.assertEqual((12.2, 5.0, 27.8, 36.5), result["panel_inventory"][0]["layout_percent"])
        self.assertEqual((60.7, 9.0, 27.8, 36.5), result["panel_inventory"][1]["layout_percent"])
        self.assertEqual((36.9, 52.5, 27.8, 37.5), result["panel_inventory"][2]["layout_percent"])

    def test_fig12_builder_can_keep_source_crop_while_using_analytic_matrix_mode(self) -> None:
        from PIL import Image

        from builders.aa2195 import fig12_builder

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "fig12.png"
            Image.new("RGB", (805, 590), (252, 191, 110)).save(source)

            default_result = fig12_builder.build(FakeBuilderOrigin(), {"source_crop": str(source)})
            analytic_result = fig12_builder.build(
                FakeBuilderOrigin(),
                {
                    "source_crop": str(source),
                    "fig12_matrix_mode": "analytic_fallback",
                },
            )

        self.assertEqual("source_palette_digitized", default_result["fig12_matrix_mode"])
        self.assertTrue(
            all(panel["matrix_source"] == "source_palette_digitized" for panel in default_result["panel_inventory"])
        )
        self.assertEqual("analytic_fallback", analytic_result["fig12_matrix_mode"])
        self.assertTrue(
            all(panel["matrix_source"] == "analytic_fallback" for panel in analytic_result["panel_inventory"])
        )
        self.assertTrue(
            all(panel["matrix_mode"] == "analytic_fallback" for panel in analytic_result["panel_inventory"])
        )

    def test_fig12_builder_applies_bounded_matrix_resolution_scale(self) -> None:
        from builders.aa2195 import fig12_builder

        op = FakeBuilderOrigin()
        result = fig12_builder.build(op, {"fig12_matrix_resolution_scale": 0.35})

        self.assertEqual(0.35, result["fig12_matrix_resolution_scale"])
        self.assertTrue(
            all(panel["matrix_shape"] == [25, 32] for panel in result["panel_inventory"])
        )
        self.assertTrue(
            all(panel["matrix_resolution_scale"] == 0.35 for panel in result["panel_inventory"])
        )

    def test_fig12_builder_caps_output_grid_below_global_five_thousand_rows(self) -> None:
        from builders.aa2195 import fig12_builder

        op = FakeBuilderOrigin()
        result = fig12_builder.build(op, {"fig12_matrix_resolution_scale": 8.0})

        self.assertEqual(0.5, result["fig12_matrix_resolution_scale"])
        self.assertTrue(
            all(panel["matrix_shape"] == [36, 46] for panel in result["panel_inventory"])
        )
        self.assertEqual(4968, result["declared_direct_plot_worksheet_rows"])

    def test_fig12_source_regions_are_smoothed_into_a_continuous_contour_field(self) -> None:
        import numpy as np

        from builders.aa2195.geometry import _smooth_categorical_region_values

        classes = np.zeros((9, 15), dtype=int)
        classes[:, 5:10] = 1
        classes[:, 10:] = 2
        region_values = np.asarray([50.0, 40.0, 30.0])

        smoothed = _smooth_categorical_region_values(
            classes,
            region_values,
            sigma=1.25,
        )

        self.assertEqual(classes.shape, smoothed.shape)
        self.assertGreater(len(np.unique(np.round(smoothed, 4))), 3)
        self.assertGreater(smoothed[4, 4], smoothed[4, 5])
        self.assertGreater(smoothed[4, 9], smoothed[4, 10])
        self.assertAlmostEqual(50.0, smoothed[4, 0], delta=0.2)
        self.assertAlmostEqual(30.0, smoothed[4, -1], delta=0.2)

    def test_fig12_source_regions_accept_stronger_smoothing_for_contour_softening(self) -> None:
        import numpy as np

        from builders.aa2195.geometry import _smooth_categorical_region_values

        classes = np.zeros((9, 15), dtype=int)
        classes[:, 5:10] = 1
        classes[:, 10:] = 2
        region_values = np.asarray([50.0, 40.0, 30.0])

        smoothed = _smooth_categorical_region_values(
            classes,
            region_values,
            sigma=5.0,
        )

        self.assertEqual(classes.shape, smoothed.shape)
        self.assertLess(abs(float(smoothed[4, 5]) - float(smoothed[4, 4])), abs(40.0 - 50.0))
        self.assertLess(abs(float(smoothed[4, 10]) - float(smoothed[4, 9])), abs(30.0 - 40.0))

    def test_fig12_invalid_label_pixels_are_filled_from_nearest_valid_region(self) -> None:
        import numpy as np

        from builders.aa2195.geometry import _fill_invalid_class_regions

        classes = np.zeros((11, 21), dtype=int)
        classes[:, 14:] = 1
        valid = np.ones_like(classes, dtype=bool)
        valid[3:8, 4:10] = False
        classes[~valid] = 2

        filled = _fill_invalid_class_regions(classes, valid)

        self.assertTrue(np.all(filled[3:8, 4:10] == 0))
        self.assertTrue(np.all(filled[:, 14:] == 1))
        self.assertFalse(np.any(filled == 2))

    def test_fig12_palette_classifier_rejects_white_label_background(self) -> None:
        import numpy as np

        from builders.aa2195.geometry import (
            FIG12_SOURCE_PALETTE,
            _classify_fig12_palette_pixels,
        )

        pixels = np.concatenate(
            [
                FIG12_SOURCE_PALETTE.astype(float),
                np.asarray([[255.0, 255.0, 255.0], [219.0, 219.0, 219.0]]),
            ],
            axis=0,
        ).reshape(1, 5, 3)
        classes, valid = _classify_fig12_palette_pixels(pixels)

        self.assertEqual(classes[0, :3].tolist(), [0, 1, 2])
        self.assertTrue(np.all(valid[0, :3]))
        self.assertFalse(bool(valid[0, 3]))
        self.assertFalse(bool(valid[0, 4]))

    def test_fig12_builder_defaults_to_sparse_log_y_minor_ticks_and_records_smoothing(self) -> None:
        from builders.aa2195 import fig12_builder

        op = FakeBuilderOrigin()
        result = fig12_builder.build(
            op,
            {"fig12_matrix_smoothing_sigma": 1.25},
        )

        self.assertEqual(1.25, result["fig12_matrix_smoothing_sigma"])
        self.assertEqual(0, result["fig12_y_minor_ticks"])
        self.assertTrue(all(item["y.minorTicks"] == 0 for item in result["axis_contract"]))
        self.assertTrue(
            all(
                any("layer.y.minorTicks=0" in command for command in layer.commands)
                for layer in op.page.layers[:3]
            )
        )

    def test_fig12_builder_applies_explicit_label_size_candidate_without_changing_default(self) -> None:
        from builders.aa2195 import fig12_builder

        op = FakeBuilderOrigin()
        result = fig12_builder.build(
            op,
            {
                "fig12_label_size_offsets": {
                    "contour": 1.2,
                    "mechanism": 1.8,
                    "colorbar_tick": 1.0,
                    "ignored": 5.0,
                }
            },
        )

        self.assertEqual(10.0, result["fig12_label_sizes"]["panel"])
        self.assertAlmostEqual(9.6, result["fig12_label_sizes"]["contour"])
        self.assertAlmostEqual(13.0, result["fig12_label_sizes"]["mechanism"])
        self.assertAlmostEqual(9.0, result["fig12_label_sizes"]["colorbar_tick"])
        mechanism_labels = [record for record in result["label_inventory"] if record["role"] == "mechanism"]
        contour_labels = [record for record in result["label_inventory"] if record["role"] == "contour"]
        self.assertTrue(mechanism_labels)
        self.assertTrue(contour_labels)
        self.assertTrue(all(record["size"] == 13.0 for record in mechanism_labels))
        self.assertTrue(all(record["size"] == 9.6 for record in contour_labels))

    def test_fig12_builder_applies_explicit_matrix_bias_override_without_changing_other_defaults(self) -> None:
        from builders.aa2195 import fig12_builder

        op = FakeBuilderOrigin()
        result = fig12_builder.build(op, {"fig12_matrix_biases": {"PSC": 2.0, "ignored": 9.0}})

        self.assertEqual({0: 2.0, 1: 0.0, 2: 0.0}, result["fig12_matrix_biases"])
        self.assertEqual(2.0, result["panel_inventory"][0]["matrix_bias"])
        self.assertEqual(0.0, result["panel_inventory"][1]["matrix_bias"])
        self.assertEqual(3, len(op.books[0].sheet.columns))

    def test_fig16_builder_uses_verified_gid399_stackcolumn_and_paths(self) -> None:
        from builders.aa2195 import fig16_builder

        op = FakeBuilderOrigin()
        result = fig16_builder.build(op, {})

        self.assertEqual((720, 375), result["canvas_size"])
        self.assertEqual("gid399_stackcolumn_213_with_gid1652_layout", result["route"])
        self.assertEqual(11, result["expected_plot_count"])
        self.assertEqual({0: 3, 1: 2, 2: 2, 3: 2, 4: 2}, result["expected_plot_count_by_layer"])
        self.assertEqual(
            ["Fig16_gid399_stack_data"],
            result["required_worksheet_books"],
        )
        self.assertEqual("direct_worksheet_plot_binding", result["worksheet_binding_inventory"][0]["association_mode"])
        self.assertEqual(1, len(op.books))
        self.assertEqual("w", op.books[0].book_type)
        self.assertEqual("H_S_slot_x", op.books[0].sheet.columns[0][2])
        self.assertEqual(20, len(op.books[0].sheet.columns))
        self.assertEqual(11, len(result["direct_worksheet_plot_contracts"]))
        self.assertEqual(
            [213, 213, 213, 200, 200, 203, 200, 203, 200, 203, 200],
            [item["plot_type_code"] for item in result["direct_worksheet_plot_contracts"]],
        )
        self.assertFalse(any(column[2].startswith("baselines_") for column in op.books[0].sheet.columns))
        self.assertTrue(all(
            item["baseline_route"] == "native_column_bottom_edges_no_extra_baseline"
            for item in result["group_inventory"]
        ))
        self.assertTrue(all(
            item["swatch_route"] == "isolated_native_column_fill_with_closed_xy_border"
            for item in result["legend_inventory"]
        ))
        self.assertFalse(any("scanline" in item["swatch_route"] for item in result["legend_inventory"]))
        self.assertEqual(5, len(op.page.layers))
        fill_plots = [op.page.layers[index].plots[0] for index in range(2, 5)]
        for plot in fill_plots:
            commands = " ".join(plot.properties["commands"])
            self.assertIn("-pfb color(", commands)
            self.assertIn("-pbc color(0,0,0)", commands)
            self.assertIn("-vg 0", commands)
            self.assertNotIn("-pfv 9", commands)
        self.assertEqual("GID399", result["official_template_selection"]["selected_primary"])
        self.assertEqual(213, result["official_template_selection"]["selected_primary_plot_type"])
        self.assertEqual("GID1652", result["official_template_selection"]["layout_reference"])
        self.assertEqual(21, len(result["bar_inventory"]))
        self.assertEqual(3, len(result["group_inventory"]))
        self.assertEqual(7, len(result["stage_inventory"]))
        self.assertEqual(result["expected_graphobject_count"], len(result["required_graphobject_contracts"]))
        self.assertEqual(result["expected_graphobject_count"], len(result["required_graphobject_names_by_layer"][1]))
        self.assertNotIn("fig16_bar_wh_01", result["required_graphobject_contracts"])
        self.assertIn("fig16_header_h", result["required_graphobject_contracts"])
        self.assertIn("fig16_legend_text_01", result["required_graphobject_contracts"])
        self.assertIn("fig16_relation_text_07", result["required_graphobject_contracts"])
        self.assertEqual(-1.0, result["fig16_tuning"]["bar_top_dy"])
        self.assertEqual(1.0, result["fig16_tuning"]["bar_bottom_dy"])
        self.assertEqual({"WH": "#ff9830", "DRV": "#00ff98", "DRX": "#d098ff"}, result["fig16_colors"])
        self.assertEqual(
            {"header": 10.0, "legend": 9.5, "group_label": 12.0, "stage": 9.0, "relation": 10.0},
            result["fig16_text_sizes"],
        )
        self.assertEqual("#ff9830", result["bar_inventory"][0]["color"])
        self.assertEqual((24, 147, 63, 335), result["bar_inventory"][0]["bbox"])
        self.assertEqual("H: Hardening level", result["required_graphobject_contracts"]["fig16_header_h"]["text_contains"])
        relation_labels = [
            label
            for label in op.page.layers[1].labels
            if getattr(label, "name", "") == "fig16_relation_text_07"
        ]
        self.assertEqual(1, len(relation_labels))
        self.assertIn(
            result["required_graphobject_contracts"]["fig16_relation_text_07"]["text_contains"],
            relation_labels[0].text,
        )
        self.assertEqual(
            "origin_rich_text_times_new_roman_parenthesized",
            result["fig16_text_font_route"],
        )
        self.assertTrue(
            all(label.text.startswith("\\f:Times New Roman(") for label in op.page.layers[1].labels)
        )
        self.assertEqual(2, relation_labels[0].properties["attach"])
        self.assertFalse(any("label -n" in label.text.lower() for label in op.page.layers[1].labels))
        stage_labels = {
            getattr(label, "name", ""): label
            for label in op.page.layers[1].labels
            if getattr(label, "name", "").startswith("fig16_stage_text_")
        }
        self.assertEqual(7, len(stage_labels))
        self.assertAlmostEqual(-8.5, stage_labels["fig16_stage_text_01"].properties["y1"])
        self.assertAlmostEqual(61.0, stage_labels["fig16_stage_text_01"].properties["x1"])
        self.assertAlmostEqual(246.5, stage_labels["fig16_stage_text_03"].properties["x1"])
        self.assertEqual(
            "post_reopen_exported_glyph_bbox_to_circle_outline_center",
            result["fig16_stage_glyph_centering"]["calibration_basis"],
        )
        self.assertEqual("reconstructed_approximate", result["reproduction_mode"])
        self.assertTrue(any("page.width=4320" in command and "page.height=2250" in command for command in op.page.commands))
        self.assertTrue(any("page.speedMode=0" in command for command in op.page.commands))
        self.assertTrue(any("layer.unit=1" in command for command in op.page.layers[0].commands))
        self.assertTrue(any("layer.speedMode=0" in command for command in op.page.layers[0].commands))

    def test_fig16_builder_applies_explicit_color_candidate_without_changing_default(self) -> None:
        from builders.aa2195 import fig16_builder

        op = FakeBuilderOrigin()
        result = fig16_builder.build(
            op,
            {
                "fig16_colors": {
                    "WH": "#ff9828",
                    "DRV": "#00ef9b",
                    "DRX": "#bf85e8",
                    "ignored": "#000000",
                    "bad": "not-a-color",
                }
            },
        )

        self.assertEqual({"WH": "#ff9828", "DRV": "#00ef9b", "DRX": "#bf85e8"}, result["fig16_colors"])
        self.assertEqual("#ff9828", result["bar_inventory"][0]["color"])
        self.assertEqual("#00ef9b", result["bar_inventory"][7]["color"])
        self.assertEqual("#bf85e8", result["bar_inventory"][14]["color"])
        self.assertEqual("#ff9828", result["legend_inventory"][0]["color"])
        self.assertEqual("#00ef9b", result["legend_inventory"][1]["color"])
        self.assertEqual("#bf85e8", result["legend_inventory"][2]["color"])
        stack_plots = op.page.layers[0].plots[:3]
        self.assertEqual((True, 0, 2), op.page.layers[0].properties["plot_group"])
        self.assertIn("color(255,152,40)", " ".join(stack_plots[0].properties["commands"]))
        self.assertIn("color(0,239,155)", " ".join(stack_plots[1].properties["commands"]))
        self.assertIn("color(191,133,232)", " ".join(stack_plots[2].properties["commands"]))

    def test_fig16_builder_applies_documented_column_gap_candidate_only(self) -> None:
        from builders.aa2195 import fig16_builder

        default_op = FakeBuilderOrigin()
        default_result = fig16_builder.build(default_op, {})
        self.assertIsNone(default_result["fig16_column_gap_percent"])

        candidate_op = FakeBuilderOrigin()
        candidate_result = fig16_builder.build(candidate_op, {"fig16_column_gap_percent": 10})
        self.assertEqual(10.0, candidate_result["fig16_column_gap_percent"])
        for plot in candidate_op.page.layers[0].plots[:3]:
            commands = plot.properties["commands"]
            self.assertTrue(commands[0].startswith("-pfb color("))
            self.assertEqual("-pbc color(0,0,0)", commands[1])
            self.assertEqual(("-vg 10", "-vw 1"), commands[-2:])

    def test_fig16_builder_applies_bounded_group_frame_width_candidate_only(self) -> None:
        from builders.aa2195 import fig16_builder

        default_op = FakeBuilderOrigin()
        default_result = fig16_builder.build(default_op, {})
        thin_op = FakeBuilderOrigin()
        thin_result = fig16_builder.build(
            thin_op, {"fig16_group_frame_width": 0.5}
        )
        clamped_result = fig16_builder.build(
            FakeBuilderOrigin(), {"fig16_group_frame_width": 0.01}
        )

        self.assertEqual(0.5, default_result["fig16_group_frame_width"])
        self.assertEqual(0.5, thin_result["fig16_group_frame_width"])
        self.assertEqual(0.25, clamped_result["fig16_group_frame_width"])
        self.assertEqual(0.5, thin_op.page.layers[1].plots[0].properties["line.width"])

    def test_fig16_builder_applies_explicit_text_size_candidate_without_changing_default(self) -> None:
        from builders.aa2195 import fig16_builder

        op = FakeBuilderOrigin()
        result = fig16_builder.build(
            op,
            {
                "fig16_text_size_offsets": {
                    "header": -0.5,
                    "legend": -0.25,
                    "group_label": 0.5,
                    "stage": -0.5,
                    "relation": -0.75,
                    "ignored": 5.0,
                }
            },
        )

        self.assertEqual(
            {"header": 9.5, "legend": 9.25, "group_label": 12.5, "stage": 8.5, "relation": 9.25},
            result["fig16_text_sizes"],
        )
        labels = {getattr(label, "name", ""): label for label in op.page.layers[1].labels}
        self.assertAlmostEqual(9.5, labels["fig16_header_h"].properties["fsize"])
        self.assertAlmostEqual(9.25, labels["fig16_legend_text_01"].properties["fsize"])
        self.assertAlmostEqual(12.5, labels["fig16_group_label_psc"].properties["fsize"])
        self.assertAlmostEqual(8.5, labels["fig16_stage_text_01"].properties["fsize"])
        self.assertAlmostEqual(9.25, labels["fig16_relation_text_01"].properties["fsize"])

    def test_fig16_builder_applies_bounded_tuning_parameters(self) -> None:
        from builders.aa2195 import fig16_builder

        op = FakeBuilderOrigin()
        result = fig16_builder.build(
            op,
            {
                "fig16_tuning": {
                    "bar_top_dy": -1.0,
                    "bar_bottom_dy": 1.0,
                    "header_dy": -2.0,
                    "legend_dx": 1.0,
                    "legend_dy": -2.0,
                    "relation_text_dy": -3.0,
                }
            },
        )

        self.assertEqual(-2.0, result["fig16_tuning"]["header_dy"])
        self.assertEqual((24, 147, 63, 335), result["bar_inventory"][0]["bbox"])
        wh_x = op.books[0].sheet.columns[0][1]
        wh_values = op.books[0].sheet.columns[1][1]
        drv_values = op.books[0].sheet.columns[2][1]
        drx_values = op.books[0].sheet.columns[3][1]
        self.assertAlmostEqual(43.5, wh_x[0])
        self.assertAlmostEqual(85.0, wh_x[1])
        self.assertAlmostEqual(188.0, wh_values[0])
        self.assertAlmostEqual(0.0, drv_values[0])
        self.assertAlmostEqual(0.0, drx_values[0])
        self.assertAlmostEqual(0.0, wh_values[1])
        self.assertAlmostEqual(134.0, drv_values[1])
        self.assertAlmostEqual(14.0, drx_values[1])
        self.assertEqual((602, -2, 640, 8), result["legend_inventory"][0]["bbox"])
        header_labels = [
            label
            for label in op.page.layers[1].labels
            if getattr(label, "name", "") == "fig16_header_h"
        ]
        relation_labels = [
            label
            for label in op.page.layers[1].labels
            if getattr(label, "name", "") == "fig16_relation_text_01"
        ]
        self.assertEqual(1, len(header_labels))
        self.assertEqual(1, len(relation_labels))
        self.assertAlmostEqual(328.0, header_labels[0].properties["y1"])
        self.assertAlmostEqual(222.0, relation_labels[0].properties["y1"])


class VisualQaTests(unittest.TestCase):
    def test_identical_images_have_complete_nonblocking_metrics(self) -> None:
        from PIL import Image

        from scripts.visual_qa import score_visual

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            render = root / "render.png"
            image = Image.new("RGB", (120, 80), "white")
            for x in range(20, 100):
                for y in range(15, 65):
                    image.putpixel((x, y), (30, 80, 180))
            image.save(source)
            image.save(render)
            result = score_visual(source, render, comparison_dir=root / "qa")

        required = {
            "canvas_size_match", "mae_0_1", "rmse_0_1", "ssim_score", "layout_score",
            "edge_score", "color_score", "source_content_bbox", "actual_content_bbox",
            "registration_shift", "nonwhite_delta", "demo_cyan_ratio", "blocking_reasons",
        }
        self.assertTrue(required.issubset(result))
        self.assertEqual(0.0, result["mae_0_1"])
        self.assertEqual(1.0, result["ssim_score"])
        self.assertEqual([], result["blocking_reasons"])

    def test_canvas_mismatch_and_demo_cyan_are_blocking(self) -> None:
        from PIL import Image, ImageDraw

        from scripts.visual_qa import score_visual

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            render = root / "render.png"
            Image.new("RGB", (100, 60), "white").save(source)
            actual = Image.new("RGB", (140, 90), "white")
            draw = ImageDraw.Draw(actual)
            draw.text((10, 10), "demo demo demo", fill=(0, 240, 240))
            actual.save(render)
            result = score_visual(source, render, comparison_dir=root / "qa")

        self.assertFalse(result["canvas_size_match"])
        self.assertGreater(result["demo_cyan_ratio"], 0.0)
        self.assertIn("canvas_size_mismatch", result["blocking_reasons"])
        self.assertIn("demo_cyan_markings", result["blocking_reasons"])
        self.assertTrue(result["environment_blocked"])
        self.assertIn("E122_ORIGIN_DEMO_EXPORT_BLOCKED", result["error_codes"])

    def test_green_drv_fill_is_not_demo_cyan(self) -> None:
        from PIL import Image, ImageDraw

        from scripts.visual_qa import score_visual

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            render = root / "render.png"
            Image.new("RGB", (120, 80), "white").save(source)
            actual = Image.new("RGB", (120, 80), "white")
            draw = ImageDraw.Draw(actual)
            draw.rectangle((20, 15, 100, 65), fill=(0, 239, 155))
            actual.save(render)
            result = score_visual(source, render, comparison_dir=root / "qa")

        self.assertEqual(0.0, result["demo_cyan_ratio"])
        self.assertNotIn("demo_cyan_markings", result["blocking_reasons"])
        self.assertFalse(result["environment_blocked"])

    def test_candidate_worker_merges_real_visual_metrics(self) -> None:
        from PIL import Image

        from scripts import origin_candidate_worker

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            render = root / "candidate.png"
            opju = root / "candidate.opju"
            image = Image.new("RGB", (850, 335), "white")
            image.save(source)
            image.save(render)
            opju.write_bytes(b"opju")
            result = origin_candidate_worker.evaluate_visual_metrics(
                figure="fig15",
                candidate={"source_crop": str(source)},
                png=render,
                opju=opju,
                output_dir=root,
                hard_gate_status={"status": "pass"},
                origin_export_qa=[],
            )

        self.assertTrue(result["canvas_size_match"])
        self.assertEqual(0.0, result["mae_0_1"])
        self.assertEqual([], result["blocking_reasons"])
        self.assertTrue(result["pass_eligible"])

    def test_candidate_sha_alone_cannot_trigger_fig15_frozen_baseline(self) -> None:
        from PIL import Image

        from scripts import origin_candidate_worker

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            render = root / "candidate.png"
            opju = root / "candidate.opju"
            image = Image.new("RGB", (850, 335), "white")
            image.save(source)
            image.save(render)
            opju.write_bytes(b"opju")
            with patch.object(
                origin_candidate_worker,
                "candidate_sha256",
                return_value="fc0fe92dc204e9b85105b12a6a2cecbb42cff4f91e2f4d9830842a23c19e7143",
            ):
                result = origin_candidate_worker.evaluate_visual_metrics(
                    figure="fig15",
                    candidate={"source_crop": str(source)},
                    png=render,
                    opju=opju,
                    output_dir=root,
                    hard_gate_status={"status": "pass"},
                    origin_export_qa=[],
                )

        self.assertTrue(result["pass_eligible"])
        self.assertNotIn("fig15_status", result)
        self.assertNotIn("fig15_frozen_baseline", result)

    def test_candidate_worker_propagates_builder_failure_without_built_status(self) -> None:
        import json

        from scripts import origin_candidate_worker

        class FailedBuilder:
            @staticmethod
            def build_origin_figure(**kwargs: object) -> dict[str, object]:
                return {
                    "status": "failed",
                    "error_code": "E121_ATTACH_POLICY_VIOLATION",
                    "message": "No visible Origin process is available.",
                    "origin_attach_not_attempted": True,
                    "opju_generation_allowed": False,
                    "pass_eligible": False,
                }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = root / "candidate.json"
            output = root / "out"
            candidate.write_text('{"figure":"fig15"}', encoding="utf-8")
            with patch.object(origin_candidate_worker, "is_admin", return_value=True), patch.object(
                origin_candidate_worker, "_load_aa2195_builder", return_value=FailedBuilder()
            ):
                result = origin_candidate_worker.run_live("fig15", candidate, output)

            readback = json.loads((output / "candidate_readback.json").read_text(encoding="utf-8"))
            metrics = json.loads((output / "candidate_visual_metrics.json").read_text(encoding="utf-8"))

        self.assertEqual("failed", result["status"])
        self.assertEqual("E121_ATTACH_POLICY_VIOLATION", result["error_code"])
        self.assertNotIn("candidate_export", result)
        self.assertNotIn("candidate_opju", result)
        self.assertEqual("failed", readback["builder_status"])
        self.assertEqual(["origin_builder_failed"], metrics["blocking_reasons"])
        self.assertFalse(metrics["pass_eligible"])

    def test_candidate_worker_records_fig12_effective_builder_route_fields(self) -> None:
        from scripts import origin_candidate_worker

        route = origin_candidate_worker._effective_builder_route(
            {
                "builder_route": {
                    "route": "native_source_calibrated_three_panel_contour",
                    "canvas_size": (805, 590),
                    "page_size_inches": (8.05, 5.9),
                    "expected_plot_count": 3,
                    "expected_plot_count_by_layer": {0: 1, 1: 1, 2: 1, 3: 0},
                    "expected_graphobject_count": 52,
                    "panel_inventory": [{"name": "PSC", "layout_percent": (12.2, 9.0, 27.8, 36.5)}],
                    "colorbar_inventory": [{"panel": "PSC", "bbox": (333.0, 82.0, 367.0, 188.0)}],
                    "fig12_colorbar_offsets": {0: {"dx": -32.0, "dy": 0.0}},
                    "fig12_label_sizes": {"mechanism": 13.0},
                    "fig12_matrix_biases": {0: -1.5, 1: 0.0, 2: 0.0},
                    "candidate_params": {"figure": "fig12"},
                }
            }
        )

        self.assertEqual("native_source_calibrated_three_panel_contour", route["route"])
        self.assertEqual(3, route["expected_plot_count"])
        self.assertEqual({0: 1, 1: 1, 2: 1, 3: 0}, route["expected_plot_count_by_layer"])
        self.assertEqual([{"panel": "PSC", "bbox": (333.0, 82.0, 367.0, 188.0)}], route["colorbar_inventory"])
        self.assertEqual({0: {"dx": -32.0, "dy": 0.0}}, route["fig12_colorbar_offsets"])
        self.assertEqual({"mechanism": 13.0}, route["fig12_label_sizes"])
        self.assertEqual({0: -1.5, 1: 0.0, 2: 0.0}, route["fig12_matrix_biases"])

    def test_candidate_worker_records_effective_builder_route(self) -> None:
        import json

        from scripts import origin_candidate_worker

        class SuccessfulBuilder:
            @staticmethod
            def build_origin_figure(**kwargs: object) -> dict[str, object]:
                output_dir = Path(kwargs["output_dir"])
                opju = output_dir / "fig16_builder_result.opju"
                pre = output_dir / "fig16_builder_pre_save.png"
                png = output_dir / "fig16_builder_post_reopen.png"
                opju.write_bytes(b"opju")
                pre.write_bytes(b"pre")
                png.write_bytes(b"png")
                return {
                    "status": "built_post_reopen_not_promoted",
                    "per_figure": {
                        "fig16": {
                            "status": "post_reopen_built",
                            "opju_path": str(opju),
                            "origin_rendered_exports": [
                                {"path": str(pre), "phase": "pre_save"},
                                {"path": str(png), "phase": "post_reopen"},
                            ],
                            "origin_candidate_hard_gate": {"status": "pass"},
                            "origin_export_qa": [],
                            "origin_object_readback": {},
                            "origin_object_readback_validation": {"status": "ok"},
                            "editable_view_evidence": {
                                "pre_save": {"status": "applied", "command": "win -z0;"},
                                "post_reopen": {"status": "applied", "command": "win -z0;"},
                            },
                            "builder_route": {
                                "route": "graphobject_source_calibrated_semantic_schematic",
                                "canvas_size": (720, 375),
                                "expected_plot_count": 0,
                                "expected_graphobject_count": 516,
                                "fig16_tuning": {"bar_top_dy": -1.0, "bar_bottom_dy": 1.0},
                                "fig16_colors": {"WH": "#ff9830", "DRV": "#00ff98", "DRX": "#d098ff"},
                                "fig16_text_sizes": {
                                    "header": 10.0,
                                    "legend": 9.5,
                                    "group_label": 12.0,
                                    "stage": 9.0,
                                    "relation": 10.0,
                                },
                                "candidate_params": {"figure": "fig16"},
                            },
                        }
                    },
                }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate = root / "candidate.json"
            output = root / "out"
            candidate.write_text('{"figure":"fig16"}', encoding="utf-8")
            source = root / "source.png"
            source.write_bytes(b"source")
            candidate.write_text(
                json.dumps({"figure": "fig16", "source_crop": str(source)}),
                encoding="utf-8",
            )
            with patch.object(origin_candidate_worker, "is_admin", return_value=True), patch.object(
                origin_candidate_worker, "_load_aa2195_builder", return_value=SuccessfulBuilder()
            ), patch.object(
                origin_candidate_worker,
                "evaluate_visual_metrics",
                return_value={"pass_eligible": True, "blocking_reasons": []},
            ), patch.object(
                origin_candidate_worker,
                "materialize_standard_evidence",
                return_value={"status": "ok", "pass_eligible": True},
            ) as materialize:
                result = origin_candidate_worker.run_live("fig16", candidate, output)

            readback = json.loads((output / "candidate_readback.json").read_text(encoding="utf-8"))
            manifest = json.loads((output / "candidate_manifest.json").read_text(encoding="utf-8"))

        expected = {
            "route": "graphobject_source_calibrated_semantic_schematic",
            "canvas_size": [720, 375],
            "expected_plot_count": 0,
            "expected_graphobject_count": 516,
            "fig16_tuning": {"bar_top_dy": -1.0, "bar_bottom_dy": 1.0},
            "fig16_colors": {"WH": "#ff9830", "DRV": "#00ff98", "DRX": "#d098ff"},
            "fig16_text_sizes": {"header": 10.0, "legend": 9.5, "group_label": 12.0, "stage": 9.0, "relation": 10.0},
            "candidate_params": {"figure": "fig16"},
        }
        self.assertEqual("built_real_candidate_not_promoted", result["status"])
        self.assertEqual("provisional", manifest["target_visual_gate"]["baseline_role"])
        self.assertFalse(manifest["target_visual_gate"]["visual_baseline_promoted"])
        self.assertFalse(manifest["release_status"]["overall_release_pass"])
        self.assertEqual(expected, readback["effective_builder_route"])
        self.assertEqual("win -z0;", readback["editable_view_evidence"]["pre_save"]["command"])
        self.assertEqual("win -z0;", readback["editable_view_evidence"]["post_reopen"]["command"])
        self.assertEqual(expected, manifest["effective_builder_route"])
        self.assertEqual("evidence", manifest["standard_evidence_dir"])
        self.assertEqual("ok", manifest["standard_evidence"]["status"])
        kwargs = materialize.call_args.kwargs
        self.assertEqual("fig16_builder_pre_save.png", kwargs["pre_save"].name)
        self.assertEqual("candidate_export.png", kwargs["post_reopen"].name)

    def test_combined_review_package_sanitizes_absolute_json_paths(self) -> None:
        from scripts import build_combined_review_package

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = root / "fig15_run011.png"
            image.write_bytes(b"png")
            manifest = root / "manifest.json"
            manifest.write_text(
                '{"source":"%s","nested":{"path":"%s"}}'
                % (str(image).replace("\\", "\\\\"), str(image).replace("\\", "\\\\")),
                encoding="utf-8",
            )
            zip_out = root / "package.zip"

            build_combined_review_package.build(
                zip_out,
                [
                    (manifest, "fig15/candidate_manifest.json"),
                    (image, "fig15/reproduction/fig15_run011.png"),
                ],
            )

            import json
            import zipfile

            with zipfile.ZipFile(zip_out) as archive:
                payload = json.loads(archive.read("fig15/candidate_manifest.json").decode("utf-8"))

        self.assertEqual("fig15/reproduction/fig15_run011.png", payload["source"])
        self.assertEqual("fig15/reproduction/fig15_run011.png", payload["nested"]["path"])


class VersionContractTests(unittest.TestCase):
    def test_skill_documents_v589_authorized_attach_and_visual_closure(self) -> None:
        root = Path(__file__).resolve().parents[1]
        skill = (root / "SKILL.md").read_text(encoding="utf-8-sig")

        self.assertIn("OriginPlot Skill v5.8.9", skill)
        self.assertIn("v5.8.9 Authorized Attach and Visual Closure", skill)
        self.assertIn("v5.8.9-p4 Default Administrator Attach Policy", skill)
        self.assertIn("Formal production runs default to administrator attach-existing", skill)
        self.assertIn("must already be the administrator-opened visible Origin process", skill)
        self.assertIn("formal builders must verify that a visible `Origin*` process exists", skill)
        self.assertIn("origin_attach_not_attempted=true", skill)
        self.assertIn("opju_generation_allowed=false", skill)
        self.assertIn("diagnostic_new_hidden_not_pass_eligible", skill)
        self.assertIn("E121_ATTACH_POLICY_VIOLATION", skill)
        self.assertIn("op.detach()", skill)
        self.assertIn("demo_cyan_ratio", skill)

    def test_skill_documents_page_dot_and_font_point_unit_gate(self) -> None:
        root = Path(__file__).resolve().parents[1]
        skill = (root / "SKILL.md").read_text(encoding="utf-8-sig")

        self.assertIn("page.width/page.height are dots", skill)
        self.assertIn("page.width = width_inches * page.resx", skill)
        self.assertIn("layer.unit=1 uses 0..100 page percent", skill)
        self.assertIn("text fsize is points", skill)

    def test_skill_requires_editable_page_fit_after_save_and_reopen(self) -> None:
        skill = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("win -z0", skill)
        self.assertIn("editable_view_evidence", skill)
        self.assertIn("does not change page geometry", skill)
        self.assertIn("E540_PAGE_UNIT_SCALE_MISMATCH", skill)

    def test_skill_documents_fig15_post_reopen_object_gates(self) -> None:
        root = Path(__file__).resolve().parents[1]
        skill = (root / "SKILL.md").read_text(encoding="utf-8-sig")

        self.assertIn("v5.8.9-p2 Fig15 Object Persistence Patch", skill)
        self.assertIn("layer.axis.showAxes", skill)
        self.assertIn("scale-attached spanning caption", skill)
        self.assertIn("Origin escape sequences", skill)
        self.assertIn("curve-shape ROI", skill)
        self.assertIn("worksheet arrowhead paths", skill)
        self.assertIn("E122_ORIGIN_DEMO_EXPORT_BLOCKED", skill)

    def test_skill_documents_p11_origin2022_deep_plot_readback(self) -> None:
        root = Path(__file__).resolve().parents[1]
        skill = (root / "SKILL.md").read_text(encoding="utf-8-sig")

        self.assertIn("OriginPlot Skill v5.8.9-p13", skill)
        self.assertIn("v5.8.9-p11 Origin 2022 Deep Plot Readback", skill)
        self.assertIn("layer.plotn.pid", skill)
        self.assertIn("%A=xof(Ydataset)", skill)
        self.assertIn("restore the string register", skill)
        self.assertIn("Plot.lt_range()", skill)

    def test_skill_documents_p12_portable_release_and_live_evidence_closure(self) -> None:
        root = Path(__file__).resolve().parents[1]
        skill = (root / "SKILL.md").read_text(encoding="utf-8-sig")

        self.assertIn("OriginPlot Skill v5.8.9-p13", skill)
        self.assertIn("v5.8.9-p12 Portable Release and Live Evidence Closure", skill)
        self.assertIn("validate_release_candidate.py", skill)
        self.assertIn("release_ready_for_fig12_targeted_optimization", skill)
        self.assertIn("Run047", skill)
        self.assertIn("Run052", skill)
        self.assertIn("Run062_clean_reference_baseline", skill)

    def test_test_runner_reports_v589_p12_schema(self) -> None:
        root = Path(__file__).resolve().parents[1]
        runner = (root / "scripts" / "run_all_tests.py").read_text(encoding="utf-8-sig")
        self.assertIn('"schema": "originplot.run_all_tests.v5.8.9-p13"', runner)
        self.assertIn('"skill_version": "5.8.9-p13"', runner)


if __name__ == "__main__":
    unittest.main()
