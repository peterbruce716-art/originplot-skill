from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .errors import ProfileConfigurationError


PROFILE_NAMES = ("quick", "standard", "release")
TEMPLATE_POLICIES = ("skip", "auto", "strict")
EVIDENCE_LEVELS = ("basic", "visual", "full")
REOPEN_CHECKS = ("basic", "strict")
VISUAL_QA_LEVELS = ("off", "basic", "benchmark")
SOURCE_POLICIES = (
    "supplied",
    "fresh_extract",
    "validated_reuse",
    "validated_crop_reextract",
)


@dataclass(frozen=True)
class ProfileConfig:
    name: str
    template_policy: str
    evidence_level: str
    reopen_check: str
    visual_qa: str
    max_template_candidates: int
    max_rebuild_attempts: int
    require_admin_controller: bool
    require_admin_origin_worker: bool
    require_fresh_output_root: bool
    require_release_eligibility: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_DEFAULTS = {
    "quick": ProfileConfig(
        name="quick",
        template_policy="skip",
        evidence_level="basic",
        reopen_check="basic",
        visual_qa="off",
        max_template_candidates=0,
        max_rebuild_attempts=0,
        require_admin_controller=False,
        require_admin_origin_worker=True,
        require_fresh_output_root=False,
        require_release_eligibility=False,
    ),
    "standard": ProfileConfig(
        name="standard",
        template_policy="auto",
        evidence_level="visual",
        reopen_check="basic",
        visual_qa="basic",
        max_template_candidates=3,
        max_rebuild_attempts=1,
        require_admin_controller=False,
        require_admin_origin_worker=True,
        require_fresh_output_root=False,
        require_release_eligibility=False,
    ),
    "release": ProfileConfig(
        name="release",
        template_policy="strict",
        evidence_level="full",
        reopen_check="strict",
        visual_qa="benchmark",
        max_template_candidates=0,
        max_rebuild_attempts=0,
        require_admin_controller=True,
        require_admin_origin_worker=True,
        require_fresh_output_root=True,
        require_release_eligibility=True,
    ),
}


def _choice(name: str, value: str, allowed: tuple[str, ...]) -> str:
    if value not in allowed:
        raise ProfileConfigurationError(
            "E201_PROFILE_CONFIGURATION_INVALID",
            f"{name} must be one of {', '.join(allowed)}; got {value!r}",
        )
    return value


def resolve_profile(
    profile: str = "standard",
    *,
    template_policy: str | None = None,
    evidence_level: str | None = None,
    reopen_check: str | None = None,
    visual_qa: str | None = None,
    max_template_candidates: int | None = None,
    max_rebuild_attempts: int | None = None,
) -> ProfileConfig:
    """Resolve defaults and reject overrides that weaken release semantics."""
    profile = _choice("profile", profile, PROFILE_NAMES)
    base = _DEFAULTS[profile]
    values = base.to_dict()
    values["template_policy"] = _choice(
        "template_policy", template_policy or base.template_policy, TEMPLATE_POLICIES
    )
    values["evidence_level"] = _choice(
        "evidence_level", evidence_level or base.evidence_level, EVIDENCE_LEVELS
    )
    values["reopen_check"] = _choice(
        "reopen_check", reopen_check or base.reopen_check, REOPEN_CHECKS
    )
    values["visual_qa"] = _choice(
        "visual_qa", visual_qa or base.visual_qa, VISUAL_QA_LEVELS
    )
    if max_template_candidates is not None:
        if max_template_candidates < 0:
            raise ProfileConfigurationError(
                "E201_PROFILE_CONFIGURATION_INVALID",
                "max_template_candidates must be non-negative",
            )
        values["max_template_candidates"] = max_template_candidates
    if max_rebuild_attempts is not None:
        if max_rebuild_attempts < 0:
            raise ProfileConfigurationError(
                "E201_PROFILE_CONFIGURATION_INVALID",
                "max_rebuild_attempts must be non-negative",
            )
        values["max_rebuild_attempts"] = max_rebuild_attempts

    if profile == "release":
        required = {
            "template_policy": "strict",
            "evidence_level": "full",
            "reopen_check": "strict",
            "visual_qa": "benchmark",
        }
        weakened = [key for key, expected in required.items() if values[key] != expected]
        if weakened:
            raise ProfileConfigurationError(
                "E202_RELEASE_PROFILE_WEAKENED",
                "release requires strict/full/strict/benchmark; invalid overrides: "
                + ", ".join(weakened),
            )
    if profile == "quick" and values["template_policy"] == "strict":
        raise ProfileConfigurationError(
            "E203_QUICK_STRICT_TEMPLATE_CONFLICT",
            "quick cannot request strict template discovery; use release",
        )
    return ProfileConfig(**values)
