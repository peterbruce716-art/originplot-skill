from __future__ import annotations

from typing import Any


def fresh_builder_record(figure: str, source_crop: str = "synthetic-test-source.png") -> dict[str, Any]:
    common = {
        "source_data_policy": "fresh_extract",
        "manifest_path": "synthetic-test-manifest.json",
        "source_crop": source_crop,
        "source_crop_sha256": "1" * 64,
        "source_pdf_sha256": "2" * 64,
        "bundle_data_sha256": "3" * 64,
        "data_sha256": "4" * 64,
    }
    if figure == "fig3":
        panels = []
        for index, name in enumerate(("a", "b", "c", "d")):
            modes = ("PSC", "UC") if name == "d" else ("PSC", "UC", "TR")
            series = {
                temperature: {
                    mode: {"x": [0.0, 0.45, 0.9], "y": [0.0, 80.0 + index * 5, 55.0 + index * 5]}
                    for mode in modes
                }
                for temperature in ("250", "300", "350", "400")
            }
            panels.append({
                "name": name,
                "panel": f"({name})",
                "strain_rate": ("0.01", "0.1", "1", "10")[index],
                "ymax": 225.0 if index < 2 else 200.0,
                "frame_percent": ([10.2, 2.6, 38.2, 42.7], [58.0, 2.6, 38.2, 42.7], [10.2, 53.0, 38.2, 42.7], [58.0, 53.0, 38.2, 42.7])[index],
                "series": series,
            })
        data = {"method": "synthetic_fresh_test_data", "panels": panels}
    elif figure == "fig12":
        data = {"method": "synthetic_fresh_test_palette_source"}
    elif figure == "fig14":
        data = {
            "method": "synthetic_fresh_test_data",
            "temperature": [250.0, 300.0, 350.0, 400.0],
            "series": {
                "PSC": {"y": [0.04, 0.08, 0.13, 0.19], "err": [0.01] * 4, "color": "#ef4b4b", "symbol": 1},
                "UC": {"y": [0.06, 0.10, 0.16, 0.24], "err": [0.01] * 4, "color": "#2675d8", "symbol": 2},
                "TR": {"y": [0.09, 0.15, 0.19, 0.27], "err": [0.01] * 4, "color": "#35a66b", "symbol": 3},
            },
        }
    elif figure == "fig15":
        curve = {"x": [0.02, 0.2, 0.5, 0.9], "y": [0.03, 0.75, 0.70, 0.70], "method": "synthetic_fresh_test_curve"}
        data = {"method": "synthetic_fresh_test_data", "panels": {"PSC": {"curve": curve}, "UC_TR": {"curve": curve}}}
    elif figure == "fig16":
        data = {
            "method": "synthetic_fresh_test_data",
            "colors": {"WH": "#ff9933", "DRV": "#00ff99", "DRX": "#cc99ff"},
            "bars": {
                "WH": [[24, 148, 62, 334], [117, 134, 154, 334], [209, 93, 247, 335], [320, 134, 358, 335], [411, 93, 449, 334], [518, 134, 556, 335], [609, 93, 647, 335]],
                "DRV": [[65, 202, 103, 335], [157, 175, 195, 335], [249, 161, 287, 335], [361, 229, 399, 335], [452, 202, 491, 335], [559, 242, 596, 335], [650, 215, 688, 335]],
                "DRX": [[65, 188, 103, 199], [157, 120, 195, 172], [249, 93, 287, 158], [361, 161, 399, 226], [452, 93, 491, 199], [559, 161, 597, 239], [650, 93, 688, 213]],
            },
        }
    else:
        raise ValueError(figure)
    return {**common, "data": data}
