from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import BuilderDefinition


class DuplicateBuilderError(ValueError):
    pass


class UnknownBuilderError(KeyError):
    pass


_BUILDERS: dict[str, BuilderDefinition] = {}


def register_builder(builder_id: str, builder: BuilderDefinition) -> None:
    if not builder_id or builder_id != builder.builder_id:
        raise ValueError("registry key must equal the nonempty BuilderDefinition.builder_id")
    if builder_id in _BUILDERS:
        raise DuplicateBuilderError(f"builder already registered: {builder_id}")
    _BUILDERS[builder_id] = builder


def get_builder(builder_id: str) -> BuilderDefinition:
    try:
        return _BUILDERS[builder_id]
    except KeyError as exc:
        raise UnknownBuilderError(f"unknown builder: {builder_id}") from exc


def list_builders() -> tuple[str, ...]:
    return tuple(sorted(_BUILDERS))


def resolve_builder(
    *,
    builder_id: str | None = None,
    figure: str | None = None,
) -> BuilderDefinition:
    requested = builder_id or figure
    if not requested:
        raise UnknownBuilderError("a builder or legacy figure id is required")
    definition = get_builder(requested)
    if figure and definition.figure_ids and figure not in definition.figure_ids:
        raise ValueError(
            f"figure {figure!r} is not accepted by builder {definition.builder_id!r}"
        )
    return definition


def _aa2195_live(figure: str, candidate: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    from builders import aa2195

    return aa2195.build_origin_figure(
        figure_id=figure,
        candidate_params=candidate,
        output_dir=output_dir,
        attach_existing_authorized=True,
    )


def _register_builtins() -> None:
    for figure in ("fig12", "fig15", "fig16"):
        register_builder(
            figure,
            BuilderDefinition(
                builder_id=figure,
                description=f"AA2195 specialized {figure} Origin builder",
                figure_ids=(figure,),
                supports_live=True,
                live_builder=_aa2195_live,
            ),
        )

    from .generic.line_builder import validate_plan

    register_builder(
        "generic_line",
        BuilderDefinition(
            builder_id="generic_line",
            description="Synthetic/public single-panel line planning example",
            supports_live=False,
            plan_validator=validate_plan,
        ),
    )


_register_builtins()
