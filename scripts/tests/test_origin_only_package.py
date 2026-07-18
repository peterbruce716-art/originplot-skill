from __future__ import annotations

import importlib.util
import json
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class OriginOnlyPackageTests(unittest.TestCase):
    def test_skill_routes_open_code_reproduction_elsewhere(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("editable Origin project", text)
        self.assertIn("scientific-figure-reproduction", text)
        self.assertIn("Verified Origin Runtime", text)
        self.assertNotIn("Python " + "Mat" + "plotlib visual render", text)
        self.assertNotIn("r_" + "ggplot2", text)

    def test_no_open_code_redraw_files_are_packaged(self) -> None:
        names = [
            path.relative_to(ROOT).as_posix().lower()
            for path in ROOT.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and "tmp_v5_validation" not in path.parts
        ]
        forbidden = ["visual" + "spec", "render_" + "visual" + "spec", "score_iteration", "run_visual_optimization_loop", "mat" + "plotlib"]
        for fragment in forbidden:
            self.assertFalse(any(fragment in name for name in names), fragment)

    def test_capability_profiles_are_fail_closed(self) -> None:
        for path in (ROOT / "capabilities").glob("origin-*.json"):
            profile = json.loads(path.read_text(encoding="utf-8"))
            if profile.get("schema") == "originplot.capabilities.v5":
                self.assertIn("adapters", profile)
                if path.name.endswith(".example.json"):
                    self.assertIn("example", profile.get("environment", {}).get("policy", ""))
                    continue
                self.assertTrue(
                    any(
                        operation.get("verified") is not True
                        for adapter in profile["adapters"].values()
                        for operation in (adapter.get("operations") or {}).values()
                    ),
                    path,
                )
            else:
                self.assertIn("operations", profile)
                for operation in profile["operations"]:
                    self.assertIn(operation["status"], profile["status_values"])
                    self.assertTrue(operation.get("must_verify_locally"))

    def test_shareable_validator_accepts_built_origin_only_archive(self) -> None:
        validator = load_module("validate_shareable_package_v5", SCRIPTS / "validate_shareable_package_v5.py")
        builder = load_module("build_shareable_package_for_validation", SCRIPTS / "build_shareable_package.py")
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "originplot-skill.zip"
            builder.build_zip(ROOT, archive_path)
            result = validator.validate(archive_path)
        self.assertEqual("ok", result["status"], result["failures"])

    def test_shareable_archive_excludes_generated_outputs(self) -> None:
        builder = load_module("build_shareable_package_test", SCRIPTS / "build_shareable_package.py")
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "originplot-skill.zip"
            builder.build_zip(ROOT, archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
                candidate = json.loads(archive.read("originplot-skill/examples/candidates/fig12.json"))
        self.assertFalse(any("/outputs/" in name for name in names))
        self.assertFalse(
            any(part.casefold().startswith("tmp_") for name in names for part in Path(name).parts)
        )
        self.assertFalse(any(name.lower().endswith((".png", ".jpg", ".jpeg")) for name in names))
        self.assertFalse(any("/examples/candidates/source/" in name for name in names))
        self.assertEqual("AUTHORIZED_LOCAL_SOURCE_REQUIRED", candidate["source_crop"])
        self.assertIn("authorized", candidate["source_crop_policy"])

    def test_shareable_builder_materializes_source_authorization_marker(self) -> None:
        builder = load_module("build_shareable_package_marker_test", SCRIPTS / "build_shareable_package.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            candidate_dir = root / "examples" / "candidates"
            candidate_dir.mkdir(parents=True)
            (candidate_dir / "fig12.json").write_text(
                json.dumps({"source_crop": "local-only-source.png"}),
                encoding="utf-8",
            )
            archive_path = Path(tmp) / "originplot-skill.zip"
            builder.build_zip(root, archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
                self.assertIn("originplot-skill/AUTHORIZED_LOCAL_SOURCE_REQUIRED", names)
                marker = archive.read("originplot-skill/AUTHORIZED_LOCAL_SOURCE_REQUIRED").decode("utf-8")
        self.assertIn("local source authorization contract", marker)

    def test_shareable_archive_excludes_local_virtual_environment(self) -> None:
        builder = load_module("build_shareable_package_venv_test", SCRIPTS / "build_shareable_package.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            sentinel = root / ".venv" / "Lib" / "site-packages" / "sentinel.py"
            sentinel.parent.mkdir(parents=True)
            sentinel.write_text("LOCAL_ENVIRONMENT_SENTINEL", encoding="utf-8")
            (root / "SKILL.md").write_text("---\nname: originplot\n---\n", encoding="utf-8")
            archive_path = Path(tmp) / "originplot-skill.zip"

            builder.build_zip(root, archive_path)

            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
                payload = b"\n".join(archive.read(name) for name in names)
        self.assertFalse(any(".venv" in name.lower() for name in names))
        self.assertNotIn(b"LOCAL_ENVIRONMENT_SENTINEL", payload)

    def test_shareable_validator_rejects_polluted_virtual_environment(self) -> None:
        validator = load_module("validate_shareable_package_polluted_venv", SCRIPTS / "validate_shareable_package_v5.py")
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "polluted.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    "originplot-skill/.venv/Lib/site-packages/sentinel.py",
                    "LOCAL_ENVIRONMENT_SENTINEL",
                )

            result = validator.validate(archive_path)

        self.assertEqual("failed", result["status"])
        self.assertIn(
            "forbidden_local_environment_path",
            {failure["code"] for failure in result["failures"]},
        )

    def test_shareable_validator_rejects_local_interpreter_binary(self) -> None:
        validator = load_module("validate_shareable_package_interpreter", SCRIPTS / "validate_shareable_package_v5.py")
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "polluted.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("originplot-skill/tools/python.exe", b"local interpreter")

            result = validator.validate(archive_path)

        self.assertEqual("failed", result["status"])
        self.assertIn(
            "forbidden_local_interpreter_binary",
            {failure["code"] for failure in result["failures"]},
        )

    def test_shareable_validator_rejects_parent_path_traversal(self) -> None:
        validator = load_module("validate_shareable_package_parent_traversal", SCRIPTS / "validate_shareable_package_v5.py")
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "polluted.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("originplot-skill/../outside.py", "escape")

            result = validator.validate(archive_path)

        self.assertEqual("failed", result["status"])
        self.assertIn(
            "unsafe_path_traversal",
            {failure["code"] for failure in result["failures"]},
        )

    def test_shareable_validator_rejects_zip_symlink_entry(self) -> None:
        validator = load_module("validate_shareable_package_zip_symlink", SCRIPTS / "validate_shareable_package_v5.py")
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "polluted.zip"
            info = zipfile.ZipInfo("originplot-skill/tools/outside-link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(info, "../../outside")

            result = validator.validate(archive_path)

        self.assertIn(
            "forbidden_zip_symlink",
            {failure["code"] for failure in result["failures"]},
        )

    def test_shareable_validator_rejects_environment_added_to_extracted_package(self) -> None:
        validator = load_module("validate_shareable_package_extracted_venv", SCRIPTS / "validate_shareable_package_v5.py")
        builder = load_module("build_shareable_package_extracted_venv", SCRIPTS / "build_shareable_package.py")
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            archive_path = temp / "clean.zip"
            extracted = temp / "extracted"
            builder.build_zip(ROOT, archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(extracted)
            sentinel = extracted / "originplot-skill" / ".venv" / "Lib" / "site-packages" / "sentinel.py"
            sentinel.parent.mkdir(parents=True)
            sentinel.write_text("LOCAL_ENVIRONMENT_SENTINEL", encoding="utf-8")

            result = validator.validate(extracted / "originplot-skill")

        self.assertEqual("failed", result["status"])
        self.assertIn(
            "forbidden_local_environment_path",
            {failure["code"] for failure in result["failures"]},
        )

    def test_shareable_validator_rejects_duplicate_zip_entry(self) -> None:
        validator = load_module("validate_shareable_package_duplicate_entry", SCRIPTS / "validate_shareable_package_v5.py")
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "polluted.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(archive_path, "w") as archive:
                    archive.writestr("originplot-skill/scripts/versioning.py", "first")
                    archive.writestr("originplot-skill/scripts/versioning.py", "second")

            result = validator.validate(archive_path)

        self.assertIn("duplicate_archive_entry", {failure["code"] for failure in result["failures"]})

    def test_shareable_validator_rejects_zip_path_alias_collisions(self) -> None:
        validator = load_module("validate_shareable_package_alias_collision", SCRIPTS / "validate_shareable_package_v5.py")
        for alias in (
            "originplot-skill/scripts/./versioning.py",
            "originplot-skill/scripts//versioning.py",
        ):
            with self.subTest(alias=alias), tempfile.TemporaryDirectory() as tmp:
                archive_path = Path(tmp) / "polluted.zip"
                with zipfile.ZipFile(archive_path, "w") as archive:
                    archive.writestr("originplot-skill/scripts/versioning.py", "first")
                    archive.writestr(alias, "second")

                result = validator.validate(archive_path)

            self.assertIn("duplicate_archive_entry", {failure["code"] for failure in result["failures"]})

    def test_shareable_validator_rejects_forbidden_coverage_file(self) -> None:
        validator = load_module("validate_shareable_package_coverage", SCRIPTS / "validate_shareable_package_v5.py")
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "polluted.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("originplot-skill/.coverage", "local coverage metadata")

            result = validator.validate(archive_path)

        self.assertIn("forbidden_local_file_name", {failure["code"] for failure in result["failures"]})

    def test_shareable_validator_returns_structured_failure_for_invalid_zip(self) -> None:
        validator = load_module("validate_shareable_package_invalid_zip", SCRIPTS / "validate_shareable_package_v5.py")
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "invalid.zip"
            archive_path.write_bytes(b"not a zip archive")

            result = validator.validate(archive_path)

        self.assertEqual("failed", result["status"])
        self.assertIn("invalid_archive", {failure["code"] for failure in result["failures"]})

    def test_shareable_validator_rejects_backslash_entry_without_crashing(self) -> None:
        validator = load_module("validate_shareable_package_backslash", SCRIPTS / "validate_shareable_package_v5.py")
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "polluted.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("originplot-skill/SKILL.md", "invalid portable path")
            archive_path.write_bytes(
                archive_path.read_bytes().replace(
                    b"originplot-skill/SKILL.md",
                    b"originplot-skill\\SKILL.md",
                )
            )

            result = validator.validate(archive_path)

        self.assertEqual("failed", result["status"])
        self.assertIn("backslash_zip_entry", {failure["code"] for failure in result["failures"]})

    def test_shareable_validator_rejects_non_object_candidate_without_crashing(self) -> None:
        validator = load_module("validate_shareable_package_candidate_type", SCRIPTS / "validate_shareable_package_v5.py")
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "polluted.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("originplot-skill/examples/candidates/fig3.json", "[]")

            result = validator.validate(archive_path)

        self.assertEqual("failed", result["status"])
        self.assertIn("invalid_candidate_json", {failure["code"] for failure in result["failures"]})

    def test_package_cli_rejects_nonexistent_skill_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp = Path(tmp)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "build_shareable_package.py"),
                    "--skill-dir",
                    str(temp / "missing"),
                    "--zip-out",
                    str(temp / "out.zip"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(0, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual("failed", payload["status"])
        self.assertEqual("source_skill_dir_missing", payload["failures"][0]["code"])

    def test_v5_compiler_and_runtime_fail_closed(self) -> None:
        compiler = load_module("originplot_compile_v5", SCRIPTS / "originplot_compile_v5.py")
        runtime = load_module("originplot_runtime_v5", SCRIPTS / "originplot_runtime_v5.py")
        spec = json.loads((ROOT / "examples" / "originplot_figurespec_v5_minimal.json").read_text(encoding="utf-8"))
        result = compiler.compile_v5(spec)
        self.assertEqual("ok", result["status"])
        self.assertEqual("originplot.compiled_ir.v5", result["compiled_ir"]["schema"])
        self.assertEqual("originplot.operation_plan.v5", result["operation_plan"]["schema"])
        self.assertIn("axis.verify_final", result["compiled_ir"]["operation_ids"])
        self.assertNotIn("axis.freeze", result["compiled_ir"]["operation_ids"])

        unverified_caps = json.loads((ROOT / "capabilities" / "origin-2022-v5.json").read_text(encoding="utf-8"))
        preflight = runtime.preflight(result["operation_plan"], unverified_caps)
        self.assertEqual("failed", preflight["preflight_status"])
        self.assertEqual("failed", preflight["overall_status"])

    def test_v5_dry_run_passes_only_with_verified_capability_fixture(self) -> None:
        compiler = load_module("originplot_compile_v5", SCRIPTS / "originplot_compile_v5.py")
        runtime = load_module("originplot_runtime_v5", SCRIPTS / "originplot_runtime_v5.py")
        spec = json.loads((ROOT / "examples" / "originplot_figurespec_v5_minimal.json").read_text(encoding="utf-8"))
        plan = compiler.compile_v5(spec)["operation_plan"]
        capabilities = verified_capabilities_from_plan(plan)
        preflight = runtime.preflight(plan, capabilities)
        self.assertEqual("pass", preflight["preflight_status"])
        self.assertEqual("incomplete", preflight["overall_status"])
        manifest = runtime.run(plan, capabilities, dry_run=True, adapter_modules={}, adapter_configs={})
        self.assertEqual("incomplete", manifest["overall_status"])
        self.assertEqual("pass", manifest["simulation_status"])
        self.assertTrue(all(item["result"].get("dry_run") for item in manifest["execution_trace"]))

    def test_v5_compiler_rejects_unregistered_plot_type(self) -> None:
        compiler = load_module("originplot_compile_v5_scatter", SCRIPTS / "originplot_compile_v5.py")
        spec = json.loads((ROOT / "examples" / "originplot_figurespec_v5_minimal.json").read_text(encoding="utf-8"))
        spec["plots"][0]["type"] = "scatter"
        with self.assertRaises(compiler.CompileError):
            compiler.compile_v5(spec)

    def test_production_noop_adapter_is_refused(self) -> None:
        adapter_module = load_module("originpro_adapter", ROOT / "adapters" / "originpro" / "adapter.py")
        with self.assertRaises(RuntimeError):
            adapter_module.Adapter({"allow_noop": True, "execution_mode": "live"})

    def test_local_agent_uses_runtime_v5_and_forwards_adapter_files(self) -> None:
        agent = load_module("originplot_local_agent", SCRIPTS / "originplot_local_agent.py")
        self.assertEqual("originplot_orchestrator.py", agent.runtime_script().name)
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            for name in ["spec.json", "ir.json", "plan.json", "caps.json", "modules.json", "configs.json"]:
                (temp / name).write_text("{}", encoding="utf-8")
            (temp / "modules.json").write_text(
                json.dumps(
                    {
                        "originpro": "adapters/originpro/adapter.py",
                        "inspection": "adapters/inspection/adapter.py",
                        "evidence_qa": "adapters/evidence_qa/adapter.py",
                    }
                ),
                encoding="utf-8",
            )
            args = agent.build_parser().parse_args(
                [
                    "submit",
                    "--root",
                    str(temp / "queue"),
                    "--no-start",
                    "--job-id",
                    "job_v5",
                    "--workspace",
                    str(temp),
                    "--figure-spec",
                    str(temp / "spec.json"),
                    "--compiled-ir",
                    str(temp / "ir.json"),
                    "--operation-plan",
                    str(temp / "plan.json"),
                    "--capabilities",
                    str(temp / "caps.json"),
                    "--manifest-out",
                    str(temp / "manifest.json"),
                    "--adapter-modules",
                    str(temp / "modules.json"),
                    "--adapter-configs",
                    str(temp / "configs.json"),
                ]
            )
            self.assertEqual(0, args.func(args))
            job = json.loads((temp / "queue" / "queue" / "inbox" / "job_v5.json").read_text(encoding="utf-8"))
            self.assertEqual(str((temp / "modules.json").resolve()), job["adapter_modules"])
            self.assertEqual(str((temp / "configs.json").resolve()), job["adapter_configs"])
            self.assertIn("originplot_agent_runs", job["run_dir"])

    def test_orchestrator_dry_run_is_incomplete(self) -> None:
        compiler = load_module("originplot_compile_v5_orch", SCRIPTS / "originplot_compile_v5.py")
        spec = json.loads((ROOT / "examples" / "originplot_figurespec_v5_minimal.json").read_text(encoding="utf-8"))
        plan = compiler.compile_v5(spec)["operation_plan"]
        capabilities = verified_capabilities_from_plan(plan)
        with tempfile.TemporaryDirectory() as tempdir:
            temp = Path(tempdir)
            plan_path = temp / "plan.json"
            caps_path = temp / "caps.json"
            modules_path = temp / "modules.json"
            configs_path = temp / "configs.json"
            manifest_path = temp / "manifest.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            caps_path.write_text(json.dumps(capabilities), encoding="utf-8")
            modules_path.write_text(json.dumps({}), encoding="utf-8")
            configs_path.write_text(json.dumps({}), encoding="utf-8")
            import subprocess

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "originplot_orchestrator.py"),
                    "--operation-plan",
                    str(plan_path),
                    "--capabilities",
                    str(caps_path),
                    "--adapter-modules",
                    str(modules_path),
                    "--adapter-configs",
                    str(configs_path),
                    "--run-dir",
                    str(temp / "run"),
                    "--manifest-out",
                    str(manifest_path),
                    "--workspace",
                    str(ROOT),
                    "--dry-run",
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual("dry_run", manifest["execution_mode"])
            self.assertEqual("incomplete", manifest["overall_status"])
            self.assertEqual("originplot_orchestrator.v5.2", manifest["orchestrator"])
            self.assertIn("stdout_log", manifest["command_results"][0])

    def test_timeout_controls_are_packaged(self) -> None:
        smoke = (SCRIPTS / "origin_attach_smoke.py").read_text(encoding="utf-8")
        orchestrator = (SCRIPTS / "originplot_orchestrator.py").read_text(encoding="utf-8")
        worker = (SCRIPTS / "origin_build_worker.py").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue((SCRIPTS / "origin_cleanup_embedding.py").exists())
        self.assertIn("--phase-timeout-seconds", smoke)
        self.assertIn("--child-process", smoke)
        self.assertIn("launch_delayed_embedding_cleanup", smoke)
        self.assertIn("--worker-timeout-seconds", orchestrator)
        self.assertIn("--runtime-timeout-seconds", worker)
        self.assertIn("E300_ORIGIN_ATTACH_FAILED", orchestrator)
        self.assertIn("phase-timeout-seconds", skill)

    def test_v52_originpro_adapter_has_no_axis_auto_rescale_freeze(self) -> None:
        text = (ROOT / "adapters" / "originpro" / "adapter.py").read_text(encoding="utf-8")
        self.assertNotIn("layer -a", text)
        self.assertIn("op_axis_verify_final", text)
        self.assertIn("_apply_and_verify", text)


def verified_capabilities_from_plan(plan: dict) -> dict:
    adapters: dict[str, dict] = {}
    for operation in plan["operations"]:
        route = operation["adapter_route"]
        adapters.setdefault(route, {"origin_version": "2022", "operations": {}})
        adapters[route]["operations"][operation["operation_id"]] = {
            "verified": True,
            "source": "unit-test-fixture",
        }
    return {
        "schema": "originplot.capabilities.v5",
        "environment": {
            "origin_version": "2022",
            "fingerprint": "unit-test-fixture",
            "policy": "verified fixture for runtime logic only",
        },
        "adapters": adapters,
    }


if __name__ == "__main__":
    unittest.main()
