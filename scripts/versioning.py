from __future__ import annotations

import json
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
    required = {"release_version", "contract_version", "evidence_version"}
    if set(payload) != required:
        raise ValueError(f"version.json must contain exactly {sorted(required)}")
    if not all(isinstance(payload[key], str) and payload[key].strip() for key in required):
        raise ValueError("version values must be nonempty strings")
    versions = Versions(**payload)
    if not versions.release_version.startswith(versions.contract_version + "."):
        raise ValueError("release_version must be a revision of contract_version")
    if versions.evidence_version != versions.contract_version:
        raise ValueError("evidence_version must retain the current functional contract identity")
    return versions
