from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class DocumentationContractTests(unittest.TestCase):
    def test_fig3_patterned_series_keeps_editable_nan_breaks(self) -> None:
        from builders.aa2195.fig3_builder import FIG3_FONT, FIG3_FONT_ID, _legend_segment, _patterned_series

        x = [0.0, 0.5, 1.0]
        y = [0.0, 1.0, 0.5]
        plot_x, plot_y = _patterned_series(x, y, "UC")
        self.assertEqual(len(plot_x), len(plot_y))
        self.assertGreater(len(plot_x), len(x))
        self.assertTrue(any(value != value for value in plot_y))
        self.assertEqual("Times New Roman", FIG3_FONT)
        self.assertEqual(429, FIG3_FONT_ID)
        for mode in ("UC", "TR"):
            legend_x, legend_y = _legend_segment(0.05, 0.18, 200.0, mode)
            self.assertEqual(len(legend_x), len(legend_y))
            self.assertTrue(any(value != value for value in legend_y))
        _, solid_y = _legend_segment(0.05, 0.18, 200.0, "PSC")
        self.assertFalse(any(value != value for value in solid_y))

    def test_skill_is_bounded_and_reference_links_resolve(self) -> None:
        path = ROOT / "SKILL.md"
        text = path.read_text(encoding="utf-8-sig")
        self.assertLessEqual(len(text.splitlines()), 250)
        self.assertLess(path.stat().st_size, 30_000)
        links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
        self.assertGreaterEqual(len(links), 7)
        for link in links:
            self.assertTrue((ROOT / link).is_file(), link)

    def test_readme_is_scope_honest_and_has_required_sections(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8-sig")
        self.assertNotIn("examples reproduce Fig12, Fig15, and Fig16", text)
        self.assertIn("not raw-data recovery or pixel identity", text)
        self.assertIn("Frozen regression identity plus same-run visual gates", text)
        self.assertIn("## Install as a Codex skill", text)
        self.assertIn("## Add a builder", text)

    def test_official_sources_and_continuous_admin_rule_are_explicit(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8-sig")
        readme = (ROOT / "README.md").read_text(encoding="utf-8-sig")
        for url in (
            "https://www.originlab.com/www/products/GraphGallery.aspx?s=0&sort=Newest",
            "https://docs.originlab.com/zh/",
            "https://www.originlab.com/videos/index.aspx?CID=11",
            "https://docs.originlab.com/quick-help/graphing/zh/",
        ):
            self.assertIn(url, text)
            self.assertIn(url, readme)
        self.assertIn("examples/template_search/aa2195_official_template_search.json", readme)
        self.assertIn("administrator privilege for the entire live lifecycle", text)
        self.assertIn("every helper process that touches Origin must remain elevated", text)

    def test_formal_default_forbids_smoke_preflight_and_requires_post_attach_identity(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8-sig")
        runtime = (ROOT / "references" / "origin-runtime.md").read_text(encoding="utf-8-sig")
        for content in (text, runtime):
            self.assertIn("Do not run `origin_attach_smoke.py` as the default formal preflight", content)
            self.assertIn("E123_ORIGIN_SESSION_IDENTITY_DRIFT", content)

    def test_current_docs_do_not_advertise_v4_as_runtime(self) -> None:
        for filename in ("README.md", "SKILL.md"):
            text = (ROOT / filename).read_text(encoding="utf-8-sig").lower()
            self.assertNotIn("run originplot_runtime_v4.py", text)
        v4_protocol = (ROOT / "FIGURESPEC_V4_PROTOCOL.md").read_text(encoding="utf-8-sig").lower()
        self.assertIn("legacy protocol", v4_protocol)
        self.assertIn("not a supported p14 execution route", v4_protocol)
        self.assertNotIn("from `scripts/originplot_runtime_v4.py error-codes`", v4_protocol)
        legacy = (ROOT / "references" / "legacy-and-migration.md").read_text(encoding="utf-8-sig")
        self.assertIn("legacy inputs", legacy)

    def test_implementation_report_contains_all_fourteen_required_sections(self) -> None:
        text = (ROOT / "P14_IMPLEMENTATION_REPORT.md").read_text(encoding="utf-8-sig")
        headings = [line for line in text.splitlines() if re.match(r"^## \d+\. ", line)]
        self.assertEqual(list(range(1, 15)), [int(line.split(".", 1)[0][3:]) for line in headings])


class RegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from builders import base, registry

        cls.base = base
        cls.registry = registry

    def test_builtin_registry_and_legacy_ids(self) -> None:
        self.assertTrue({"fig3", "fig12", "fig14", "fig15", "fig16", "generic_line"}.issubset(self.registry.list_builders()))
        for figure in ("fig3", "fig12", "fig14", "fig15", "fig16"):
            definition = self.registry.resolve_builder(figure=figure)
            self.assertEqual(figure, definition.builder_id)
            self.assertTrue(definition.supports_live)

    def test_duplicate_and_unknown_ids_fail(self) -> None:
        builder_id = "__p14_duplicate_test__"
        definition = self.base.BuilderDefinition(builder_id=builder_id, description="test")
        self.registry.register_builder(builder_id, definition)
        with self.assertRaises(self.registry.DuplicateBuilderError):
            self.registry.register_builder(builder_id, definition)
        with self.assertRaises(self.registry.UnknownBuilderError):
            self.registry.get_builder("__p14_unknown_test__")

    def test_generic_plan_validates_spec_candidate_relationship(self) -> None:
        definition = self.registry.get_builder("generic_line")
        candidate = json.loads((ROOT / "examples/public_demo/candidate.json").read_text(encoding="utf-8"))
        figure_spec = json.loads((ROOT / "examples/public_demo/figure_spec.json").read_text(encoding="utf-8"))
        plan = definition.validate_plan(candidate, figure_spec)
        self.assertEqual("offline_plan_validated", plan["validation"])
        bad = dict(candidate, figure="wrong")
        with self.assertRaises(ValueError):
            definition.validate_plan(bad, figure_spec)


class CandidateCliTests(unittest.TestCase):
    def command(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "scripts/origin_candidate_worker.py", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def generic_args(self, output: Path) -> list[str]:
        return [
            "--builder", "generic_line",
            "--figure-spec", "examples/public_demo/figure_spec.json",
            "--candidate", "examples/public_demo/candidate.json",
            "--output-dir", str(output),
        ]

    def test_explicit_and_legacy_default_dry_run_are_not_success_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            explicit = self.command(*self.generic_args(Path(tmp) / "explicit"), "--dry-run")
            self.assertEqual(0, explicit.returncode, explicit.stderr)
            payload = json.loads(explicit.stdout)
            self.assertTrue(payload["command_success"])
            for key in ("structure_pass", "visual_pass", "live_origin_verified", "pass_eligible"):
                self.assertFalse(payload[key], key)
            self.assertEqual("planned_not_executed", payload["overall_status"])
            legacy = self.command(*self.generic_args(Path(tmp) / "legacy"))
            self.assertEqual(0, legacy.returncode)
            self.assertIn("legacy-compatible --dry-run", legacy.stderr)

    def test_mode_conflict_is_argument_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.command(*self.generic_args(Path(tmp)), "--dry-run", "--live")
        self.assertEqual(2, result.returncode)

    def test_live_unimplemented_and_require_live_success_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.command(*self.generic_args(Path(tmp)), "--live", "--require-live-success")
            payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertEqual("E440_PLOT_FAMILY_NOT_IMPLEMENTED", payload["error_code"])
        self.assertFalse(payload["live_origin_verified"])

    def test_packaged_source_placeholder_fails_with_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            candidate = json.loads(
                (ROOT / "examples/candidates/fig12.json").read_text(encoding="utf-8")
            )
            candidate["source_crop"] = "AUTHORIZED_LOCAL_SOURCE_REQUIRED"
            candidate["template_search_record"] = str(
                (ROOT / "examples/template_search/aa2195_official_template_search.json").resolve()
            )
            candidate_path = Path(tmp) / "fig12.json"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            result = self.command(
                "--builder", "fig12",
                "--candidate", str(candidate_path),
                "--output-dir", str(Path(tmp) / "fig12"),
                "--live", "--require-live-success",
            )
            payload = json.loads(result.stdout)
        self.assertEqual(1, result.returncode)
        self.assertEqual("E124_AUTHORIZED_SOURCE_REQUIRED", payload["error_code"])
        self.assertTrue(payload["origin_attach_not_attempted"])
        self.assertIn("authorized local source image", payload["message"])

    def test_legacy_figures_still_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for figure in ("fig3", "fig12", "fig14", "fig15", "fig16"):
                result = self.command(
                    "--figure", figure,
                    "--candidate", f"examples/candidates/{figure}.json",
                    "--output-dir", str(Path(tmp) / figure),
                    "--dry-run",
                )
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(figure, json.loads(result.stdout)["builder_id"])

    def test_paper_like_route_rejects_missing_template_search_record(self) -> None:
        candidate = json.loads(
            (ROOT / "examples/candidates/fig12.json").read_text(encoding="utf-8")
        )
        candidate.pop("template_search_record", None)
        with tempfile.TemporaryDirectory() as tmp:
            candidate_path = Path(tmp) / "fig12-without-template-search.json"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            result = self.command(
                "--figure", "fig12",
                "--candidate", str(candidate_path),
                "--output-dir", str(Path(tmp) / "plan"),
                "--dry-run",
            )
        self.assertEqual(1, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual("E130_TEMPLATE_SEARCH_REQUIRED", payload["error_code"])
        self.assertFalse(payload["command_success"])

    def test_legacy_figures_accept_audited_template_search_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for figure in ("fig3", "fig12", "fig14", "fig15", "fig16"):
                result = self.command(
                    "--figure", figure,
                    "--candidate", f"examples/candidates/{figure}.json",
                    "--output-dir", str(Path(tmp) / figure),
                    "--dry-run",
                )
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                payload = json.loads(result.stdout)
                gate = payload["template_search_gate"]
                self.assertEqual("pass", gate["status"])
                self.assertEqual("originplot.template_search_record.v1", gate["schema"])
                self.assertRegex(gate["record_sha256"], r"^[0-9a-f]{64}$")
                self.assertIn(figure, gate["figures"])

    def test_portable_candidates_include_resolvable_source_crops(self) -> None:
        worker = load("candidate_worker_source_assets", "scripts/origin_candidate_worker.py")
        for figure in ("fig3", "fig12", "fig14", "fig15", "fig16"):
            candidate_path = ROOT / f"examples/candidates/{figure}.json"
            candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
            source_crop = worker._resolve_source_crop(candidate, candidate_path)
            self.assertIsNotNone(source_crop)
            self.assertTrue(source_crop.is_file(), source_crop)

    def test_canonical_fig12_candidate_uses_promoted_editable_visual_route(self) -> None:
        candidate = json.loads(
            (ROOT / "examples/candidates/fig12.json").read_text(encoding="utf-8")
        )
        self.assertTrue(candidate["fig12_path_overlays"])
        self.assertTrue(candidate["fig12_axis_title_overlays"])
        self.assertEqual(11.0, candidate["fig12_label_sizes"]["panel"])
        self.assertEqual(10.0, candidate["fig12_label_sizes"]["mechanism"])

    def test_fig12_path_overlay_uses_unique_cleaned_temporary_directory(self) -> None:
        source = (ROOT / "builders/aa2195/fig12_builder.py").read_text(encoding="utf-8")
        self.assertIn("TemporaryDirectory(prefix=\"originplot_fig12_\")", source)
        self.assertNotIn("tempfile.gettempdir()", source)

    def test_template_search_record_requires_selection_decision(self) -> None:
        record = json.loads(
            (ROOT / "examples/template_search/aa2195_official_template_search.json").read_text(
                encoding="utf-8"
            )
        )
        record["templates"]["GID499"]["decision"] = ""
        candidate = json.loads(
            (ROOT / "examples/candidates/fig12.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "invalid-template-search.json"
            record_path.write_text(json.dumps(record), encoding="utf-8")
            candidate["template_search_record"] = str(record_path)
            candidate_path = Path(tmp) / "candidate.json"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            result = self.command(
                "--figure", "fig12",
                "--candidate", str(candidate_path),
                "--output-dir", str(Path(tmp) / "plan"),
                "--dry-run",
            )
        self.assertEqual(1, result.returncode)
        self.assertEqual("E130_TEMPLATE_SEARCH_REQUIRED", json.loads(result.stdout)["error_code"])

    def test_malformed_template_search_record_uses_stable_gate_error(self) -> None:
        candidate = json.loads(
            (ROOT / "examples/candidates/fig12.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as tmp:
            record_path = Path(tmp) / "broken.json"
            record_path.write_text("{not-json", encoding="utf-8")
            candidate["template_search_record"] = str(record_path)
            candidate_path = Path(tmp) / "candidate.json"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            result = self.command(
                "--figure", "fig12",
                "--candidate", str(candidate_path),
                "--output-dir", str(Path(tmp) / "plan"),
                "--dry-run",
            )
        self.assertEqual(1, result.returncode)
        self.assertEqual("E130_TEMPLATE_SEARCH_REQUIRED", json.loads(result.stdout)["error_code"])


class ReproducibilityTests(unittest.TestCase):
    def test_dependency_files_and_audit(self) -> None:
        for filename in ("requirements-core.txt", "requirements-origin.txt", "requirements-dev.txt"):
            self.assertTrue((ROOT / filename).is_file())
        audit = load("p14_dependency_audit", "scripts/audit_dependencies.py").audit()
        self.assertEqual("ok", audit["status"], audit)

    def test_public_demo_generation_is_rebuildable(self) -> None:
        generator = load("p14_public_demo", "examples/public_demo/generate_source.py")
        with tempfile.TemporaryDirectory() as tmp:
            result = generator.generate(Path(tmp))
            self.assertTrue(Path(result["csv"]).is_file())
            self.assertTrue(Path(result["reference_png"]).is_file())

    def test_offline_ci_does_not_claim_live_origin(self) -> None:
        workflow = (ROOT / ".github/workflows/offline-ci.yml").read_text(encoding="utf-8")
        self.assertIn("windows-latest", workflow)
        self.assertIn("python-version: \"3.10\"", workflow)
        self.assertNotIn("--live", workflow)
        self.assertIn("does not install Origin or claim live Origin E2E", workflow)

    def test_official_template_inspector_gates_before_origin_import_and_detaches(self) -> None:
        source = (ROOT / "scripts/inspect_official_templates.py").read_text(encoding="utf-8-sig")
        admin_gate = source.index("if not is_administrator_python()")
        visible_gate = source.index("if not has_visible_origin_process()")
        origin_import = source.index("import originpro as op")
        self.assertLess(admin_gate, origin_import)
        self.assertLess(visible_gate, origin_import)
        self.assertIn("op.detach()", source)
        self.assertIn("compatible_open", source)
        self.assertIn("opened_editable", source)

    def test_shareable_package_requires_official_template_search_record(self) -> None:
        builder = load("p14_package_builder", "scripts/build_shareable_package.py")
        validator = load("p14_package_validator", "scripts/validate_shareable_package_v5.py")
        required_entry = "originplot-skill/examples/template_search/aa2195_official_template_search.json"
        with tempfile.TemporaryDirectory() as tmp:
            complete_zip = Path(tmp) / "complete.zip"
            incomplete_zip = Path(tmp) / "incomplete.zip"
            builder.build_zip(ROOT, complete_zip)
            with zipfile.ZipFile(complete_zip) as source, zipfile.ZipFile(incomplete_zip, "w") as target:
                record = json.loads(source.read(required_entry).decode("utf-8"))
                urls = {item["url"] for item in record["official_sources"]}
                self.assertEqual(
                    {
                        "https://www.originlab.com/www/products/GraphGallery.aspx?s=0&sort=Newest",
                        "https://docs.originlab.com/zh/",
                        "https://www.originlab.com/videos/index.aspx?CID=11",
                        "https://docs.originlab.com/quick-help/graphing/zh/",
                    },
                    urls,
                )
                for entry in source.infolist():
                    if entry.filename != required_entry:
                        target.writestr(entry, source.read(entry.filename))
            result = validator.validate(incomplete_zip)
        self.assertEqual("failed", result["status"])
        self.assertIn(
            required_entry,
            {item.get("entry") for item in result["failures"]},
        )

    def test_shareable_validator_rejects_candidate_source_raster(self) -> None:
        validator = load("p14_package_validator_raster", "scripts/validate_shareable_package_v5.py")
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "invalid.zip"
            with zipfile.ZipFile(package, "w") as archive:
                for required in validator.REQUIRED:
                    archive.writestr(required, b"{}")
                archive.writestr(
                    "originplot-skill/examples/candidates/source/fig12_source.png",
                    b"not-a-distributable-raster",
                )
            result = validator.validate(package)
        raster_failures = [
            item for item in result["failures"]
            if item.get("entry", "").endswith("fig12_source.png")
        ]
        self.assertTrue(raster_failures)

    def test_package_builder_ignores_parent_directory_names(self) -> None:
        builder = load("p14_package_builder_parent_path", "scripts/build_shareable_package.py")
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "outputs" / "originplot-skill"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text("---\nname: originplot\n---\n", encoding="utf-8")
            package = Path(tmp) / "package.zip"
            result = builder.build_zip(skill_dir, package)
            with zipfile.ZipFile(package) as archive:
                entries = set(archive.namelist())
        self.assertEqual(1, result["entry_count"])
        self.assertIn("originplot-skill/SKILL.md", entries)


if __name__ == "__main__":
    unittest.main()
