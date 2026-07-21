from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from originplot.core.errors import OriginPlotError


Search = Callable[[int], Iterable[dict[str, Any]]]


@dataclass(frozen=True)
class TemplateDecision:
    policy: str
    status: str
    selected: dict[str, Any] | None
    candidates: tuple[dict[str, Any], ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy": self.policy,
            "status": self.status,
            "selected": self.selected,
            "candidates": list(self.candidates),
            "warnings": list(self.warnings),
        }


def apply_template_policy(
    policy: str,
    *,
    max_candidates: int,
    local_search: Search | None = None,
    gallery_search: Search | None = None,
    strict_record: dict[str, Any] | None = None,
) -> TemplateDecision:
    if policy == "skip":
        return TemplateDecision("skip", "not_required", None, (), ())
    if policy == "strict":
        if not strict_record or strict_record.get("status") != "ok":
            raise OriginPlotError(
                "E130_TEMPLATE_SEARCH_REQUIRED",
                "release requires a complete strict template search record",
            )
        return TemplateDecision("strict", "verified", strict_record.get("selected"), (), ())
    if policy != "auto":
        raise OriginPlotError("E204_TEMPLATE_POLICY_INVALID", f"unknown policy: {policy}")

    limit = max(0, max_candidates)
    candidates: list[dict[str, Any]] = []
    warnings: list[str] = []
    for label, search in (("local", local_search), ("gallery", gallery_search)):
        if search is None or len(candidates) >= limit:
            continue
        try:
            for item in search(limit - len(candidates)):
                if isinstance(item, dict):
                    candidates.append(item)
                if len(candidates) >= limit:
                    break
        except Exception as exc:
            warnings.append(f"{label}_template_search_failed: {exc}")
    selected = next((item for item in candidates if item.get("reusable") is True), None)
    return TemplateDecision(
        "auto",
        "selected" if selected else "native_fallback",
        selected,
        tuple(candidates),
        tuple(warnings),
    )
