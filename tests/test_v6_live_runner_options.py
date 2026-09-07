from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_five_figure_live_batch.ps1"
PWSH = shutil.which("pwsh")
pytestmark = pytest.mark.skipif(PWSH is None, reason="PowerShell Core required")


def run_powershell(body: str) -> subprocess.CompletedProcess[str]:
    escaped = str(RUNNER).replace("'", "''")
    prefix = (
        "$ErrorActionPreference = 'Stop'\n"
        "$tokens = $null\n$errors = $null\n"
        "$ast = [System.Management.Automation.Language.Parser]::ParseFile("
        f"'{escaped}', [ref]$tokens, [ref]$errors)\n"
        "if ($errors.Count) { throw 'Runner has parse errors' }\n"
    )
    return subprocess.run(
        [PWSH, "-NoProfile", "-NonInteractive", "-Command", prefix + body],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=30,
    )


def factor_command(expression: str) -> str:
    return (
        "$function = $ast.Find({param($node) "
        "$node -is [System.Management.Automation.Language.FunctionDefinitionAst] "
        "-and $node.Name -eq 'Resolve-FigureExportFactors'}, $true)\n"
        "if (-not $function) { throw 'Missing factor validator' }\n"
        "Invoke-Expression $function.Extent.Text\n"
        f"Resolve-FigureExportFactors -Requested {expression} | ConvertTo-Json -Compress\n"
    )


@pytest.mark.parametrize("expression", ["@{}", "@{fig3=3}", "@{fig3=1;fig14=4}"])
def test_per_figure_export_map_preserves_only_explicit_keys(expression: str) -> None:
    result = run_powershell(factor_command(expression))
    assert result.returncode == 0, result.stderr
    expected = {
        "@{}": {},
        "@{fig3=3}": {"fig3": 3},
        "@{fig3=1;fig14=4}": {"fig3": 1, "fig14": 4},
    }
    assert json.loads(result.stdout) == expected[expression]


@pytest.mark.parametrize(
    "expression",
    [
        "@{fig4=3}",
        "@{fig3=$true}",
        "@{fig3=1.5}",
        "@{fig3=0}",
        "@{fig3=5}",
        "@{fig3='3'}",
        "@{Keys=@()}",
        "@{Keys='fig3';fig3=3;fig99=4}",
    ],
)
def test_invalid_export_map_is_rejected(expression: str) -> None:
    result = run_powershell(factor_command(expression))
    assert result.returncode != 0
    assert "E134_EXPORT_SUPERSAMPLE_INVALID" in result.stderr


def test_restoration_does_not_erase_a_hidden_window_observation() -> None:
    result = run_powershell(
        "$loop = $ast.Find({param($node) "
        "$node -is [System.Management.Automation.Language.WhileStatementAst] "
        "-and $node.Extent.Text.StartsWith('while (-not $process.HasExited)')}, $true)\n"
        "if (-not $loop) { throw 'Missing worker visibility loop' }\n"
        "function Get-OriginWindowState { param($ProcessId) "
        "[pscustomobject]@{restored=$false;is_visible=$false;is_iconic=$true;main_window_handle=12} }\n"
        "function Show-OriginWindow { param($ProcessId) "
        "[pscustomobject]@{restored=$true;is_visible=$true;is_iconic=$false;main_window_handle=12} }\n"
        "function Start-Sleep { param($Milliseconds) }\n"
        "$process = [pscustomobject]@{HasExited=$false}\n"
        "$process | Add-Member -MemberType ScriptMethod -Name Refresh -Value {$this.HasExited=$true}\n"
        "$originPid = 123\n$windowSamples = @()\n$windowRestorationCount = 0\n"
        "Invoke-Expression $loop.Extent.Text\n"
        "[pscustomobject]@{samples=@($windowSamples);restorations=$windowRestorationCount} | ConvertTo-Json -Depth 5\n"
    )
    assert result.returncode == 0, result.stderr
    record = json.loads(result.stdout)
    assert record["restorations"] == 1
    assert len(record["samples"]) == 2
    assert record["samples"][0]["is_visible"] is False
    assert record["samples"][1]["is_visible"] is True


@pytest.mark.parametrize(
    "options,code",
    [
        ("-ExportSupersampleByFigure @{fig4=3}", "E134_EXPORT_SUPERSAMPLE_INVALID"),
        (
            "-Fig3CanvasMode full -SourceDataPolicy validated_reuse",
            "E127_FRESH_SOURCE_REQUIRED",
        ),
    ],
)
def test_invalid_options_fail_before_output_creation(
    tmp_path, options: str, code: str
) -> None:
    output = tmp_path / "must-not-be-created"
    escaped_output = str(output).replace("'", "''")
    escaped_runner = str(RUNNER).replace("'", "''")
    result = run_powershell(
        f"& '{escaped_runner}' -OutputRoot '{escaped_output}' {options}\n"
    )
    assert result.returncode != 0
    assert code in result.stderr
    assert not output.exists()
