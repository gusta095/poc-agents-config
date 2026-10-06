from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from hub_fixture import (
    add_agent_lock_entry,
    add_lock_entry,
    make_agent,
    make_command,
    make_integration,
    make_skill,
    read_integration,
    write_integration,
)


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts/validate_hub_manifest.py"
SPEC = importlib.util.spec_from_file_location("validate_hub_manifest", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load {MODULE_PATH}")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

BOOTSTRAP_PATH = ROOT / "scripts/hub_bootstrap.py"
BOOTSTRAP_SPEC = importlib.util.spec_from_file_location("hub_bootstrap_for_manifest", BOOTSTRAP_PATH)
hub_bootstrap = importlib.util.module_from_spec(BOOTSTRAP_SPEC)
BOOTSTRAP_SPEC.loader.exec_module(hub_bootstrap)


class HubValidationTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        make_skill(self.root, "router")
        write_integration(self.root, make_integration("example", base="install_home", target_subdir=".agents/skills"))

    def errors(self) -> list[str]:
        return validator.validate(self.root)

    def assert_error(self, fragment: str) -> None:
        self.assertTrue(any(fragment in error for error in self.errors()), self.errors())

    def test_valid_hub_has_no_errors(self):
        self.assertEqual(self.errors(), [])

    def test_hub_without_integrations_is_reported(self):
        (self.root / "config/example/integration.json").unlink()
        self.assert_error("no integrations found")

    def test_invalid_json_is_reported(self):
        (self.root / "config/example/integration.json").write_text("{not json", encoding="utf-8")
        self.assert_error("is not valid JSON")

    def test_non_object_integration_is_reported_without_crashing(self):
        (self.root / "config/example/integration.json").write_text("[]", encoding="utf-8")
        self.assert_error("top level must be an object")

    def test_non_object_entry_is_reported_without_crashing(self):
        integration = read_integration(self.root, "example")
        integration["entry"] = "invalid"
        write_integration(self.root, integration)
        self.assert_error("entry must be an object")

    def test_unsupported_schema_version_fails(self):
        write_integration(self.root, make_integration("example", schema_version=2))
        self.assert_error("schema_version")

    def test_name_must_match_directory(self):
        integration = read_integration(self.root, "example")
        integration["name"] = "not-example"
        (self.root / "config/example/integration.json").write_text(json.dumps(integration), encoding="utf-8")
        self.assert_error("does not match its directory")

    def test_missing_entry_source_fails(self):
        (self.root / "config/example/ENTRY.md").unlink()
        self.assert_error("entry.source missing")

    def test_integration_referencing_unknown_skill_fails(self):
        integration = read_integration(self.root, "example")
        integration["skills"]["names"].append("ghost-skill")
        write_integration(self.root, integration)
        self.assert_error("unknown skill")

    def test_invalid_skills_base_fails(self):
        integration = read_integration(self.root, "example")
        integration["skills"]["base"] = "somewhere_else"
        write_integration(self.root, integration)
        self.assert_error("skills.base invalid")

    def test_skill_directory_without_skill_md_fails(self):
        (self.root / "skills/orphan").mkdir()
        self.assert_error("skills/orphan has no SKILL.md")

    def test_skill_frontmatter_name_must_match_directory(self):
        make_skill(self.root, "renamed", frontmatter_name="something-else")
        self.assert_error("directory name and the frontmatter name must match")


class HubSkillLockTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        make_skill(self.root, "router")
        make_skill(self.root, "vendored", upstream=True)
        write_integration(self.root, make_integration("example", base="install_home", target_subdir=".agents/skills"))

    def lock(self) -> dict:
        return json.loads((self.root / "skills" / "skills.lock.json").read_text(encoding="utf-8"))

    def write_lock(self, data: dict) -> None:
        (self.root / "skills" / "skills.lock.json").write_text(json.dumps(data), encoding="utf-8")

    def assert_error(self, fragment: str) -> None:
        errors = validator.validate(self.root)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_valid_lock_has_no_errors(self):
        self.assertEqual(validator.validate(self.root), [])

    def test_missing_lock_is_reported(self):
        (self.root / "skills" / "skills.lock.json").unlink()
        self.assert_error("skills.lock.json is missing")

    def test_invalid_json_is_reported(self):
        (self.root / "skills" / "skills.lock.json").write_text("{", encoding="utf-8")
        self.assert_error("skills.lock.json is not valid JSON")

    def test_unsupported_schema_version_fails(self):
        data = self.lock()
        data["schema_version"] = 99
        self.write_lock(data)
        self.assert_error("unsupported schema_version")

    def test_skill_without_entry_fails(self):
        make_skill(self.root, "another", lock=False)
        self.assert_error("skill 'another' has no entry")

    def test_entry_without_skill_directory_fails(self):
        add_lock_entry(self.root, "ghost")
        self.assert_error("entry 'ghost' has no directory")

    def test_invalid_origin_fails(self):
        data = self.lock()
        data["skills"]["vendored"]["origin"] = "unknown"
        self.write_lock(data)
        self.assert_error("'vendored' origin must be one of")

    def test_origin_comes_from_the_lock_not_from_the_name(self):
        add_lock_entry(self.root, "vendored", {"origin": "own"})
        add_lock_entry(self.root, "router", self.lock()["skills"]["vendored"])
        self.assertEqual(validator.validate(self.root), [])

    def test_upstream_needs_https_repo(self):
        data = self.lock()
        data["skills"]["vendored"]["repo"] = None
        self.write_lock(data)
        self.assert_error("'vendored' needs an https 'repo'")

    def test_upstream_missing_key_fails(self):
        data = self.lock()
        del data["skills"]["vendored"]["ref"]
        self.write_lock(data)
        self.assert_error("'vendored' missing 'ref'")

    def test_unknown_values_may_be_null(self):
        data = self.lock()
        for key in ("path", "ref", "fetched", "license"):
            data["skills"]["vendored"][key] = None
        self.write_lock(data)
        self.assertEqual(validator.validate(self.root), [])

    def test_local_changes_must_be_list_of_strings(self):
        data = self.lock()
        data["skills"]["vendored"]["local_changes"] = "not a list"
        self.write_lock(data)
        self.assert_error("'local_changes' must be a list of strings")


class HubLoaderTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_skills_are_discovered_from_skill_md(self):
        make_skill(self.root, "beta")
        make_skill(self.root, "alpha")
        (self.root / "skills/not-a-skill").mkdir()

        self.assertEqual(
            hub_bootstrap.load_manifest(self.root)["skills"],
            [
                {"name": "alpha", "path": "skills/alpha"},
                {"name": "beta", "path": "skills/beta"},
            ],
        )

    def test_integrations_are_discovered_sorted_with_repo_relative_source(self):
        write_integration(self.root, make_integration("zeta"))
        write_integration(self.root, make_integration("alpha"))
        (self.root / "config/template").mkdir()

        integrations = hub_bootstrap.load_manifest(self.root)["integrations"]

        self.assertEqual([item["name"] for item in integrations], ["alpha", "zeta"])
        self.assertEqual(integrations[0]["entry"]["source"], "config/alpha/ENTRY.md")

    def test_absolute_source_is_left_alone(self):
        integration = make_integration("outside")
        integration["entry"]["source"] = "/somewhere/ENTRY.md"
        write_integration(self.root, integration)

        loaded = hub_bootstrap.load_manifest(self.root)["integrations"][0]

        self.assertEqual(loaded["entry"]["source"], "/somewhere/ENTRY.md")

    def test_empty_repo_loads_as_empty(self):
        self.assertEqual(
            hub_bootstrap.load_manifest(self.root),
            {"skills": [], "agents": [], "integrations": []},
        )

    def test_agents_are_discovered_from_markdown_files(self):
        make_agent(self.root, "beta")
        make_agent(self.root, "alpha")
        (self.root / "agents/README.md").write_text("# Agents\n", encoding="utf-8")
        (self.root / "agents/_draft.md").write_text("# Draft\n", encoding="utf-8")
        (self.root / "agents/notes.txt").write_text("not an agent\n", encoding="utf-8")

        self.assertEqual(
            hub_bootstrap.load_manifest(self.root)["agents"],
            [
                {"name": "alpha", "path": "agents/alpha.md"},
                {"name": "beta", "path": "agents/beta.md"},
            ],
        )


class HubAgentValidationTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        make_skill(self.root, "router")
        make_agent(self.root, "helper")
        make_agent(self.root, "vendored", upstream=True)
        write_integration(self.root, make_integration("example", agents=["helper"]))

    def lock(self) -> dict:
        return json.loads((self.root / "agents" / "agents.lock.json").read_text(encoding="utf-8"))

    def write_lock(self, data: dict) -> None:
        (self.root / "agents" / "agents.lock.json").write_text(json.dumps(data), encoding="utf-8")

    def assert_error(self, fragment: str) -> None:
        errors = validator.validate(self.root)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_valid_agents_have_no_errors(self):
        self.assertEqual(validator.validate(self.root), [])

    def test_hub_without_agents_is_still_valid(self):
        for path in (self.root / "agents").iterdir():
            path.unlink()
        write_integration(self.root, make_integration("example"))
        self.assertEqual(validator.validate(self.root), [])

    def test_unknown_agent_reference_is_reported(self):
        write_integration(self.root, make_integration("example", agents=["ghost"]))
        self.assert_error("references unknown agent: ghost")

    def test_integration_agents_needs_target_subdir(self):
        integration = make_integration("example", agents=["helper"])
        del integration["agents"]["target_subdir"]
        write_integration(self.root, integration)
        self.assert_error("missing agents.target_subdir")

    def test_integration_agents_names_must_be_a_list(self):
        integration = make_integration("example", agents=["helper"])
        integration["agents"]["names"] = "helper"
        write_integration(self.root, integration)
        self.assert_error("agents.names must be a list")

    def test_agent_variant_with_another_source_is_validated(self):
        variant = self.root / "agents/alt/helper.txt"
        variant.parent.mkdir(parents=True)
        variant.write_text("variant\n", encoding="utf-8")
        write_integration(
            self.root,
            make_integration(
                "example",
                agents=["helper"],
                agent_source_subdir="agents/alt",
                agent_source_suffix=".txt",
                agent_target_suffix=".txt",
            ),
        )
        self.assertEqual(validator.validate(self.root), [])

    def test_missing_agent_variant_is_reported(self):
        write_integration(
            self.root,
            make_integration(
                "example",
                agents=["helper"],
                agent_source_subdir="agents/alt",
                agent_source_suffix=".txt",
                agent_target_suffix=".txt",
            ),
        )
        self.assert_error("agent source missing")

    def test_agent_frontmatter_name_must_match_file(self):
        make_agent(self.root, "renamed", frontmatter_name="something-else")
        self.assert_error("the file name and the frontmatter name must match")

    def test_agent_without_frontmatter_is_reported(self):
        make_agent(self.root, "bare", frontmatter=False)
        self.assert_error("agent 'bare' has no frontmatter")

    def test_agent_without_description_is_reported(self):
        make_agent(self.root, "silent", description=False)
        self.assert_error("agent 'silent' has no 'description'")

    def test_missing_agents_lock_is_reported(self):
        (self.root / "agents" / "agents.lock.json").unlink()
        self.assert_error("agents.lock.json is missing")

    def test_agent_without_lock_entry_fails(self):
        make_agent(self.root, "another", lock=False)
        self.assert_error("agent 'another' has no entry")

    def test_lock_entry_without_agent_file_fails(self):
        add_agent_lock_entry(self.root, "ghost")
        self.assert_error("entry 'ghost' has no file in agents/")

    def test_agent_origin_comes_from_the_lock_not_from_a_prefix(self):
        upstream_entry = self.lock()["agents"]["vendored"]
        add_agent_lock_entry(self.root, "vendored", {"origin": "own"})
        add_agent_lock_entry(self.root, "helper", upstream_entry)
        self.assertEqual(validator.validate(self.root), [])

    def test_upstream_agent_needs_https_repo(self):
        data = self.lock()
        data["agents"]["vendored"]["repo"] = None
        self.write_lock(data)
        self.assert_error("'vendored' needs an https 'repo'")

    def test_agents_lock_is_independent_from_skills_lock(self):
        add_agent_lock_entry(self.root, "helper", {"origin": "own"})
        (self.root / "agents" / "agents.lock.json").unlink()
        self.assert_error("agents.lock.json is missing")
        self.assertFalse(any("skills.lock.json" in error for error in validator.validate(self.root)))


class HubEntrylessAndCommandsTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        make_skill(self.root, "router")
        make_skill(self.root, "extra")
        make_command(self.root, "example", "run")
        make_command(self.root, "example", "other")
        self.write(make_integration("example", with_entry=False, commands=["run"]))

    def write(self, integration: dict) -> None:
        write_integration(self.root, integration)

    def assert_error(self, fragment: str) -> None:
        errors = validator.validate(self.root)
        self.assertTrue(any(fragment in error for error in errors), errors)

    def test_integration_without_entry_is_valid(self):
        self.assertEqual(validator.validate(self.root), [])

    def test_integration_needs_home_or_entry(self):
        integration = make_integration("example", with_entry=False)
        del integration["home"]
        self.write(integration)
        self.assert_error("needs 'home' or 'entry'")

    def test_home_env_must_be_a_list(self):
        integration = make_integration("example", with_entry=False)
        integration["home"]["home_env"] = "EXAMPLE_HOME"
        self.write(integration)
        self.assert_error("home.home_env must be a list")

    def test_entry_still_requires_target_name(self):
        integration = make_integration("example")
        del integration["entry"]["target_name"]
        self.write(integration)
        self.assert_error("missing entry.target_name")

    def test_entry_without_home_fields_is_reported(self):
        integration = make_integration("example")
        del integration["entry"]["home_default"]
        self.write(integration)
        self.assert_error("missing entry.home_default")

    def test_unknown_command_is_reported(self):
        self.write(make_integration("example", with_entry=False, commands=["ghost"]))
        self.assert_error("command source missing: ghost.md")

    def test_commands_need_source_dir_and_target_subdir(self):
        integration = make_integration("example", with_entry=False, commands=["run"])
        del integration["commands"]["source_dir"]
        del integration["commands"]["target_subdir"]
        self.write(integration)
        self.assert_error("missing commands.source_dir")
        self.assert_error("missing commands.target_subdir")

    def test_disabled_items_are_validated(self):
        integration = make_integration("example", with_entry=False, skills=["router"], commands=["run"])
        integration["skills"]["disabled"] = ["extra"]
        integration["commands"]["disabled"] = ["other"]
        self.write(integration)
        self.assertEqual(validator.validate(self.root), [])

    def test_disabled_unknown_item_is_reported(self):
        integration = make_integration("example", with_entry=False)
        integration["skills"]["disabled"] = ["ghost"]
        self.write(integration)
        self.assert_error("skills.disabled references unknown item: ghost")

    def test_item_cannot_be_enabled_and_disabled(self):
        integration = make_integration("example", with_entry=False, commands=["run"])
        integration["commands"]["disabled"] = ["run"]
        self.write(integration)
        self.assert_error("'run' is both enabled and disabled")

    def test_disabled_must_be_a_list(self):
        integration = make_integration("example", with_entry=False)
        integration["skills"]["disabled"] = "extra"
        self.write(integration)
        self.assert_error("skills.disabled must be a list")


if __name__ == "__main__":
    unittest.main()
