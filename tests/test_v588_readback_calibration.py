from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakePlot:
    def __init__(self, name: str, plot_type: int, *, visible: bool = True) -> None:
        self.name = name
        self.type = plot_type
        self.visible = visible
        self.lt_range = "[Book1]Sheet1!(A,B)"
        self.color = "#1b35ff"
        self.linewidth = 2.0


class FakeLayer:
    name = "Layer1"

    def __len__(self) -> int:
        return 0

    def plot_list(self):
        return [FakePlot("p1", 200), FakePlot("p2", 200)]


class FakeOrigin:
    def __init__(self) -> None:
        self.requested_page_type = None

    def pages(self, page_type: str):
        self.requested_page_type = page_type
        return iter(["graph-page"])


class FakeSemanticSheet:
    name = "RawData"


class FakeSemanticBook:
    def __len__(self):
        return 1

    def __getitem__(self, index):
        if index != 0:
            raise IndexError(index)
        return FakeSemanticSheet()


class FakeSemanticOrigin:
    def __init__(self) -> None:
        self.register_a = "preserve-me"

    def lt_int(self, formula: str):
        values = {
            "layer.plot1.pid": 200,
            "layer.plot1.show": 1,
            "layer.plot2.pid": 201,
            "layer.plot2.show": 0,
        }
        return values[formula]

    def get_lt_str(self, name: str):
        values = {
            "layer.plot1.name$": "Book2_B",
            "layer.plot2.name$": "Book2_D",
        }
        if name == "%A":
            return self.register_a
        return values[name]

    def lt_exec(self, command: str):
        if command == "%A=xof(Book2_B);":
            self.register_a = "Book2_A"
        elif command == "%A=xof(Book2_D);":
            self.register_a = "Book2_C"
        else:
            raise AssertionError(command)
        return True

    def set_lt_str(self, name: str, value: str):
        if name != "%A":
            raise AssertionError(name)
        self.register_a = value

    def find_book(self, book_type: str, name: str):
        if (book_type, name) == ("w", "Book2"):
            return FakeSemanticBook()
        return None


class FakeXYZSemanticOrigin(FakeSemanticOrigin):
    def lt_int(self, formula: str):
        if formula == "layer.plot1.pid":
            return 243
        if formula == "layer.plot1.show":
            return 1
        return super().lt_int(formula)

    def get_lt_str(self, name: str):
        if name == "layer.plot1.name$":
            return "Book2_C"
        return super().get_lt_str(name)

    def lt_exec(self, command: str):
        if command == "%A=xof(Book2_C);":
            self.register_a = "Book2_B"
            return True
        return super().lt_exec(command)


class FakeGraphObject:
    def __init__(self, name: str, object_type: int = 9, type_name: str | None = None) -> None:
        self._name = name
        self._object_type = object_type
        self._type_name = type_name
        self.properties = {}

    def GetName(self):
        return self._name

    def GetObjectType(self):
        return self._object_type

    def GetTypeName(self):
        if self._type_name is not None:
            return self._type_name
        return "Ellipse" if self._object_type == 9 else "Object"

    def GetNumProp(self, name: str):
        return self.properties.get(name, 0)

    def GetStrProp(self, name: str):
        return self.properties.get(name, "")

    def GetText(self):
        return self.properties.get("text", "")

    def SetName(self, name: str):
        self._name = name

    def SetNumProp(self, name: str, value):
        self.properties[name] = value


class FakeGraphObjects:
    def __init__(self, objects=None) -> None:
        self.objects = {obj.GetName().lower(): obj for obj in (objects or [])}

    def GetCount(self):
        return len(self.objects)

    def __iter__(self):
        return iter(self.objects.values())

    def __call__(self, name: str):
        if not isinstance(name, str):
            raise TypeError("name required")
        direct = self.objects.get(name.lower())
        if direct is not None:
            return direct
        return next((obj for obj in self.objects.values() if obj.GetName().lower() == name.lower()), None)

    def Add(self, object_type: int):
        obj = FakeGraphObject("", object_type)
        self.objects[f"pending_{len(self.objects)}"] = obj
        return obj


class FakeObjectLayer:
    def __init__(self, objects=None) -> None:
        self.obj = type("LayerObject", (), {"GraphObjects": FakeGraphObjects(objects)})()


class FakeLabTalkLayer:
    def __init__(self) -> None:
        self.commands = []

    def lt_exec(self, command: str):
        self.commands.append(command)


