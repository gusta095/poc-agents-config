from __future__ import annotations

import importlib.util
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
MODULE_PATH = ROOT / "scripts/hub_bootstrap.py"
SPEC = importlib.util.spec_from_file_location("hub_bootstrap", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load {MODULE_PATH}")
hub_bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hub_bootstrap)


class HubBootstrapTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.home = self.root / "home"
        self.home.mkdir()
        make_skill(self.repo, "router")
        write_integration(self.repo, make_integration("example", home_env=["EXAMPLE_HOME"]))
        write_integration(
            self.repo,
            make_integration(
                "example-shared",
                base="install_home",
                target_subdir=".agents/skills",
                home_env=["EXAMPLE_SHARED_HOME"],
            ),
        )

    def test_install_creates_entry_and_skill_symlinks(self):
        hub_bootstrap.install(self.repo, "example", self.home)

        entry_target = self.home / ".example/ENTRY.md"
        skill_target = self.home / ".example/skills/router"

        self.assertTrue(entry_target.is_symlink())
        self.assertEqual(entry_target.resolve(), (self.repo / "config/example/ENTRY.md").resolve())
        self.assertTrue(skill_target.is_symlink())
        self.assertEqual(
            skill_target.resolve(),
            (self.repo / "skills/router").resolve(),
        )

    def test_install_is_idempotent(self):
        hub_bootstrap.install(self.repo, "example", self.home)
        results = hub_bootstrap.install(self.repo, "example", self.home)
        self.assertTrue(all(line.startswith("ok ") for line in results))

    def test_install_refuses_to_replace_unmanaged_file(self):
        target_dir = self.home / ".example"
        target_dir.mkdir(parents=True)
        (target_dir / "ENTRY.md").write_text("not managed by the hub\n", encoding="utf-8")

        with self.assertRaises(SystemExit):
            hub_bootstrap.install(self.repo, "example", self.home)

    def test_install_refuses_to_replace_symlink_pointing_elsewhere(self):
        other_source = self.root / "other-entry.md"
        other_source.write_text("# Other\n", encoding="utf-8")
        target_dir = self.home / ".example"
        target_dir.mkdir(parents=True)
        (target_dir / "ENTRY.md").symlink_to(other_source)

        with self.assertRaises(SystemExit):
            hub_bootstrap.install(self.repo, "example", self.home)

    def test_install_preflights_every_link_before_creating_any(self):
        conflict = self.home / ".example/skills/router"
        conflict.parent.mkdir(parents=True)
        conflict.write_text("unmanaged\n", encoding="utf-8")

        with self.assertRaises(SystemExit):
            hub_bootstrap.install(self.repo, "example", self.home)

        self.assertFalse((self.home / ".example/ENTRY.md").exists())

    def test_install_home_base_ignores_entry_home_override(self):
        hub_bootstrap.install(self.repo, "example-shared", self.home)

        entry_target = self.home / ".example-shared/ENTRY.md"
        skill_target = self.home / ".agents/skills/router"

        self.assertTrue(entry_target.is_symlink())
        self.assertTrue(skill_target.is_symlink())

    def test_unknown_integration_fails(self):
        with self.assertRaises(SystemExit):
            hub_bootstrap.install(self.repo, "ghost", self.home)

    def test_unknown_skill_reference_fails(self):
        integration = read_integration(self.repo, "example")
        integration["skills"]["names"].append("ghost-skill")
        write_integration(self.repo, integration)

        with self.assertRaises(SystemExit):
            hub_bootstrap.install(self.repo, "example", self.home)

    def test_env_override_wins_over_default_home(self):
        override_home = self.root / "custom-home"
        os_environ_backup = dict(__import__("os").environ)
        try:
            __import__("os").environ["EXAMPLE_HOME"] = str(override_home)
            hub_bootstrap.install(self.repo, "example", self.home)
            self.assertTrue((override_home / "ENTRY.md").is_symlink())
            self.assertFalse((self.home / ".example").exists())
        finally:
            __import__("os").environ.clear()
            __import__("os").environ.update(os_environ_backup)


class HubBootstrapAgentsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.home = self.root / "home"
        self.home.mkdir()
        make_skill(self.repo, "router")
        make_agent(self.repo, "helper")
        make_agent(self.repo, "unlisted")
        write_integration(
            self.repo, make_integration("example", home_env=["EXAMPLE_HOME"], agents=["helper"])
        )

    def test_install_links_only_the_declared_agents_as_files(self):
        hub_bootstrap.install(self.repo, "example", self.home)

        linked = self.home / ".example/agents/helper.md"
        self.assertTrue(linked.is_symlink())
        self.assertEqual(linked.resolve(), (self.repo / "agents/helper.md").resolve())
        self.assertFalse((self.home / ".example/agents/unlisted.md").exists())

    def test_integration_without_agents_key_creates_no_agents_directory(self):
        write_integration(self.repo, make_integration("example", home_env=["EXAMPLE_HOME"]))

        hub_bootstrap.install(self.repo, "example", self.home)

        self.assertFalse((self.home / ".example/agents").exists())

    def test_install_refuses_to_replace_an_unmanaged_agent_file(self):
        target_dir = self.home / ".example/agents"
        target_dir.mkdir(parents=True)
        (target_dir / "helper.md").write_text("mine\n", encoding="utf-8")

        with self.assertRaises(SystemExit):
            hub_bootstrap.install(self.repo, "example", self.home)

    def test_unknown_agent_reference_fails(self):
        write_integration(
            self.repo, make_integration("example", home_env=["EXAMPLE_HOME"], agents=["ghost"])
        )

        with self.assertRaises(SystemExit):
            hub_bootstrap.install(self.repo, "example", self.home)

    def test_install_links_an_agent_variant_with_another_source_and_suffix(self):
        variant = self.repo / "agents/alt/helper.txt"
        variant.parent.mkdir(parents=True)
        variant.write_text("variant\n", encoding="utf-8")
        write_integration(
            self.repo,
            make_integration(
                "example",
                home_env=["EXAMPLE_HOME"],
                agents=["helper"],
                agent_source_subdir="agents/alt",
                agent_source_suffix=".txt",
                agent_target_suffix=".txt",
            ),
        )

        hub_bootstrap.install(self.repo, "example", self.home)

        linked = self.home / ".example/agents/helper.txt"
        self.assertTrue(linked.is_symlink())
        self.assertEqual(linked.resolve(), variant.resolve())


class HubBootstrapEntrylessTest(unittest.TestCase):
    """Consumidor sem arquivo global de entrada: o home vem do bloco `home`."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repo = self.root / "repo"
        self.home = self.root / "home"
        self.home.mkdir()
        make_skill(self.repo, "router")
        make_command(self.repo, "example", "run")
        make_command(self.repo, "example", "unused")
        write_integration(
            self.repo,
            make_integration(
                "example", home_env=["EXAMPLE_HOME"], with_entry=False, commands=["run"]
            ),
        )

    def test_install_links_skills_and_commands_without_an_entry_file(self):
        hub_bootstrap.install(self.repo, "example", self.home)

        skill = self.home / ".example/skills/router"
        command = self.home / ".example/commands/run.md"
        self.assertTrue(skill.is_symlink())
        self.assertTrue(command.is_symlink())
        self.assertEqual(command.resolve(), (self.repo / "config/example/commands/run.md").resolve())
        self.assertFalse((self.home / ".example/commands/unused.md").exists())
        self.assertFalse((self.home / ".example/ENTRY.md").exists())

    def test_only_enabled_commands_are_linked(self):
        write_integration(
            self.repo,
            make_integration("example", home_env=["EXAMPLE_HOME"], with_entry=False, commands=[]),
        )

        hub_bootstrap.install(self.repo, "example", self.home)

        self.assertFalse((self.home / ".example/commands").exists())

    def test_missing_command_source_fails(self):
        write_integration(
            self.repo,
            make_integration("example", home_env=["EXAMPLE_HOME"], with_entry=False, commands=["ghost"]),
        )

        with self.assertRaises(SystemExit):
            hub_bootstrap.install(self.repo, "example", self.home)

    def test_install_home_skills_base_still_works_without_entry(self):
        write_integration(
            self.repo,
            make_integration(
                "example",
                base="install_home",
                target_subdir=".shared/skills",
                home_env=["EXAMPLE_HOME"],
                with_entry=False,
            ),
        )

        hub_bootstrap.install(self.repo, "example", self.home)

        self.assertTrue((self.home / ".shared/skills/router").is_symlink())


if __name__ == "__main__":
    unittest.main()
