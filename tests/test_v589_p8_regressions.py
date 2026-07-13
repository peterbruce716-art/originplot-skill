from __future__ import annotations

import os
import importlib.util
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(
    os.environ.get("ORIGINPLOT_SKILL_ROOT")
    or Path(__file__).resolve().parents[1]
).resolve()
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))


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


class FakeLabel:
    def __init__(self, text: str, x: float, y: float) -> None:
        self.text = text
        self.x = x
        self.y = y
        self.name = ""
        self.properties: dict[str, float] = {}
        self.obj = self

    def SetName(self, name: str) -> None:
        self.name = name

    def set_int(self, name: str, value: int) -> None:
        self.properties[name] = value

    def set_float(self, name: str, value: float) -> None:
        self.properties[name] = value


class FakeLayer:
    def __init__(self) -> None:
        self.obj = type("LayerObject", (), {"GraphObjects": FakeGraphObjects()})()
        self.commands: list[str] = []
        self.labels: list[FakeLabel] = []

    def lt_exec(self, command: str) -> None:
        self.commands.append(command)

    def add_label(self, text: str, x: float, y: float) -> FakeLabel:
        label = FakeLabel(text, x, y)
        self.labels.append(label)
        return label


class Fig16ObjectRegressionTests(unittest.TestCase):
    def test_fig16_geometry_uses_source_stacked_drv_drx_semantics(self) -> None:
        from builders.aa2195.geometry import fig16_geometry

        geometry = fig16_geometry()
        by_name = {record["name"]: record for record in geometry["bars"]}

        self.assertEqual(21, len(geometry["bars"]))
        for index in range(1, 8):
            wh = by_name[f"wh_{index:02d}"]
            drv = by_name[f"drv_{index:02d}"]
            drx = by_name[f"drx_{index:02d}"]

            self.assertLess(wh["bbox"][0], drv["bbox"][0])
            self.assertEqual(drv["bbox"][0], drx["bbox"][0])
            self.assertEqual(drv["bbox"][2], drx["bbox"][2])
            self.assertEqual(drv["bbox"][1], drx["bbox"][3])
            self.assertEqual(drv["bbox"][3], wh["bbox"][3])

        self.assertEqual((13, 62, 301, 365), geometry["group_boxes"][0]["bbox"])
        self.assertEqual((308, 62, 502, 365), geometry["group_boxes"][1]["bbox"])
        self.assertEqual((510, 62, 702, 365), geometry["group_boxes"][2]["bbox"])

    def test_group_boxes_are_styled_as_blue_dashed_no_fill_objects(self) -> None:
        from builders.aa2195 import fig16_builder

        layer = FakeLayer()
        fig16_builder._draw_rectangle(
            layer,
            "fig16_group_box_psc",
            (13, 62, 301, 365),
            "#1e62ff",
            dashed=True,
            transparent=True,
        )

        self.assertEqual(1, len(layer.obj.GraphObjects.created))
        rectangle = layer.obj.GraphObjects.created[0]
        self.assertEqual(8, rectangle.object_type)
        self.assertEqual(2, rectangle.properties["lineStyle"])
        self.assertEqual(100, rectangle.properties["transparency"])
        self.assertTrue(any("color=color(30,98,255)" in command for command in layer.commands))
        self.assertFalse(any(".color=color(0,0,0)" in command for command in layer.commands))

    def test_fig16_builder_declares_axisless_contract(self) -> None:
        from builders.aa2195 import fig16_builder

        test_module_path = SKILL_ROOT / "tests" / "test_v589_aa2195_reproduction.py"
        spec = importlib.util.spec_from_file_location("originplot_v589_test_support", test_module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        op = module.FakeBuilderOrigin()

        result = fig16_builder.build(op, {})

        self.assertEqual(2, len(result["axis_contract"]))
        self.assertEqual({0, 1}, {item["layer_index"] for item in result["axis_contract"]})
        self.assertEqual({0}, {item["layer_index"] for item in result["legend_plot_reference_contracts"]})
        for axis_contract in result["axis_contract"]:
            self.assertEqual(0, axis_contract["x.showAxes"])
            self.assertEqual(0, axis_contract["y.showAxes"])
            self.assertEqual(0, axis_contract["x.showLabels"])
            self.assertEqual(0, axis_contract["y.showLabels"])
            self.assertEqual(0, axis_contract["x.ticks"])
            self.assertEqual(0, axis_contract["y.ticks"])
        self.assertTrue(
            any("layer.x.showAxes=0" in command for command in op.page.layers[0].commands)
        )

    def test_contract_matching_is_case_insensitive_for_origin_names(self) -> None:
        from builders.aa2195.readback import validate_graphobject_contracts

        readback = {
            "layers": [
                {
                    "graph_object_readback": {
                        "objects": [
                            {
                                "name": "FIG16_BAR_WH_01",
                                "attach": 2,
                                "standard_type": "rectangle",
                            }
                        ],
                        "enumerated_objects": [
                            {
                                "name": "FIG16_BAR_WH_01",
                                "attach": 2,
                                "standard_type": "rectangle",
                            }
                        ],
                        "missing_names": [],
                        "enumeration_status": "ok",
                    }
                }
            ]
        }

        result = validate_graphobject_contracts(
            readback,
            {"fig16_bar_wh_01": {"attach": 2}},
        )

        self.assertEqual("ok", result["status"])
        self.assertEqual([], result["mismatches"])

    def test_rectangle_coordinates_use_native_graphobject_properties(self) -> None:
        from builders.aa2195 import fig16_builder

        layer = FakeLayer()
        fig16_builder._draw_rectangle(
            layer,
            "fig16_bar_wh_01",
            (24, 148, 61, 334),
            "#ff9828",
        )

        self.assertEqual(1, len(layer.obj.GraphObjects.created))
        rectangle = layer.obj.GraphObjects.created[0]
        self.assertEqual(8, rectangle.object_type)
        self.assertEqual("fig16_bar_wh_01", rectangle.name)
        self.assertEqual(42.5, rectangle.properties["x"])
        self.assertEqual(134.0, rectangle.properties["y"])
        self.assertEqual(37.0, rectangle.properties["dx"])
        self.assertEqual(186.0, rectangle.properties["dy"])
        self.assertNotIn("y1", rectangle.properties)
        self.assertNotIn("y2", rectangle.properties)

    def test_text_uses_add_label_without_command_arguments_in_content(self) -> None:
        from builders.aa2195 import fig16_builder

        layer = FakeLayer()
        fig16_builder._add_text(
            layer,
            "fig16_header_h",
            "H: Hardening level",
            18,
            22,
            10.0,
        )

        self.assertEqual(1, len(layer.labels))
        label = layer.labels[0]
        self.assertEqual("H: Hardening level", label.text)
        self.assertEqual("fig16_header_h", label.name)
        self.assertEqual(2, label.properties["attach"])
        self.assertFalse(any("label -n" in command for command in layer.commands))

    def test_stage_circle_uses_verified_originext_ellipse_object(self) -> None:
        from builders.aa2195 import fig16_builder

        helper = getattr(fig16_builder, "_draw_ellipse", None)
        self.assertIsNotNone(helper)
        layer = FakeLayer()
        helper(
            layer,
            "fig16_stage_circle_01",
            (52, 345, 70, 363),
            "#505050",
            transparent=True,
        )

        self.assertEqual(1, len(layer.obj.GraphObjects.created))
        ellipse = layer.obj.GraphObjects.created[0]
        self.assertEqual(9, ellipse.object_type)
        self.assertEqual("fig16_stage_circle_01", ellipse.name)
        self.assertEqual(61.0, ellipse.properties["x"])
        self.assertEqual(21.0, ellipse.properties["y"])
        self.assertEqual(18.0, ellipse.properties["dx"])
        self.assertEqual(18.0, ellipse.properties["dy"])
        self.assertNotIn("y1", ellipse.properties)
        self.assertNotIn("y2", ellipse.properties)


if __name__ == "__main__":
    unittest.main()
