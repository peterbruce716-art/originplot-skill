from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


SKILL_ROOT = Path(
    os.environ.get("ORIGINPLOT_SKILL_ROOT")
    or Path(__file__).resolve().parents[1]
).resolve()
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))


class GraphObjectsWithoutAdd:
    pass


class LayerWithoutNativeAdd:
    def __init__(self) -> None:
        self.obj = type("LayerObject", (), {"GraphObjects": GraphObjectsWithoutAdd()})()
        self.commands: list[str] = []

    def lt_exec(self, command: str) -> None:
        self.commands.append(command)


class Fig16PersistentRectangleRegressionTests(unittest.TestCase):
    def test_rectangle_route_fails_closed_without_native_add(self) -> None:
        from builders.aa2195 import fig16_builder

        layer = LayerWithoutNativeAdd()
        with self.assertRaisesRegex(RuntimeError, "E401_GRAPHOBJECT_READBACK_UNVERIFIED"):
            fig16_builder._draw_rectangle(
                layer,
                "fig16_bar_wh_01",
                (24, 148, 63, 334),
                "#ff9828",
            )

        self.assertFalse(any("draw -n" in command for command in layer.commands))

    def test_geometry_contract_accepts_persistent_xy_dxdy(self) -> None:
        from builders.aa2195.readback import validate_graphobject_contracts

        record = {
            "name": "FIG16_BAR_WH_01",
            "attach": 2,
            "standard_type": "rectangle",
            "x": 43.5,
            "y": 134.0,
            "dx": 39.0,
            "dy": 186.0,
        }
        readback = {
            "layers": [
                {
                    "graph_object_readback": {
                        "objects": [record],
                        "enumerated_objects": [record],
                        "missing_names": [],
                        "enumeration_status": "ok",
                    }
                }
            ]
        }
        result = validate_graphobject_contracts(
            readback,
            {
                "fig16_bar_wh_01": {
                    "attach": 2,
                    "geometry": {
                        "x": 43.5,
                        "y": 134.0,
                        "dx": 39.0,
                        "dy": 186.0,
                        "tolerance": 0.75,
                    },
                }
            },
        )

        self.assertEqual("ok", result["status"])
        self.assertEqual([], result["mismatches"])

    def test_geometry_contract_rejects_collapsed_rectangle_height(self) -> None:
        from builders.aa2195.readback import validate_graphobject_contracts

        record = {
            "name": "fig16_bar_wh_01",
            "attach": 2,
            "standard_type": "rectangle",
            "x": 43.5,
            "y": 101.3,
            "dx": 39.0,
            "dy": 52.7,
        }
        readback = {
            "layers": [
                {
                    "graph_object_readback": {
                        "objects": [record],
                        "enumerated_objects": [record],
                        "missing_names": [],
                        "enumeration_status": "ok",
                    }
                }
            ]
        }
        result = validate_graphobject_contracts(
            readback,
            {
                "fig16_bar_wh_01": {
                    "attach": 2,
                    "geometry": {
                        "x": 43.5,
                        "y": 134.0,
                        "dx": 39.0,
                        "dy": 186.0,
                        "tolerance": 0.75,
                    },
                }
            },
        )

        self.assertEqual("failed", result["status"])
        self.assertTrue(
            any(item["property"] in {"y", "dy"} for item in result["mismatches"])
        )


if __name__ == "__main__":
    unittest.main()
