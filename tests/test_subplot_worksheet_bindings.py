import unittest
from pathlib import Path

from builders.aa2195.readback import (
    validate_plot_derived_legends,
    validate_subplot_worksheet_bindings,
)


def _readback(workbook: str = "Book2", include_second_layer: bool = True):
    layers = [{
        "index": 0,
        "plot_details": [{
            "index": 0,
            "plot_type_code": 200,
            "data_workbook": workbook,
            "data_worksheet": "Sheet1",
            "x_column": "A",
            "y_column": "B",
        }],
    }]
    if include_second_layer:
        layers.append({
            "index": 1,
            "plot_details": [{
                "index": 0,
                "plot_type_code": 243,
                "data_workbook": "Book3",
                "data_worksheet": "Sheet1",
                "x_column": "A",
                "y_column": "B",
                "z_column": "C",
            }],
        })
    return {"layers": layers}


def _contracts():
    return [
        {
            "subplot_id": "panel_a",
            "layer_index": 0,
            "expected_plot_count": 1,
            "worksheet_books": ["Panel_A_Data"],
            "worksheet_names": ["Sheet1"],
        },
        {
            "subplot_id": "panel_b",
            "layer_index": 1,
            "expected_plot_count": 1,
            "worksheet_books": ["Panel_B_Data"],
            "worksheet_names": ["Sheet1"],
        },
    ]


ALIASES = {
    "Panel_A_Data": ["Book2", "Panel_A_Data"],
    "Panel_B_Data": ["Book3", "Panel_B_Data"],
}


class SubplotWorksheetBindingTests(unittest.TestCase):
    def test_accepts_each_editable_subplot_bound_to_its_declared_worksheet(self):
        result = validate_subplot_worksheet_bindings(_readback(), _contracts(), ALIASES)
        self.assertEqual("originplot.subplot_worksheet_bindings.v1", result["schema"])
        self.assertEqual("ok", result["status"])
        self.assertEqual(2, result["subplot_count"])
        self.assertEqual(["Panel_A_Data"], result["subplots"][0]["resolved_worksheet_books"])

    def test_rejects_subplot_bound_to_another_panels_workbook(self):
        result = validate_subplot_worksheet_bindings(_readback("Book3"), _contracts(), ALIASES)
        self.assertEqual("failed", result["status"])
        self.assertIn("corresponding worksheet book", {item["property"] for item in result["mismatches"]})

    def test_rejects_missing_editable_subplot_layer(self):
        result = validate_subplot_worksheet_bindings(_readback(include_second_layer=False), _contracts(), ALIASES)
        self.assertEqual("failed", result["status"])
        self.assertIn("editable graph layer exists", {item["property"] for item in result["mismatches"]})

    def test_all_five_builders_declare_subplot_worksheet_contracts(self):
        root = Path(__file__).resolve().parents[1]
        for figure in ("fig3", "fig12", "fig14", "fig15", "fig16"):
            text = (root / "builders" / "aa2195" / f"{figure}_builder.py").read_text(encoding="utf-8")
            self.assertIn('"subplot_worksheet_contracts"', text, figure)

    def test_accepts_legend_references_to_existing_plots(self):
        readback = {
            "layers": [{
                "index": 0,
                "plot_details": [{"index": 0}, {"index": 1}],
                "graph_object_readback": {
                    "objects": [{"name": "legend_psc", "text": r"\l(1)\l(2) PSC"}],
                    "enumerated_objects": [],
                },
            }]
        }
        contracts = [{
            "object_name": "legend_psc",
            "layer_index": 0,
            "plot_numbers": [1, 2],
            "text_contains": "PSC",
        }]
        self.assertEqual("ok", validate_plot_derived_legends(readback, contracts)["status"])

    def test_requires_referenced_plots_to_keep_the_declared_line_style(self):
        readback = {
            "layers": [{
                "index": 0,
                "plot_details": [
                    {"index": 0, "line_style": 2},
                    {"index": 1, "line_style": 2},
                ],
                "graph_object_readback": {
                    "objects": [{"name": "legend_uc", "text": r"\l(1)\l(2) UC"}],
                    "enumerated_objects": [],
                },
            }]
        }
        contracts = [{
            "object_name": "legend_uc",
            "layer_index": 0,
            "plot_numbers": [1, 2],
            "expected_plot_line_style": 2,
            "text_contains": "UC",
        }]
        result = validate_plot_derived_legends(readback, contracts)
        self.assertEqual("ok", result["status"])
        self.assertEqual([2, 2], result["legends"][0]["actual_plot_line_styles"])

        readback["layers"][0]["plot_details"][1]["line_style"] = 0
        result = validate_plot_derived_legends(readback, contracts)
        self.assertEqual("failed", result["status"])
        self.assertIn("referenced plot line styles", {item["property"] for item in result["mismatches"]})

    def test_rejects_legend_only_or_missing_plot_references(self):
        readback = {
            "layers": [{
                "index": 0,
                "plot_details": [{"index": 0}],
                "graph_object_readback": {
                    "objects": [{"name": "legend_psc", "text": "PSC"}],
                    "enumerated_objects": [],
                },
            }]
        }
        contracts = [{
            "object_name": "legend_psc",
            "layer_index": 0,
            "plot_numbers": [1],
            "text_contains": "PSC",
        }]
        result = validate_plot_derived_legends(readback, contracts)
        self.assertEqual("failed", result["status"])
        self.assertIn("plot references", {item["property"] for item in result["mismatches"]})

    def test_fig3_and_fig16_do_not_create_legend_only_worksheets_or_plots(self):
        root = Path(__file__).resolve().parents[1]
        fig3 = (root / "builders" / "aa2195" / "fig3_builder.py").read_text(encoding="utf-8")
        fig16 = (root / "builders" / "aa2195" / "fig16_builder.py").read_text(encoding="utf-8")
        self.assertNotIn("editable_legend_segments", fig3)
        self.assertNotIn("legend_sheet", fig3)
        self.assertNotIn("legend_layer.add_plot", fig16)
        self.assertNotIn("legend_{record['label']}_fill", fig16)
        self.assertIn("plot_derived_legend_reference", fig16)


if __name__ == "__main__":
    unittest.main()
