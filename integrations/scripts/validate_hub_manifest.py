#!/usr/bin/env python3
"""Valida o hub: integration.json, skills e agentes globais, seus lock files e as referências entre eles."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hub_bootstrap import (  # noqa: E402
    INTEGRATION_FILE,
    discover_agents,
    discover_skills,
    integration_files,
    load_integration,
    resolve_repo_path,
)

SCHEMA_VERSION = 1
LOCK_FILE = "skills/skills.lock.json"
AGENTS_LOCK_FILE = "agents/agents.lock.json"
VALID_ORIGINS = ("own", "upstream")
UPSTREAM_KEYS = ("repo", "path", "ref", "fetched", "license", "local_changes", "notes")
VALID_SKILLS_BASE = ("install_home", "entry_home")
FRONTMATTER_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
FRONTMATTER_DESCRIPTION_RE = re.compile(r"^description:\s*\S", re.MULTILINE)


def _validate_skills(repo_root: Path) -> tuple[set[str], list[str]]:
    errors: list[str] = []
    skills_dir = repo_root / "skills"
    if skills_dir.is_dir():
        for path in sorted(skills_dir.iterdir()):
            if path.is_dir() and not path.name.startswith((".", "_")) and not (path / "SKILL.md").is_file():
                errors.append(f"skills/{path.name} has no SKILL.md")

    names: set[str] = set()
    for skill in discover_skills(repo_root):
        names.add(skill["name"])
        head = (repo_root / skill["path"] / "SKILL.md").read_text(encoding="utf-8").split("---")
        match = FRONTMATTER_NAME_RE.search(head[1]) if len(head) > 2 else None
        if match and match.group(1) != skill["name"]:
            errors.append(
                f"skill '{skill['name']}' declares name '{match.group(1)}' in SKILL.md; "
                "the directory name and the frontmatter name must match"
            )
    return names, errors


def _validate_lock(
    repo_root: Path,
    names: set[str],
    *,
    lock_file: str = LOCK_FILE,
    key: str = "skills",
    kind: str = "skill",
    where: str = "directory in skills/",
) -> list[str]:
    """Confere um lock file: uma entrada por skill/agente e os campos de proveniência.

    A origem (own ou upstream) vem só do lock, nunca do nome. Sem itens e sem
    lock file, nada a validar (agents/ é opcional).
    """
    lock_path = repo_root / lock_file
    if not names and not lock_path.exists():
        return []
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except OSError:
        return [f"{lock_file} is missing: every {kind} needs an entry"]
    except ValueError as error:
        return [f"{lock_file} is not valid JSON: {error}"]

    errors: list[str] = []
    if lock.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"{lock_file} unsupported schema_version: {lock.get('schema_version')!r}")
    entries = lock.get(key)
    if not isinstance(entries, dict):
        return errors + [f"{lock_file} '{key}' must be an object"]

    for name in sorted(names - entries.keys()):
        errors.append(f"{kind} '{name}' has no entry in {lock_file}")
    for name in sorted(entries.keys() - names):
        errors.append(f"{lock_file} entry '{name}' has no {where}")

    for name in sorted(entries.keys() & names):
        entry = entries[name]
        if not isinstance(entry, dict) or entry.get("origin") not in VALID_ORIGINS:
            errors.append(f"{lock_file} '{name}' origin must be one of {VALID_ORIGINS}")
            continue
        if entry["origin"] == "own":
            continue
        repo = entry.get("repo")
        if not (isinstance(repo, str) and repo.startswith("https://")):
            errors.append(f"{lock_file} '{name}' needs an https 'repo'")
        for field in UPSTREAM_KEYS:
            if field not in entry:
                errors.append(f"{lock_file} '{name}' missing '{field}' (use null when unknown)")
        for field in ("local_changes", "notes"):
            value = entry.get(field, [])
            if not (isinstance(value, list) and all(isinstance(item, str) for item in value)):
                errors.append(f"{lock_file} '{name}' '{field}' must be a list of strings")
    return errors


def _validate_agents(repo_root: Path) -> tuple[set[str], list[str]]:
    """Confere agents/<nome>.md: frontmatter com name igual ao arquivo e uma description."""
    errors: list[str] = []
    names: set[str] = set()
    for agent in discover_agents(repo_root):
        names.add(agent["name"])
        parts = (repo_root / agent["path"]).read_text(encoding="utf-8").split("---")
        head = parts[1] if len(parts) > 2 and not parts[0].strip() else None
        if head is None:
            errors.append(f"agent '{agent['name']}' has no frontmatter")
            continue
        match = FRONTMATTER_NAME_RE.search(head)
        if not match:
            errors.append(f"agent '{agent['name']}' has no 'name' in its frontmatter")
        elif match.group(1) != agent["name"]:
            errors.append(
                f"agent '{agent['name']}' declares name '{match.group(1)}'; "
                "the file name and the frontmatter name must match"
            )
        if not FRONTMATTER_DESCRIPTION_RE.search(head):
            errors.append(f"agent '{agent['name']}' has no 'description' in its frontmatter")
    return names, errors


def _check_home(iname: str, block: object, label: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(block, dict) or not isinstance(block.get("home_env"), list):
        return [f"integration '{iname}' {label}.home_env must be a list"]
    if not block.get("home_default"):
        errors.append(f"integration '{iname}' missing {label}.home_default")
    return errors


def _check_enabled_disabled(iname: str, label: str, cfg: dict, known: set[str]) -> list[str]:
    """names (habilitados) e disabled (desabilitados de propósito) são listas, sem sobreposição."""
    errors: list[str] = []
    names = cfg.get("names")
    disabled = cfg.get("disabled", [])
    if not isinstance(names, list):
        errors.append(f"integration '{iname}' {label}.names must be a list")
        names = []
    if not isinstance(disabled, list):
        errors.append(f"integration '{iname}' {label}.disabled must be a list")
        disabled = []
    for name in disabled:
        if name not in known:
            errors.append(f"integration '{iname}' {label}.disabled references unknown item: {name}")
        if name in names:
            errors.append(f"integration '{iname}' {label}: '{name}' is both enabled and disabled")
    return errors


def _validate_integration(
    repo_root: Path, config_path: Path, skill_names: set[str], agent_names: set[str]
) -> list[str]:
    errors: list[str] = []
    folder = config_path.parent.name
    try:
        integration = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"config/{folder}/{INTEGRATION_FILE} is not valid JSON: {error}"]

    if not isinstance(integration, dict):
        return [f"config/{folder}/{INTEGRATION_FILE} top level must be an object"]

    if integration.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"integration '{folder}' unsupported schema_version: {integration.get('schema_version')!r}"
        )

    iname = integration.get("name")
    if not iname:
        return errors + [f"integration '{folder}' missing 'name'"]
    if iname != folder:
        errors.append(f"integration name '{iname}' does not match its directory '{folder}'")

    # Home do consumidor: bloco `home` ou, na falta dele, o `entry`.
    entry = integration.get("entry")
    home = integration.get("home")
    if "entry" in integration and not isinstance(entry, dict):
        return errors + [f"integration '{iname}' entry must be an object"]
    if "home" in integration and not isinstance(home, dict):
        return errors + [f"integration '{iname}' home must be an object"]
    if home is None and entry is None:
        errors.append(f"integration '{iname}' needs 'home' or 'entry' to locate the consumer home")
    elif home is not None:
        errors.extend(_check_home(iname, home, "home"))

    if entry is not None:
        source = entry.get("source")
        if not source or not resolve_repo_path(repo_root, load_integration(config_path)["entry"]["source"]).is_file():
            errors.append(f"integration '{iname}' entry.source missing: {source}")
        if not entry.get("target_name"):
            errors.append(f"integration '{iname}' missing entry.target_name")
        if home is None:
            errors.extend(_check_home(iname, entry, "entry"))

    skills_cfg = integration.get("skills", {})
    if not isinstance(skills_cfg, dict):
        return errors + [f"integration '{iname}' skills must be an object"]
    if skills_cfg.get("base") not in VALID_SKILLS_BASE:
        errors.append(f"integration '{iname}' skills.base invalid: {skills_cfg.get('base')!r}")
    if not skills_cfg.get("target_subdir"):
        errors.append(f"integration '{iname}' missing skills.target_subdir")
    for name in skills_cfg.get("names", []):
        if name not in skill_names:
            errors.append(f"integration '{iname}' references unknown skill: {name}")
    errors.extend(_check_enabled_disabled(iname, "skills", skills_cfg, skill_names))

    if "commands" in integration:
        commands_cfg = integration["commands"]
        if not isinstance(commands_cfg, dict):
            errors.append(f"integration '{iname}' commands must be an object")
            commands_cfg = {}
        if not commands_cfg.get("source_dir"):
            errors.append(f"integration '{iname}' missing commands.source_dir")
        if not commands_cfg.get("target_subdir"):
            errors.append(f"integration '{iname}' missing commands.target_subdir")
        suffix = commands_cfg.get("suffix", ".md")
        if not isinstance(suffix, str) or not suffix.startswith("."):
            errors.append(f"integration '{iname}' commands.suffix must start with '.'")
            suffix = ".md"
        known_commands: set[str] = set()
        source_dir = commands_cfg.get("source_dir")
        if isinstance(source_dir, str) and source_dir:
            resolved_dir = resolve_repo_path(
                repo_root, load_integration(config_path)["commands"]["source_dir"]
            )
            if resolved_dir.is_dir():
                known_commands = {p.name[: -len(suffix)] for p in resolved_dir.glob(f"*{suffix}")}
        names = commands_cfg.get("names", [])
        if isinstance(names, list):
            for name in names:
                if name not in known_commands:
                    errors.append(f"integration '{iname}' command source missing: {name}{suffix}")
        errors.extend(_check_enabled_disabled(iname, "commands", commands_cfg, known_commands))

    if "agents" in integration:
        agents_cfg = integration["agents"]
        if not isinstance(agents_cfg, dict):
            errors.append(f"integration '{iname}' agents must be an object")
            agents_cfg = {}
        if not agents_cfg.get("target_subdir"):
            errors.append(f"integration '{iname}' missing agents.target_subdir")
        source_subdir = agents_cfg.get("source_subdir", "agents")
        source_suffix = agents_cfg.get("source_suffix", ".md")
        target_suffix = agents_cfg.get("target_suffix", source_suffix)
        if not isinstance(source_subdir, str) or not source_subdir:
            errors.append(f"integration '{iname}' agents.source_subdir must be a non-empty string")
        if not isinstance(source_suffix, str) or not source_suffix.startswith("."):
            errors.append(f"integration '{iname}' agents.source_suffix must start with '.'")
        if not isinstance(target_suffix, str) or not target_suffix.startswith("."):
            errors.append(f"integration '{iname}' agents.target_suffix must start with '.'")
        errors.extend(_check_enabled_disabled(iname, "agents", agents_cfg, agent_names))
        names = agents_cfg.get("names", []) if isinstance(agents_cfg.get("names"), list) else []
        for name in names:
            if name not in agent_names:
                errors.append(f"integration '{iname}' references unknown agent: {name}")
                continue
            if not (isinstance(source_subdir, str) and isinstance(source_suffix, str)):
                continue
            source_path = resolve_repo_path(repo_root, f"{source_subdir}/{name}{source_suffix}")
            if not source_path.is_file():
                errors.append(f"integration '{iname}' agent source missing: {source_path}")

    return errors


def validate(repo_root: Path) -> list[str]:
    skill_names, errors = _validate_skills(repo_root)
    errors.extend(_validate_lock(repo_root, skill_names))
    agent_names, agent_errors = _validate_agents(repo_root)
    errors.extend(agent_errors)
    errors.extend(
        _validate_lock(
            repo_root,
            agent_names,
            lock_file=AGENTS_LOCK_FILE,
            key="agents",
            kind="agent",
            where="file in agents/",
        )
    )

    configs = integration_files(repo_root)
    if not configs:
        errors.append(f"no integrations found: expected config/<name>/{INTEGRATION_FILE}")
    for config_path in configs:
        errors.extend(_validate_integration(repo_root, config_path, skill_names, agent_names))

    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    errors = validate(repo_root)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print("hub validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
