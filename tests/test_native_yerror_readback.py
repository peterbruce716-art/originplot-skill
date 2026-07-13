from __future__ import annotations

import unittest

from builders.aa2195.readback import validate_native_yerror_pairs


class NativeYErrorReadbackTests(unittest.TestCase):
    def test_accepts_origin_2022_column_error_pair(self) -> None:
        readback = {
            "layers": [
                {
                    "index": 0,
                    "plot_count": 2,
                    "plot_details": [
                        {
                            "plot_type_code": 203,
                            "data_workbook": "Book1",
                            "data_worksheet": "Sheet1",
                            "x_column": "A",
                            "y_column": "B",
                            "y_dataset": "Book1_B",
                        },
                        {
                            "plot_type_code": 231,
                            "data_workbook": "Book1",
                            "data_worksheet": "Sheet1",
                            "x_column": "B",
                            "y_column": "C",
                            "x_dataset": "Book1_B",
                        },
                    ],
                }
            ]
        }
        contract = [
            {
                "layer_index": 0,
                "expected_plot_count": 2,
                "pairs": [
                    {
                        "column_plot_index": 0,
                        "error_plot_index": 1,
                        "column_x": "A",
                        "column_y": "B",
                        "error_value_column": "C",
                    }
                ],
            }
        ]
        result = validate_native_yerror_pairs(readback, contract)
        self.assertEqual("ok", result["status"])
        self.assertEqual(1, result["pair_count"])

    def test_rejects_unlinked_error_plot(self) -> None:
        readback = {
            "layers": [
                {
                    "index": 0,
                    "plot_count": 2,
                    "plot_details": [
                        {
                            "plot_type_code": 203,
                            "data_workbook": "Book1",
                            "data_worksheet": "Sheet1",
                            "x_column": "A",
                            "y_column": "B",
                            "y_dataset": "Book1_B",
                        },
                        {
                            "plot_type_code": 200,
                            "data_workbook": "Book1",
                            "data_worksheet": "Sheet1",
                            "x_column": "A",
                            "y_column": "C",
                            "x_dataset": "Book1_A",
                        },
                    ],
                }
            ]
        }
        contract = [
            {
                "layer_index": 0,
                "pairs": [
                    {
                        "column_plot_index": 0,
                        "error_plot_index": 1,
                        "column_x": "A",
                        "column_y": "B",
                        "error_value_column": "C",
                    }
                ],
            }
        ]
        result = validate_native_yerror_pairs(readback, contract)
        self.assertEqual("failed", result["status"])
        self.assertTrue(result["mismatches"])

    def test_accepts_declared_grouped_column_implicit_error_plot(self) -> None:
        readback = {
            "layers": [
                {
                    "index": 0,
                    "plot_count": 2,
                    "plot_details": [
                        {
                            "plot_type_code": 203,
                            "data_workbook": "Book1",
                            "data_worksheet": "Sheet1",
                            "x_column": "A",
                            "y_column": "B",
                            "y_dataset": "Book1_B",
                        },
                        {
                            "plot_type_code": 231,
                            "data_workbook": "Book1",
                            "data_worksheet": "Sheet1",
                            "x_column": "C",
                            "y_column": "C",
                            "x_dataset": "Book1_C",
                            "y_dataset": "Book1_C",
                        },
                    ],
                }
            ]
        }
        contract = [
            {
                "layer_index": 0,
                "expected_plot_count": 2,
                "pairs": [
                    {
                        "column_plot_index": 0,
                        "error_plot_index": 1,
                        "column_x": "A",
                        "column_y": "B",
                        "error_value_column": "C",
                        "binding_mode": "implicit_error_column",
                    }
                ],
            }
        ]
        result = validate_native_yerror_pairs(readback, contract)
        self.assertEqual("ok", result["status"])
        self.assertEqual("implicit_error_column", result["pairs"][0]["binding_mode"])


if __name__ == "__main__":
    unittest.main()