class FakeSpeedModeLayer(FakeLayer):
    def __init__(self) -> None:
        self.obj = type("LayerObject", (), {"GraphObjects": FakeGraphObjects([])})()

    def activate(self) -> None:
        return None


class FakeSpeedModePage:
    def __init__(self) -> None:
        self.layers = [FakeSpeedModeLayer(), FakeSpeedModeLayer()]

    def __iter__(self):
        return iter(self.layers)

    def activate(self) -> None:
        return None


class FakeSpeedModeOrigin:
    def __init__(self) -> None:
        self.requests: list[str] = []

    def lt_exec(self, command: str) -> None:
        self.requests.append(command)

    def lt_int(self, name: str) -> int:
        self.requests.append(name)
        if name in {"page.speedMode", "layer.speedMode", "count"}:
            return 0
        if name.startswith("layer."):
            return 0
        raise KeyError(name)


class FakeCalibrationInspectOrigin:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def set_show(self, show: bool) -> None:
        self.calls.append(("set_show", show))

    def new(self, asksave: bool = True) -> None:
        self.calls.append(("new", asksave))

    def open(self, path: str, **kwargs):
        self.calls.append(("open", {"path": path, "kwargs": kwargs}))
        return True

    def save(self, path: str) -> None:
        self.calls.append(("save", path))

    def pages(self, page_type: str):
        self.calls.append(("pages", page_type))
        return []

    def exit(self) -> None:
        self.calls.append(("exit", None))


