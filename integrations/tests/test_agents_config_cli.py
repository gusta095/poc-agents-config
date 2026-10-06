from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

from hub_fixture import (
    make_agent,
    make_command,
    make_integration,
    make_skill,
    read_integration,
    write_integration,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/agents_config.py"
SPEC = importlib.util.spec_from_file_location("agents_config", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load {MODULE_PATH}")
agents_config = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agents_config)


class AgentsConfigCliTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.home = self.root / "home"
        self.home.mkdir()
        make_skill(self.repo, "router")
        write_integration(self.repo, make_integration("example", home_env=["EXAMPLE_HOME"]))

    def test_connect_writes_receipt_and_links(self):
        agents_config.connect(self.repo, "example", self.home)

        receipt = agents_config.load_receipt(self.home, "example")
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["consumer"], "example")
        self.assertEqual(len(receipt["links"]), 2)
        self.assertTrue((self.home / ".example/ENTRY.md").is_symlink())
        self.assertTrue((self.home / ".example/skills/router").is_symlink())

    def test_status_reports_not_connected_before_connect(self):
        report = agents_config.status(self.repo, self.home)
        self.assertEqual(report["example"], ["not connected"])

    def test_status_reports_ok_after_connect(self):
        agents_config.connect(self.repo, "example", self.home)
        report = agents_config.status(self.repo, self.home)
        self.assertEqual(report["example"], ["ok"])

    def test_status_reports_missing_link(self):
        agents_config.connect(self.repo, "example", self.home)
        (self.home / ".example/ENTRY.md").unlink()

        report = agents_config.status(self.repo, self.home)
        self.assertTrue(any("missing link" in problem for problem in report["example"]))

    def test_status_reports_drifted_link(self):
        agents_config.connect(self.repo, "example", self.home)
        target = self.home / ".example/ENTRY.md"
        target.unlink()
        other_source = self.root / "other.md"
        other_source.write_text("# Other\n", encoding="utf-8")
        target.symlink_to(other_source)

        report = agents_config.status(self.repo, self.home)
        self.assertTrue(any("drifted" in problem for problem in report["example"]))

    def test_status_reports_source_missing(self):
        agents_config.connect(self.repo, "example", self.home)
        (self.repo / "config/example/ENTRY.md").unlink()

        report = agents_config.status(self.repo, self.home)
        self.assertTrue(any("source missing" in problem for problem in report["example"]))

    def test_status_reports_manifest_drift(self):
        agents_config.connect(self.repo, "example", self.home)
        integration = read_integration(self.repo, "example")
        integration["skills"]["names"] = []
        write_integration(self.repo, integration)

        report = agents_config.status(self.repo, self.home)
        self.assertTrue(any("run 'sync'" in problem for problem in report["example"]))

    def test_plan_reports_changes_without_touching_the_home(self):
        results = agents_config.plan(self.repo, "example", self.home)

        self.assertTrue(any(line.startswith("create ") for line in results))
        self.assertIn("plan complete: no changes made", results)
        self.assertFalse((self.home / ".example").exists())
        self.assertFalse(agents_config.receipt_path(self.home, "example").exists())

    def test_connect_preflight_leaves_no_partial_links_or_receipt(self):
        conflict = self.home / ".example/skills/router"
        conflict.parent.mkdir(parents=True)
        conflict.write_text("unmanaged\n", encoding="utf-8")

        with self.assertRaises(SystemExit):
            agents_config.connect(self.repo, "example", self.home)

        self.assertFalse((self.home / ".example/ENTRY.md").exists())
        self.assertFalse(agents_config.receipt_path(self.home, "example").exists())

    def test_invalid_receipt_has_an_actionable_error(self):
        receipt = agents_config.receipt_path(self.home, "example")
        receipt.parent.mkdir(parents=True)
        receipt.write_text("{invalid", encoding="utf-8")

        with self.assertRaises(SystemExit) as raised:
            agents_config.status(self.repo, self.home)

        self.assertIn("invalid receipt", str(raised.exception))

    def test_status_does_not_run_environment_checks(self):
        self.assertNotIn("environment", agents_config.status(self.repo, self.home))

    def test_doctor_keeps_the_connection_report_from_status(self):
        agents_config.connect(self.repo, "example", self.home)
        report = agents_config.doctor(self.repo, self.home)

        self.assertEqual(report["example"], agents_config.status(self.repo, self.home)["example"])

    def test_doctor_environment_is_ok_when_everything_is_in_place(self):
        report = agents_config.doctor(self.repo, self.home)

        self.assertEqual(report["environment"], ["ok"])

    def test_doctor_reports_hub_layout_errors(self):
        (self.repo / "skills/orphan").mkdir()
        report = agents_config.doctor(self.repo, self.home)

        self.assertTrue(any("skills/orphan has no SKILL.md" in p for p in report["environment"]))

    def test_doctor_reports_missing_install_home(self):
        report = agents_config.doctor(self.repo, self.root / "nowhere")

        self.assertTrue(any("install home does not exist" in p for p in report["environment"]))

    def test_doctor_exit_code_is_nonzero_on_environment_problem(self):
        report = agents_config.doctor(self.repo, self.root / "nowhere")

        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = agents_config._print_report(report)

        self.assertEqual(exit_code, 1)

    def test_sync_removes_orphaned_link_pointing_where_recorded(self):
        agents_config.connect(self.repo, "example", self.home)
        integration = read_integration(self.repo, "example")
        integration["skills"]["names"] = []
        write_integration(self.repo, integration)

        results = agents_config.sync(self.repo, "example", self.home)

        self.assertFalse((self.home / ".example/skills/router").exists())
        self.assertTrue(any("removed orphaned" in line for line in results))

    def test_sync_keeps_orphaned_link_modified_by_hand(self):
        agents_config.connect(self.repo, "example", self.home)
        skill_target = self.home / ".example/skills/router"
        skill_target.unlink()
        other_source = self.root / "other-skill"
        other_source.mkdir()
        skill_target.symlink_to(other_source)

        integration = read_integration(self.repo, "example")
        integration["skills"]["names"] = []
        write_integration(self.repo, integration)

        results = agents_config.sync(self.repo, "example", self.home)

        self.assertTrue(skill_target.is_symlink())
        self.assertTrue(any("skip orphaned" in line for line in results))

    def test_disconnect_removes_links_and_receipt(self):
        agents_config.connect(self.repo, "example", self.home)
        agents_config.disconnect(self.home, "example")

        self.assertFalse((self.home / ".example/ENTRY.md").exists())
        self.assertFalse((self.home / ".example/skills/router").exists())
        self.assertIsNone(agents_config.load_receipt(self.home, "example"))

    def test_disconnect_skips_link_modified_by_hand(self):
        agents_config.connect(self.repo, "example", self.home)
        target = self.home / ".example/ENTRY.md"
        target.unlink()
        other_source = self.root / "other.md"
        other_source.write_text("# Other\n", encoding="utf-8")
        target.symlink_to(other_source)

        results = agents_config.disconnect(self.home, "example")

        self.assertTrue(target.is_symlink())
        self.assertTrue(any("skip" in line for line in results))

    def test_disconnect_without_receipt_is_a_noop(self):
        results = agents_config.disconnect(self.home, "example")
        self.assertIn("nothing to disconnect", results[0])

    def test_validate_wraps_hub_manifest_validation(self):
        self.assertEqual(agents_config.validate(self.repo), [])

        integration = read_integration(self.repo, "example")
        integration["schema_version"] = 99
        write_integration(self.repo, integration)
        self.assertTrue(agents_config.validate(self.repo))

    def test_receipt_is_not_written_inside_the_repo(self):
        agents_config.connect(self.repo, "example", self.home)
        receipt = agents_config.receipt_path(self.home, "example")
        self.assertTrue(str(receipt).startswith(str(self.home)))
        self.assertFalse(str(receipt).startswith(str(self.repo)))


class CliAgentsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.home = self.root / "home"
        self.home.mkdir()
        make_skill(self.repo, "router")
        make_agent(self.repo, "helper")
        write_integration(
            self.repo, make_integration("example", home_env=["EXAMPLE_HOME"], agents=["helper"])
        )
        self.agent_link = self.home / ".example/agents/helper.md"

    def test_connect_records_the_agent_link_in_the_receipt(self):
        agents_config.connect(self.repo, "example", self.home)

        receipt = agents_config.load_receipt(self.home, "example")
        self.assertEqual(len(receipt["links"]), 3)
        self.assertIn(str(self.agent_link), [link["target"] for link in receipt["links"]])
        self.assertTrue(self.agent_link.is_symlink())

    def test_status_is_ok_after_connect(self):
        agents_config.connect(self.repo, "example", self.home)
        self.assertEqual(agents_config.status(self.repo, self.home)["example"], ["ok"])

    def test_status_reports_a_missing_agent_link(self):
        agents_config.connect(self.repo, "example", self.home)
        self.agent_link.unlink()

        problems = agents_config.status(self.repo, self.home)["example"]
        self.assertTrue(any("missing link" in problem for problem in problems))

    def test_status_reports_manifest_drift_when_an_agent_is_added(self):
        agents_config.connect(self.repo, "example", self.home)
        make_agent(self.repo, "other")
        write_integration(
            self.repo,
            make_integration("example", home_env=["EXAMPLE_HOME"], agents=["helper", "other"]),
        )

        problems = agents_config.status(self.repo, self.home)["example"]
        self.assertTrue(any("run 'sync'" in problem for problem in problems))

    def test_sync_removes_an_agent_link_no_longer_in_the_manifest(self):
        agents_config.connect(self.repo, "example", self.home)
        write_integration(self.repo, make_integration("example", home_env=["EXAMPLE_HOME"], agents=[]))

        results = agents_config.sync(self.repo, "example", self.home)

        self.assertFalse(self.agent_link.is_symlink())
        self.assertTrue(any("removed orphaned" in line for line in results))

    def test_sync_leaves_a_changed_agent_link_alone(self):
        agents_config.connect(self.repo, "example", self.home)
        self.agent_link.unlink()
        other = self.root / "other.md"
        other.write_text("mine\n", encoding="utf-8")
        self.agent_link.symlink_to(other)
        write_integration(self.repo, make_integration("example", home_env=["EXAMPLE_HOME"], agents=[]))

        agents_config.sync(self.repo, "example", self.home)

        self.assertEqual(self.agent_link.resolve(), other.resolve())

    def test_disconnect_removes_the_agent_link(self):
        agents_config.connect(self.repo, "example", self.home)

        agents_config.disconnect(self.home, "example")

        self.assertFalse(self.agent_link.is_symlink())


