from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


semantic = load_module("semantic_figure_benchmark", ROOT / "scripts" / "semantic_figure_benchmark.py")
compiler = load_module("originplot_compile_v5", ROOT / "scripts" / "originplot_compile_v5.py")


class SemanticFigureBenchmarkTests(unittest.TestCase):
    def test_missing_semantic_objects_block_low_mae(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source.png"
            export = tmp_path / "export.png"
            image = Image.new("RGB", (120, 80), "white")
            draw = ImageDraw.Draw(image)
            draw.line((10, 60, 110, 20), fill="blue", width=2)
            image.save(source)
            image.save(export)
            spec = {
                "schema": "originplot.semantic_figure_benchmark.v1",
                "figure_id": "fig15",
                "recipe": "recipe.schematic.dual_panel_curve.v1",
                "source_image": "source.png",
                "exports": [{"id": "post", "path": "export.png"}],
                "expected": {
                    "structure": {"graph_pages": 1, "layers": 2, "plots": 2},
                    "data": {"curve_series": 2},
                    "geometry": {"panel_count": 2},
                    "style": {"blue_curves": 2},
                    "required_objects": [
                        {"role": "axis_arrow", "expected_count": 4, "critical": True},
                        {"role": "stage_marker", "expected_count": 5, "critical": True},
                    ],
                },
                "actual": {
                    "structure": {"graph_pages": 1, "layers": 2, "plots": 2},
                    "data": {"curve_series": 2},
                    "geometry": {"panel_count": 2},
                    "style": {"blue_curves": 2},
                    "objects": [{"role": "axis_arrow", "count": 4}],
                },
            }
            result = semantic.benchmark(spec, tmp_path, tmp_path / "evidence")
            self.assertEqual(result["report"]["status"], "failed")
            self.assertIn("MISSING_REQUIRED_OBJECTS", result["report"]["blocking_failures"])
            self.assertGreater(result["report"]["scores"]["visual_score"], 0.9)
            self.assertLess(result["report"]["scores"]["semantic_coverage"], 1.0)

    def test_compile_v53_contour_recipe_emits_benchmark_ops(self) -> None:
        spec = {
            "schema": "originplot.figurespec.v5",
            "figure": {"id": "fig12", "recipe": "recipe.contour.discrete_three_panel.v1", "family": "multi_panel_contour"},
            "runtime": {
                "project_path": "out/fig12.opju",
                "pre_save_export": "out/pre.png",
                "post_reopen_export": "out/post.png",
            },
            "origin": {
                "target_version": "2022",
                "adapter_policy": "capability_driven",
                "primary_graph": "Fig12",
                "capability_profile": "capabilities/origin-2022-v5.json",
                "operation_routes": {
                    "session": "originpro",
                    "data": "originpro",
                    "graph": "originpro",
                    "plot": "originpro",
                    "style": "originpro",
                    "object": "originpro_labtalk",
                    "axis": "originpro",
                    "export": "originpro",
                    "save": "originpro",
                    "reopen": "inspection",
                    "inspect": "inspection",
                    "qa": "evidence_qa",
                },
            },
            "data": [{"id": "m1", "kind": "matrix", "source": "m1.csv"}],
            "page": {"size_mm": [150, 110], "expected_graph_pages": 1, "panel_layout": {"rows": 2, "columns": 2}},
            "layers": [{"id": "panel_a", "position_abs_mm": [10, 10, 50, 40], "x": {"limits": [0, 1]}, "y": {"limits": [0, 1]}}],
            "plots": [{"id": "c1", "layer": "panel_a", "data_ref": "m1", "type": "contour", "colormap": {"mode": "discrete"}}],
            "annotations": [{"id": "label_a", "kind": "text", "text": "(a)"}],
            "required_objects": [{"role": "panel_label", "expected_count": 3, "critical": True}],
            "rois": [{"id": "panel_a", "bbox": [0, 0, 1, 1]}],
            "benchmark": {"path": "benchmark.json"},
            "contracts": {"primary_graph": "Fig12", "expected": {"graph_pages": 1, "layers": 1, "plots": 1, "workbooks": 0}},
        }
        result = compiler.compile_v5(spec)
        self.assertEqual(result["status"], "ok", result.get("validation"))
        operation_ids = result["compiled_ir"]["operation_ids"]
        self.assertIn("plot.add.contour", operation_ids)
        self.assertIn("contour.fill.configure", operation_ids)
        self.assertIn("colorbar.create", operation_ids)
        self.assertIn("object.text.create", operation_ids)
        self.assertIn("qa.semantic_benchmark", operation_ids)


if __name__ == "__main__":
    unittest.main()