class ReadbackCalibrationV588Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.inspection = load_module("inspection_adapter_v588_test", ROOT / "adapters" / "inspection" / "adapter.py")
        cls.calibration = load_module("calibration_probe_v588_test", ROOT / "scripts" / "origin_calibration_probe.py")
        cls.candidate = load_module("candidate_worker_v588_test", ROOT / "scripts" / "origin_candidate_worker.py")
        cls.inspect_worker = load_module(
            "calibration_inspect_worker_v588_test",
            ROOT / "scripts" / "origin_calibration_inspect_worker.py",
        )

    def test_plot_list_is_primary_when_len_layer_is_zero(self) -> None:
        result = self.inspection.inspect_layer_plots(FakeLayer(), labtalk_count=2)
        self.assertEqual(2, result["plot_count"])
        self.assertEqual("plot_list", result["primary_route"])
        self.assertFalse(result["readback_disagreement"])

    def test_plot_readback_records_semantic_type_visibility_style_and_binding(self) -> None:
        result = self.inspection.inspect_layer_plots(FakeLayer(), labtalk_count=2)
        first = result["plot_details"][0]
        self.assertEqual(200, first["plot_type_code"])
        self.assertEqual("line", first["plot_family"])
        self.assertIs(first["visible"], True)
        self.assertEqual("#1b35ff", first["line_color"])
        self.assertEqual(2.0, first["line_width"])
        self.assertEqual("[Book1]Sheet1!(A,B)", first["data_binding_raw"])
        self.assertEqual("Book1", first["data_workbook"])
        self.assertEqual("Sheet1", first["data_worksheet"])
        self.assertEqual("A", first["x_column"])
        self.assertEqual("B", first["y_column"])

    def test_plot_readback_preserves_origin_contour_zlevels_dictionary(self) -> None:
        plot = FakePlot("contour", 243)
        plot.zlevels = {"minors": 0, "levels": [27.9, 35.55, 41.08, 54.0]}

        result = self.inspection._plot_detail(plot, 0)

        self.assertEqual(
            {"minors": 0, "levels": [27.9, 35.55, 41.08, 54.0]},
            result["zlevels"],
        )

    def test_plot_readback_prefers_origin2022_labtalk_semantics_and_restores_register(self) -> None:
        origin = FakeSemanticOrigin()
        result = self.inspection.inspect_layer_plots(FakeLayer(), labtalk_count=2, op=origin)
        first, second = result["plot_details"]
        self.assertEqual(200, first["plot_type_code"])
        self.assertEqual("line", first["plot_family"])
        self.assertIs(first["visible"], True)
        self.assertEqual("Book2_A", first["x_dataset"])
        self.assertEqual("Book2_B", first["y_dataset"])
        self.assertEqual("Book2", first["data_workbook"])
        self.assertEqual("RawData", first["data_worksheet"])
        self.assertEqual("A", first["x_column"])
        self.assertEqual("B", first["y_column"])
        self.assertEqual("[Book2]RawData!(A,B)", first["data_binding_raw"])
        self.assertEqual("[Book1]Sheet1!(A,B)", first["graph_plot_range"])
        self.assertEqual(201, second["plot_type_code"])
        self.assertEqual("scatter", second["plot_family"])
        self.assertIs(second["visible"], False)
        self.assertEqual("preserve-me", origin.register_a)

    def test_plot_readback_records_labtalk_disagreement(self) -> None:
        result = self.inspection.inspect_layer_plots(FakeLayer(), labtalk_count=1)
        self.assertTrue(result["readback_disagreement"])
        self.assertEqual(2, result["plot_list_count"])
        self.assertEqual(1, result["labtalk_layer_count"])

    def test_xyz_contour_readback_resolves_complete_worksheet_xyz_chain(self) -> None:
        origin = FakeXYZSemanticOrigin()
        result = self.inspection.inspect_layer_plots(FakeLayer(), labtalk_count=2, op=origin)
        first = result["plot_details"][0]
        self.assertEqual(243, first["plot_type_code"])
        self.assertEqual("worksheet_xyz_contour", first["plot_family"])
        self.assertEqual("A", first["x_column"])
        self.assertEqual("B", first["y_column"])
        self.assertEqual("C", first["z_column"])
        self.assertEqual("[Book2]RawData!(A,B,C)", first["data_binding_raw"])
        self.assertEqual("preserve-me", origin.register_a)

    def test_graph_pages_use_origin_single_letter_type_code(self) -> None:
        origin = FakeOrigin()
        self.assertEqual(["graph-page"], self.inspection.origin_graph_pages(origin))
        self.assertEqual("g", origin.requested_page_type)

    def test_aa2195_readback_records_speed_mode_off_after_reopen(self) -> None:
        from builders.aa2195 import readback

        result = readback.inspect_page(FakeSpeedModeOrigin(), FakeSpeedModePage())
        speed = result["speed_mode_state"]
        self.assertEqual("ok", speed["status"])
        self.assertTrue(speed["all_off"])
        self.assertEqual(0, speed["values"]["page.speedMode"])
        self.assertEqual([0, 0], [item["layer.speedMode"] for item in speed["values"]["layers"]])

    def test_calibration_inspect_worker_reopens_editable_and_saves_same_path(self) -> None:
        fake_origin = FakeCalibrationInspectOrigin()
        original = sys.modules.get("originpro")
        sys.modules["originpro"] = fake_origin
        try:
            with tempfile.TemporaryDirectory() as tmp:
                project = Path(tmp) / "probe.opju"
                project.write_bytes(b"fake-opju")
                project.chmod(0o444)
                result = self.inspect_worker.inspect_project(
                    project,
                    Path(tmp) / "pre",
                    Path(tmp) / "post",
                )
        finally:
            if original is None:
                sys.modules.pop("originpro", None)
            else:
                sys.modules["originpro"] = original

        open_calls = [payload for name, payload in fake_origin.calls if name == "open"]
        self.assertEqual(1, len(open_calls))
        self.assertEqual(False, open_calls[0]["kwargs"].get("readonly"))
        self.assertEqual(False, open_calls[0]["kwargs"].get("asksave"))
        save_calls = [payload for name, payload in fake_origin.calls if name == "save"]
        self.assertEqual([str(project)], save_calls)
        editable = result["editable_open_evidence"]
        self.assertTrue(editable["readonly_before"])
        self.assertFalse(editable["readonly_after"])
        self.assertTrue(editable["readonly_attribute_cleared"])
        self.assertFalse(editable["origin_open_readonly_requested"])
        self.assertTrue(editable["same_path_save_verified_after_reopen"])

    def test_graphobjects_are_read_by_expected_name(self) -> None:
        expected = ["probe_rect_01", "probe_line_01"]
        layer = FakeObjectLayer([FakeGraphObject(name, 8 if "rect" in name else 4) for name in expected])
        result = self.inspection.inspect_graph_objects(layer, expected_names=expected)
        self.assertEqual("ok", result["status"])
        self.assertEqual(expected, [item["name"].lower() for item in result["objects"]])
        self.assertEqual([], result["missing_names"])
        self.assertEqual(expected, [item["name"].lower() for item in result["enumerated_objects"]])
        self.assertEqual("ok", result["enumeration_status"])

    def test_graphobject_readback_normalizes_unknown_typename_and_standard_family(self) -> None:
        layer = FakeObjectLayer([FakeGraphObject("probe_line_01", 4, type_name="Unknow")])
        result = self.inspection.inspect_graph_objects(layer, expected_names=["probe_line_01"])
        record = result["objects"][0]
        self.assertEqual("Unknown", record["type_name"])
        self.assertEqual("line", record["standard_type"])

    def test_calibration_plan_requires_full_post_reopen_probe_set(self) -> None:
        plan = self.calibration.planned_probe_manifest()
        self.assertTrue(plan["post_reopen_required"])
        self.assertEqual(
            {"one_line": 1, "two_lines": 2, "contour_matrix": 1, "column": 1},
            plan["probes"]["plot_readback"]["expected_post_reopen_counts"],
        )
        self.assertEqual(
            ["probe_rect_01", "probe_line_01", "probe_text_01", "probe_circle_01"],
            plan["probes"]["graphobject_readback"]["expected_object_names"],
        )
        palette_keys = plan["probes"]["contour_palette"]["required_output_keys"]
        self.assertIn("default_red_region_absent", palette_keys)
        self.assertIn("post_reopen_palette_stable", palette_keys)

    def test_pre_save_only_evidence_cannot_pass(self) -> None:
        result = self.calibration.evaluate_probe_gate(
            "plot_readback",
            {"pre_save": {"one_line": {"plot_count": 1}}, "post_reopen": {}},
        )
        self.assertFalse(result["verified"])
        self.assertEqual("E526_POST_REOPEN_EVIDENCE_REQUIRED", result["error_code"])

    def test_live_partial_probe_returns_nonzero(self) -> None:
        self.assertEqual(0, self.calibration.probe_exit_code({"mode": "dry_run", "status": "planned_not_verified"}))
        self.assertEqual(0, self.calibration.probe_exit_code({"mode": "live_origin_probe", "status": "ok"}))
        self.assertEqual(1, self.calibration.probe_exit_code({"mode": "live_origin_probe", "status": "partial"}))

    def test_named_circle_uses_originext_ellipse_type(self) -> None:
        self.assertEqual(9, self.calibration.GRAPHOBJECT_ELLIPSE_TYPE)
        layer = FakeObjectLayer()
        self.assertTrue(self.calibration.add_named_ellipse(layer, "probe_circle_01", 0.62, 0.62, 0.88, 0.88))
        circle = layer.obj.GraphObjects("probe_circle_01")
        self.assertIsNotNone(circle)
        self.assertEqual(9, circle.GetObjectType())

    def test_three_region_matrix_has_contiguous_vertical_bands(self) -> None:
        matrix = self.calibration.three_region_matrix(rows=4, band_width=3)
        self.assertEqual((4, 9), matrix.shape)
        self.assertTrue(np.all(matrix[:, :3] == 0))
        self.assertTrue(np.all(matrix[:, 3:6] == 1))
        self.assertTrue(np.all(matrix[:, 6:] == 2))

    def test_palette_commands_set_three_direct_colors(self) -> None:
        layer = FakeLabTalkLayer()
        self.calibration.apply_three_region_palette(layer, [101, 202, 303])
        commands = " ".join(layer.commands)
        self.assertIn("numColors=3", commands)
        self.assertIn("color1=101", commands)
        self.assertIn("color2=202", commands)
        self.assertIn("color3=303", commands)
        self.assertIn("updateScale", commands)

    def test_palette_metrics_isolate_main_plot_from_colorbar(self) -> None:
        image = np.full((120, 360, 3), 255, dtype=np.uint8)
        image[10:110, 10:100] = [247, 189, 114]
        image[10:110, 100:190] = [100, 180, 95]
        image[10:110, 190:280] = [75, 130, 200]
        image[10:43, 320:340] = [75, 130, 200]
        image[43:76, 320:340] = [100, 180, 95]
        image[76:110, 320:340] = [247, 189, 114]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "palette.png"
            Image.fromarray(image).save(path)
            metrics = self.inspect_worker.palette_metrics(path)
        self.assertGreater(metrics["orange_iou"], 0.95)
        self.assertGreater(metrics["green_iou"], 0.95)
        self.assertGreater(metrics["blue_iou"], 0.95)

    def test_candidate_worker_uses_packaged_builder(self) -> None:
        builder_path = self.candidate.AA2195_BUILDER_PACKAGE.resolve()
        self.assertTrue(builder_path.is_relative_to(ROOT.resolve()))
        self.assertTrue((builder_path / "__init__.py").exists())
        self.assertFalse(hasattr(self.candidate, "AA2195_REPRO_SCRIPT"))


if __name__ == "__main__":
    unittest.main()
