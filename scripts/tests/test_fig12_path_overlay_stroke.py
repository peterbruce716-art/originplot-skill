from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SKILL_ROOT = Path(
    os.environ.get("ORIGINPLOT_SKILL_ROOT", Path(__file__).resolve().parents[2])
).resolve()
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))


class Fig12PathOverlayStrokeTests(unittest.TestCase):
    def test_boundary_svg_uses_requested_stroke_width(self) -> None:
        from builders.aa2195.fig12_builder import _fig12_boundary_svg

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            output = Path(tmp) / "boundary.svg"
            Image.new("RGB", (805, 590), "#b1df89").save(source)

            _fig12_boundary_svg("PSC", source, output, stroke_width=0.55)

            self.assertIn('stroke-width="0.55"', output.read_text(encoding="utf-8"))

    def test_boundary_svg_uses_requested_stroke_color(self) -> None:
        from builders.aa2195.fig12_builder import _fig12_boundary_svg

        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source.png"
            output = Path(tmp) / "boundary.svg"
            Image.new("RGB", (805, 590), "#b1df89").save(source)

            _fig12_boundary_svg("PSC", source, output, stroke_color="#7C9A63")

            self.assertIn('stroke="#7C9A63"', output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
