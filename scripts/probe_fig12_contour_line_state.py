"""Record the Origin colormap readback boundary for the AA2195 Fig12 route.

The benchmark contract calls ``layer.cmap.showLines(3)`` a hard failure and
``showLines(0)`` the canonical type-34 overlay state, but no structural gate
checks it. This probe establishes why: it opens two saved Fig12 projects that
are known to differ by exactly three 1 px vertical contour lines and reports
which colormap properties are readable and which of those distinguish the two
states.

Result on Origin 2022 (recorded in ``docs/benchmark.md``): ``showLines`` is a
method with no readable counterpart, and every readable line property
(``lineWidth1..3``, ``lineColor1..2``, ``lineStyle1``, ``cmap.type``) is
identical whether or not the lines are drawn. Contour-line visibility is
therefore not recoverable from property readback, and pixel comparison via
``scripts/compare_five_figure_batches.py`` is the only detector.

An unresolvable LabTalk property leaves the destination variable at its previous
value, so every read here is bracketed by a sentinel. Without that guard an
unreadable property returns the previously read number and looks like evidence.

Usage::

    python scripts/probe_fig12_contour_line_state.py \
        --lines-on <batch>/fig12/candidate.opju \
        --lines-off <batch>/fig12/candidate.opju
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

PAGE = "Fig12_source_calibrated_three_panel_contour"
SENTINEL = -987654.0

CONTROL_EXPRESSIONS = (
    # These are known to resolve; if they are unreadable or differ between
    # samples, the layer context/comparison is not trustworthy.
    "layer.x.from",
    "layer.x.to",
)

CONTOUR_LINE_CANDIDATE_EXPRESSIONS = (
    "layer.cmap.showLines",
    "layer.cmap.enableLines",
    "layer.cmap.lines",
    "layer.cmap.lineVisible",
    "layer.cmap.showLine",
    "layer.cmap.numLevels",
    "layer.cmap.numColors",
    "layer.cmap.lineColor1",
    "layer.cmap.lineColor2",
    "layer.cmap.lineWidth1",
    "layer.cmap.lineWidth2",
    "layer.cmap.lineWidth3",
    "layer.cmap.lineStyle1",
    "layer.cmap.showLabels",
    "layer.cmap.type",
)

PROBED_EXPRESSIONS = CONTROL_EXPRESSIONS + CONTOUR_LINE_CANDIDATE_EXPRESSIONS


def read_expression(op: Any, layer: Any, expression: str) -> float | None:
    """Return the LabTalk value, or None when the expression does not resolve."""
    try:
        layer.lt_exec(f"__probe_value = {SENTINEL};")
        layer.lt_exec(f"__probe_value = {expression};")
        value = op.lt_float("__probe_value")
    except Exception:
        return None
    return None if value == SENTINEL else value


def probe_project(op: Any, opju: Path, layers: int = 3) -> dict[str, Any]:
    from benchmarks.aa2195.builders.common_origin_utils import find_graph

    if not op.open(str(opju), readonly=False):
        raise RuntimeError(f"failed to open Origin project: {opju}")
    page = find_graph(op, PAGE)
    if page is None:
        raise RuntimeError(f"{PAGE} not found in {opju}")
    readings: dict[str, dict[str, float | None]] = {}
    for index in range(layers):
        layer = page[index]
        readings[str(index)] = {
            expression: read_expression(op, layer, expression)
            for expression in PROBED_EXPRESSIONS
        }
    return readings


def compare(lines_on: dict[str, Any], lines_off: dict[str, Any]) -> dict[str, Any]:
    unreadable: list[str] = []
    same: list[str] = []
    distinguishing: list[dict[str, Any]] = []
    control_differences: list[dict[str, Any]] = []
    for expression in PROBED_EXPRESSIONS:
        for layer in sorted(lines_on):
            on = lines_on[layer][expression]
            off = lines_off[layer][expression]
            if on is None and off is None:
                unreadable.append(f"{expression}[{layer}]")
            elif on != off:
                finding = {
                    "expression": expression,
                    "layer": layer,
                    "lines_on": on,
                    "lines_off": off,
                }
                if expression in CONTROL_EXPRESSIONS:
                    control_differences.append(finding)
                else:
                    distinguishing.append(finding)
            else:
                same.append(f"{expression}[{layer}]")
    control_failures = [
        name for name in unreadable if name.split("[", 1)[0] in CONTROL_EXPRESSIONS
    ]
    samples_equivalent = not control_failures and not control_differences
    return {
        "schema": "originplot.fig12_contour_line_probe.v1",
        "control_expressions_unreadable": control_failures,
        "control_expressions_differing": control_differences,
        "samples_equivalent": samples_equivalent,
        "probe_trustworthy": samples_equivalent,
        "unreadable": unreadable,
        "readable_but_identical": same,
        "distinguishing": distinguishing,
        "showlines_recoverable_from_readback": bool(distinguishing),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lines-on", required=True, type=Path)
    parser.add_argument("--lines-off", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    import originpro as op

    from benchmarks.aa2195.builders.session import origin_session

    with origin_session(
        op, attach_existing_authorized=True, require_administrator=True
    ):
        on = probe_project(op, args.lines_on)
        off = probe_project(op, args.lines_off)

    report = compare(on, off)
    report["lines_on_project"] = str(args.lines_on)
    report["lines_off_project"] = str(args.lines_off)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)

    if not report["probe_trustworthy"]:
        print(
            "control expressions did not resolve; layer context is wrong and "
            "these readings prove nothing",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