class CliEntrylessTest(unittest.TestCase):
    """Consumidor sem arquivo de entrada, com skills e commands: o caso do Cursor."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.home = self.root / "home"
        self.home.mkdir()
        make_skill(self.repo, "router")
        make_command(self.repo, "example", "run")
        write_integration(
            self.repo,
            make_integration("example", home_env=["EXAMPLE_HOME"], with_entry=False, commands=["run"]),
        )
        self.skill_link = self.home / ".example/skills/router"
        self.command_link = self.home / ".example/commands/run.md"

    def test_connect_links_skills_and_commands_and_writes_receipt(self):
        agents_config.connect(self.repo, "example", self.home)

        self.assertTrue(self.skill_link.is_symlink())
        self.assertTrue(self.command_link.is_symlink())
        receipt = agents_config.load_receipt(self.home, "example")
        self.assertEqual(len(receipt["links"]), 2)
        self.assertEqual(agents_config.status(self.repo, self.home)["example"], ["ok"])

    def test_receipt_lives_under_agents_config_dir(self):
        agents_config.connect(self.repo, "example", self.home)
        self.assertEqual(
            agents_config.receipt_path(self.home, "example"),
            self.home / ".agents-config/receipts/example.json",
        )

    def test_status_reports_a_missing_command_link(self):
        agents_config.connect(self.repo, "example", self.home)
        self.command_link.unlink()

        problems = agents_config.status(self.repo, self.home)["example"]
        self.assertTrue(any("missing link" in problem for problem in problems))

    def test_disabling_a_command_and_syncing_removes_only_its_link(self):
        agents_config.connect(self.repo, "example", self.home)
        write_integration(
            self.repo,
            make_integration("example", home_env=["EXAMPLE_HOME"], with_entry=False, commands=[]),
        )

        results = agents_config.sync(self.repo, "example", self.home)

        self.assertFalse(self.command_link.is_symlink())
        self.assertTrue(self.skill_link.is_symlink())
        self.assertTrue(any("removed orphaned" in line for line in results))
        self.assertEqual(agents_config.status(self.repo, self.home)["example"], ["ok"])

    def test_disconnect_removes_links_and_receipt(self):
        agents_config.connect(self.repo, "example", self.home)

        agents_config.disconnect(self.home, "example")

        self.assertFalse(self.skill_link.is_symlink())
        self.assertFalse(self.command_link.is_symlink())
        self.assertIsNone(agents_config.load_receipt(self.home, "example"))

    def test_connect_refuses_to_replace_an_existing_command(self):
        self.command_link.parent.mkdir(parents=True)
        self.command_link.write_text("mine\n", encoding="utf-8")

        with self.assertRaises(SystemExit):
            agents_config.connect(self.repo, "example", self.home)

        self.assertFalse(self.skill_link.exists())
        self.assertEqual(self.command_link.read_text(encoding="utf-8"), "mine\n")

    def test_command_name_traversal_is_rejected_without_side_effects(self):
        make_command(self.repo, "example", "plan")
        (self.repo / "README.md").write_text("# readme\n", encoding="utf-8")
        write_integration(
            self.repo,
            make_integration(
                "example", home_env=["EXAMPLE_HOME"], with_entry=False,
                commands=["plan", "../../../README"],
            ),
        )
        before = {p for p in self.root.rglob("*")}

        for action in (agents_config.connect, agents_config.plan, agents_config.sync):
            with self.subTest(action=action.__name__):
                with self.assertRaises(SystemExit) as raised:
                    action(self.repo, "example", self.home)
                self.assertIn("unknown command", str(raised.exception))

        self.assertEqual({p for p in self.root.rglob("*")}, before)
        self.assertIsNone(agents_config.load_receipt(self.home, "example"))


if __name__ == "__main__":
    unittest.main()
