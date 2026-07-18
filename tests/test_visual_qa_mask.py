from __future__ import annotations

import importlib.util
import sys
import unittest
import warnings
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def load_visual_qa():
    path = ROOT / "scripts" / "visual_qa.py"
    spec = importlib.util.spec_from_file_location("originplot_visual_qa_mask_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class VisualQaMaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.visual_qa = load_visual_qa()

    def test_mask_image_is_exact_eight_bit_luminance(self) -> None:
        mask = np.array([[False, True], [True, False]], dtype=bool)
        self.assertTrue(hasattr(self.visual_qa, "_mask_image"))

        image = self.visual_qa._mask_image(mask)

        self.assertEqual("L", image.mode)
        self.assertEqual((2, 2), image.size)
        np.testing.assert_array_equal(
            np.array([[0, 255], [255, 0]], dtype=np.uint8),
            np.asarray(image),
        )

    def test_dilate_emits_no_pillow_deprecation_and_preserves_pixels(self) -> None:
        mask = np.zeros((5, 5), dtype=bool)
        mask[2, 2] = True
        expected = np.zeros((5, 5), dtype=bool)
        expected[1:4, 1:4] = True

        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            actual = self.visual_qa._dilate(mask, 1)

        self.assertEqual(np.dtype(bool), actual.dtype)
        self.assertEqual(mask.shape, actual.shape)
        np.testing.assert_array_equal(expected, actual)


if __name__ == "__main__":
    unittest.main()
