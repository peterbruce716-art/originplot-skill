import unittest
from pathlib import Path

from builders.aa2195.source_geometry import (
    SCHEMA,
    source_geometry_contract,
    validate_source_geometry_groups,
)


def _readback(second_worksheet: str = "Sheet1", include_object: bool = True):
    objects = [{"name": "region_fill"}] if include_object else []
    return {
        "layers": [{
            "index": 0,
            "plot_details": [
                {
                    "index": 0,
                    "plot_type_code": 200,
                    "data_workbook": "Book1",
                    "data_worksheet": "Sheet1",
                    "x_column": "A",
                    "y_column": "B",
                },
                {
                    "index": 1,
                    "plot_type_code": 200,
                    "data_workbook": "Book1",
                    "data_worksheet": second_worksheet,
                    "x_column": "C",
                    "y_column": "D",
                },
            ],
            "graph_object_readback": {"objects": objects, "enumerated_objects": []},
        }]
    }


def _contract():
    return source_geometry_contract([{
        "group_id": "series.one",
        "canonical_source": {"source_id": "anchors.one", "kind": "curve_anchors"},
        "continuity": "nan_separated_xy",
        "same_worksheet": True,
        "consumers": [
            {
                "consumer_id": "curve",
                "kind": "plot",
                "view": "canonical",
                "layer_index": 0,
                "plot_index": 0,
                "x_column": "A",
                "y_column": "B",
            },
            {
                "consumer_id": "markers",
                "kind": "plot",
                "view": "derived",
                "derivation": "identity anchor view",
                "layer_index": 0,
                "plot_index": 1,
                "x_column": "C",
                "y_column": "D",
            },
            {
                "consumer_id": "fill",
                "kind": "graphobject",
                "view": "derived",
                "derivation": "closed region from the same canonical anchors",
                "object_name": "region_fill",
            },
        ],
    }])


class SourceGeometryGroupTests(unittest.TestCase):
    def test_contract_accepts_deterministic_views_in_one_reopened_worksheet(self):
        result = validate_source_geometry_groups(_readback(), _contract())
        self.assertEqual(SCHEMA, result["schema"])
        self.assertEqual("ok", result["status"])

    def test_contract_rejects_cross_worksheet_consumer(self):
        result = validate_source_geometry_groups(_readback("OtherSheet"), _contract())
        self.assertEqual("failed", result["status"])
        self.assertIn("same reopened Worksheet", {item.get("property") for item in result["mismatches"]})

    def test_contract_rejects_untracked_derived_view_and_missing_graphobject(self):
        contract = _contract()
        contract["groups"][0]["consumers"][1].pop("derivation")
        result = validate_source_geometry_groups(_readback(include_object=False), contract)
        self.assertEqual("failed", result["status"])
        properties = {item.get("property") for item in result["mismatches"]}
        self.assertIn("derivation", properties)
        self.assertIn("graphobject exists", properties)

    def test_all_five_builders_declare_source_geometry_groups(self):
        root = Path(__file__).resolve().parents[1]
        for figure in ("fig3", "fig12", "fig14", "fig15", "fig16"):
            text = (root / "builders" / "aa2195" / f"{figure}_builder.py").read_text(encoding="utf-8")
            self.assertIn('"source_geometry_groups"', text, figure)

    def test_fig12_local_fills_name_their_canonical_source_and_fig16_legend_uses_plots(self):
        root = Path(__file__).resolve().parents[1]
        fig12 = (root / "builders" / "aa2195" / "fig12_builder.py").read_text(encoding="utf-8")
        fig16 = (root / "builders" / "aa2195" / "fig16_builder.py").read_text(encoding="utf-8")
        self.assertIn("same classified palette field used to sample the XYZ matrix", fig12)
        self.assertIn("plot_derived_legend_reference", fig16)
        self.assertNotIn("same swatch bbox used by the isolated fill layer", fig16)


if __name__ == "__main__":
    unittest.main()
