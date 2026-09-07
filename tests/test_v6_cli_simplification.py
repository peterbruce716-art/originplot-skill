from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from originplot.core.errors import OriginPlotError
from originplot.core.profiles import PROFILE_NAMES

cli = importlib.import_module("originplot.cli.main")


@pytest.mark.parametrize("command", ["plan", "draw"])
def test_planning_parser_defaults_and_help_order(command):
    parser = cli.build_parser()
    args = parser.parse_args([command, "source.txt"])
    assert args.data == Path("source.txt")
    assert args.sheet is None
    assert args.plot_type is None
    assert args.profile == "standard"
    assert args.reference_style_json is None
    assert args.style_json is None
    subcommands = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    ).choices
    assert list(subcommands) == [
        "doctor",
        "inspect",
        "plan",
        "render",
        "draw",
        "verify",
    ]
    actions = subcommands[command]._actions
    middle = ["output"] if command == "plan" else ["output_dir", "dry_run"]
    assert [action.dest for action in actions] == [
        "help",
        "data",
        "sheet",
        "plot_type",
        "profile",
        *middle,
        "x",
        "y",
        "x_error",
        "y_error",
        "category",
        "z",
        "reference_style_json",
        "style_json",
    ]
    assert (
        next(action for action in actions if action.dest == "profile").choices
        == PROFILE_NAMES
    )
    help_text = subcommands[command].format_help()
    option_flags = [
        action.option_strings[0] for action in actions if action.option_strings
    ]
    options_text = help_text.split("options:", 1)[1]
    positions = [options_text.index(flag) for flag in option_flags]
    assert positions == sorted(positions)


@pytest.mark.parametrize("command", ["plan", "draw"])
@pytest.mark.parametrize("explicit", [False, True])
def test_planner_receives_identical_mapping_and_style_arguments(
    tmp_path, monkeypatch, capsys, command, explicit
):
    source = tmp_path / "source.txt"
    output = tmp_path / "out"
    spec_path = output / "figure_spec.json"
    figure_spec = {"figure": {"type": "scatter"}}
    calls = []
    events = []
    argv = [command, str(source)]
    argv += (
        ["--output", str(spec_path)]
        if command == "plan"
        else ["--output-dir", str(output)]
    )
    expected = {
        "plot_type": None,
        "sheet": None,
        "mapping": {},
        "profile": "standard",
        "reference_style": None,
        "user_style": None,
    }
    if explicit:
        reference = tmp_path / "reference.json"
        user = tmp_path / "user.json"
        reference.write_text(
            '\ufeff{"series": {"s1": {"color": "blue"}}}', encoding="utf-8"
        )
        user.write_text('{"series": {"s1": {"color": "red"}}}', encoding="utf-8")
        argv += [
            "--plot-type",
            "scatter",
            "--sheet",
            "Sheet2",
            "--profile",
            "quick",
            "--x",
            "Time",
            "--y",
            "Signal",
            "--x-error",
            "DX",
            "--y-error",
            "DY",
            "--category",
            "Category",
            "--z",
            "Height",
            "--reference-style-json",
            str(reference),
            "--style-json",
            str(user),
        ]
        expected.update(
            plot_type="scatter",
            sheet="Sheet2",
            profile="quick",
            mapping={
                "x": "Time",
                "y": "Signal",
                "x_error": "DX",
                "y_error": "DY",
                "category": "Category",
                "z": "Height",
            },
            reference_style={"series": {"s1": {"color": "blue"}}},
            user_style={"series": {"s1": {"color": "red"}}},
        )
    else:
        argv += ["--x", ""]

    def planner(data, **kwargs):
        assert output.exists() is (command == "draw")
        assert not spec_path.exists()
        calls.append((data, kwargs))
        events.append("plan")
        return figure_spec

    def execute(**kwargs):
        assert json.loads(spec_path.read_text(encoding="utf-8")) == figure_spec
        assert kwargs["figure_spec_path"] == spec_path
        assert kwargs["output_dir"] == output
        events.append("execute")
        return {"command_success": True}

    monkeypatch.setattr(cli, "build_figurespec", planner)
    monkeypatch.setattr(cli, "execute", execute)
    assert cli.main(argv) == 0
    assert calls == [(source, expected)]
    assert events == (["plan"] if command == "plan" else ["plan", "execute"])
    assert json.loads(spec_path.read_text(encoding="utf-8")) == figure_spec
    result = json.loads(capsys.readouterr().out)
    assert result == (
        {"status": "planned", "figure_spec": str(spec_path), "plot_type": "scatter"}
        if command == "plan"
        else {"command_success": True}
    )


@pytest.mark.parametrize(
    "command,require_live", [("render", False), ("render", True), ("draw", False)]
)
@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("explicit_profile", [None, "standard"])
@pytest.mark.parametrize("explicit_output", [False, True])
def test_execution_options_keep_command_specific_semantics(
    tmp_path,
    monkeypatch,
    capsys,
    command,
    dry_run,
    explicit_profile,
    require_live,
    explicit_output,
):
    source = tmp_path / "input.json"
    default_draw = tmp_path / "draw_default"
    monkeypatch.setattr(cli, "_default_output", lambda data: default_draw)
    monkeypatch.setattr(
        cli,
        "load_figure_spec",
        lambda path: SimpleNamespace(profile="quick", figure_id="sample"),
    )
    monkeypatch.setattr(
        cli, "build_figurespec", lambda *args, **kwargs: {"figure": {"type": "line"}}
    )
    calls = []
    result = {"command_success": True}

    def execute(**kwargs):
        calls.append(kwargs)
        return result

    monkeypatch.setattr(cli, "execute", execute)
    argv = [command, str(source)]
    output = tmp_path / "sample_OriginPlot" if command == "render" else default_draw
    if explicit_output:
        output = tmp_path / "chosen"
        argv += ["--output-dir", str(output)]
    if dry_run:
        argv.append("--dry-run")
    if explicit_profile:
        argv += ["--profile", explicit_profile]
    if require_live:
        argv.append("--require-live-success")
    assert cli.main(argv) == 0
    assert len(calls) == 1
    call = calls[0]
    assert call["profile"].name == (
        explicit_profile or ("quick" if command == "render" else "standard")
    )
    assert call["live"] is (not dry_run)
    assert call["require_live_success"] is (
        require_live if command == "render" else not dry_run
    )
    assert call["output_dir"] == output
    assert call["figure_spec_path"] == (
        source if command == "render" else output / "figure_spec.json"
    )
    assert json.loads(capsys.readouterr().out) == result


