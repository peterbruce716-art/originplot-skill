from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Versions:
    release_version: str
    contract_version: str
    evidence_version: str

    def as_dict(self) -> dict[str, str]:
        return {
            "release_version": self.release_version,
            "contract_version": self.contract_version,
            "evidence_version": self.evidence_version,
        }


def load_versions(skill_root: Path | None = None) -> Versions:
    root = (skill_root or Path(__file__).resolve().parents[1]).resolve()
    path = root / "version.json"
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    # v6 packages carry the product version separately from the retained
    # AA2195 benchmark evidence identity. Normalize both schemas here so the
    # legacy benchmark worker can run against the current package.
    if {"version", "schema_version", "benchmark_evidence"}.issubset(payload):
        benchmark = payload.get("benchmark_evidence", {})
        evidence = str(benchmark.get("aa2195", payload["schema_version"]))
        payload = {
            "release_version": str(payload["version"]),
            "contract_version": evidence,
            "evidence_version": evidence,
        }
    required = {"release_version", "contract_version", "evidence_version"}
    if set(payload) != required:
        raise ValueError(f"version.json must contain exactly {sorted(required)}")
    if not all(
        isinstance(payload[key], str) and payload[key].strip() for key in required
    ):
        raise ValueError("version values must be nonempty strings")
    versions = Versions(**payload)
    release = versions.release_version
    if not (
        release == versions.contract_version
        or release.startswith(versions.contract_version + ".")
        or re.fullmatch(r"\d+\.\d+\.\d+", release) is not None
    ):
        raise ValueError(
            "release_version must be a contract revision or semantic package version"
        )
    if versions.evidence_version != versions.contract_version:
        raise ValueError(
            "evidence_version must retain the current functional contract identity"
        )
    return versions
