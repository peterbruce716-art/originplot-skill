from __future__ import annotations

import unittest
from pathlib import Path


RUNNER = Path(__file__).resolve().parents[1] / "run_five_figure_live_batch.ps1"


class BatchPathResolutionTests(unittest.TestCase):
    def test_output_root_is_canonicalized_before_worker_start(self) -> None:
        source = RUNNER.read_text(encoding="utf-8-sig")
        self.assertIn(
            "$OutputRoot = [IO.Path]::GetFullPath($OutputRoot)",
            source,
            "relative output roots break workers whose working directory is SkillRoot",
        )


if __name__ == "__main__":
    unittest.main()