@pytest.mark.parametrize("command", ["render", "draw"])
@pytest.mark.parametrize(
    "result,expected",
    [
        ({"command_success": True}, 0),
        ({"command_success": "truthy"}, 0),
        ({"command_success": False, "status": "planned_not_executed"}, 0),
        ({"status": "planned_not_executed"}, 0),
        ({"command_success": False, "status": "failed"}, 1),
        ({"command_success": 0}, 1),
        ({}, 1),
    ],
)
def test_execution_exit_predicate_preserves_truthiness(
    tmp_path, monkeypatch, capsys, command, result, expected
):
    monkeypatch.setattr(
        cli,
        "load_figure_spec",
        lambda path: SimpleNamespace(profile="quick", figure_id="sample"),
    )
    monkeypatch.setattr(
        cli, "build_figurespec", lambda *args, **kwargs: {"figure": {"type": "line"}}
    )
    monkeypatch.setattr(cli, "execute", lambda **kwargs: result)
    assert (
        cli.main(
            [
                command,
                str(tmp_path / "source.txt"),
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )
        == expected
    )
    assert json.loads(capsys.readouterr().out) == result


@pytest.mark.parametrize(
    "present,success,expected",
    [
        (True, True, 0),
        (False, True, 1),
        (True, False, 1),
        (False, False, 1),
        (True, "truthy", 0),
    ],
)
def test_verify_keeps_its_distinct_exit_predicate(
    tmp_path, monkeypatch, capsys, present, success, expected
):
    result = {
        "all_required_present": present,
        "command_success": success,
        "status": "planned_not_executed",
    }
    monkeypatch.setattr(cli, "_verify_output", lambda path: result)
    assert cli.main(["verify", str(tmp_path)]) == expected
    assert json.loads(capsys.readouterr().out) == result


@pytest.mark.parametrize(
    "command,failure",
    [
        ("plan", "reference"),
        ("draw", "reference"),
        ("plan", "user"),
        ("draw", "user"),
        ("plan", "planner"),
        ("draw", "planner"),
        ("plan", "write"),
        ("draw", "write"),
        ("draw", "execute"),
    ],
)
@pytest.mark.parametrize("existing", [False, True])
def test_failures_preserve_error_payload_and_file_write_order(
    tmp_path, monkeypatch, capsys, command, existing, failure
):
    output = tmp_path / "out"
    spec_path = output / "figure_spec.json"
    original = b"previous plan\n"
    if existing:
        output.mkdir()
        spec_path.write_bytes(original)
    reference = tmp_path / "reference.json"
    user = tmp_path / "user.json"
    reference.write_text("[]" if failure == "reference" else "{}", encoding="utf-8")
    user.write_text(
        "[]" if failure in {"reference", "user"} else "{}", encoding="utf-8"
    )
    events = []
    figure_spec = {"figure": {"type": "line"}}
    error = OriginPlotError("E330_TEST_PLANNER", "planner rejected")
    if failure in {"reference", "user"}:
        bad_path = reference if failure == "reference" else user
        error = OriginPlotError(
            "E340_STYLE_SPEC_INVALID", f"style JSON must contain an object: {bad_path}"
        )
    elif failure == "write":
        error = OSError("write rejected")
    elif failure == "execute":
        error = ValueError("execute rejected")

    def planner(*args, **kwargs):
        assert output.exists() is (existing or command == "draw")
        events.append("plan")
        if failure == "planner":
            raise error
        return figure_spec

    def execute(**kwargs):
        events.append("execute")
        assert json.loads(spec_path.read_text(encoding="utf-8")) == figure_spec
        raise error

    def rejected_write(path, payload):
        events.append("write")
        raise error

    monkeypatch.setattr(cli, "build_figurespec", planner)
    monkeypatch.setattr(cli, "execute", execute)
    if failure == "write":
        monkeypatch.setattr(cli, "_write", rejected_write)
    argv = [
        command,
        str(tmp_path / "source.txt"),
        "--reference-style-json",
        str(reference),
        "--style-json",
        str(user),
    ]
    argv += (
        ["--output", str(spec_path)]
        if command == "plan"
        else ["--output-dir", str(output)]
    )
    assert cli.main(argv) == 1
    assert json.loads(capsys.readouterr().out) == {
        "status": "failed",
        "error_code": getattr(error, "code", "E100_V6_COMMAND_FAILED"),
        "message": str(error),
    }
    assert output.exists() is (existing or command == "draw")
    assert (
        events
        == {
            "reference": [],
            "user": [],
            "planner": ["plan"],
            "write": ["plan", "write"],
            "execute": ["plan", "execute"],
        }[failure]
    )
    if failure == "execute":
        assert json.loads(spec_path.read_text(encoding="utf-8")) == figure_spec
    elif existing:
        assert spec_path.read_bytes() == original
    else:
        assert not spec_path.exists()
