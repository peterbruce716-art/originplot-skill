from __future__ import annotations

from runtime.artifact_manifest import same_run_failures
from scripts.validate_benchmark_evidence_package import artifact_run_identity_failure


def _record(**extra: object) -> dict[str, object]:
    return {"path": "result.opju", "exists": True, "sha256": "abc", **extra}


def test_same_run_artifact_requires_run_id() -> None:
    failures = same_run_failures(
        {"run_id": "run-1", "project": _record(eligible_for_pass=True)}
    )
    assert failures == [
        {
            "code": "ARTIFACT_RUN_ID_MISSING",
            "expected": "run-1",
            "path": "result.opju",
        }
    ]


def test_artifact_manifest_requires_top_level_run_id() -> None:
    failures = same_run_failures({"project": _record(run_id="run-1")})
    assert failures[0] == {"code": "ARTIFACT_MANIFEST_RUN_ID_MISSING"}


def test_same_run_artifact_rejects_mismatched_run_id() -> None:
    failures = same_run_failures(
        {"run_id": "run-1", "project": _record(run_id="run-2")}
    )
    assert failures[0]["code"] == "ARTIFACT_RUN_ID_MISMATCH"


def test_same_run_artifact_accepts_matching_run_id() -> None:
    assert (
        same_run_failures({"run_id": "run-1", "project": _record(run_id="run-1")}) == []
    )


def test_package_artifact_record_requires_run_id() -> None:
    assert artifact_run_identity_failure(_record(), "run-1") == {
        "code": "artifact_run_id_missing",
        "expected": "run-1",
        "path": "result.opju",
    }


def test_package_artifact_record_rejects_wrong_run_id() -> None:
    assert artifact_run_identity_failure(_record(run_id="run-2"), "run-1") == {
        "code": "artifact_run_id_mismatch",
        "expected": "run-1",
        "actual": "run-2",
        "path": "result.opju",
    }


def test_package_artifact_record_accepts_matching_run_id() -> None:
    assert artifact_run_identity_failure(_record(run_id="run-1"), "run-1") is None
