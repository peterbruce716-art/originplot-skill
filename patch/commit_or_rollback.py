from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def score(report: dict) -> float:
    return float(report.get("score_0_1", report.get("mae_0_1", 1.0)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Commit candidate spec only if QA improves; otherwise keep accepted spec.")
    parser.add_argument("--accepted", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--accepted-qa", required=True, type=Path)
    parser.add_argument("--candidate-qa", required=True, type=Path)
    parser.add_argument("--decision-out", required=True, type=Path)
    args = parser.parse_args()
    accepted_score = score(json.loads(args.accepted_qa.read_text(encoding="utf-8-sig")))
    candidate_score = score(json.loads(args.candidate_qa.read_text(encoding="utf-8-sig")))
    if candidate_score < accepted_score:
        shutil.copyfile(args.candidate, args.accepted)
        decision = {"schema": "originplot.patch_decision.v5", "status": "committed", "accepted_score": accepted_score, "candidate_score": candidate_score}
    else:
        decision = {"schema": "originplot.patch_decision.v5", "status": "rolled_back", "accepted_score": accepted_score, "candidate_score": candidate_score, "error_code": "E510_NO_IMPROVEMENT"}
    args.decision_out.parent.mkdir(parents=True, exist_ok=True)
    args.decision_out.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0 if decision["status"] == "committed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
