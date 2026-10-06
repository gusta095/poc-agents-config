"""Monta em disco o layout do hub (skills/, agents/ e config/<nome>/) para os testes."""

from __future__ import annotations

import json
from pathlib import Path


def upstream_entry(name: str) -> dict:
    return {
        "origin": "upstream",
        "repo": f"https://github.com/owner/{name}",
        "path": None,
        "ref": None,
        "fetched": None,
        "license": None,
        "local_changes": [],
        "notes": [],
    }


def make_skill(
    repo: Path, name: str, *, frontmatter_name: str | None = None, lock: bool = True, upstream: bool = False
) -> None:
    skill_dir = repo / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {frontmatter_name or name}\n---\n# {name}\n", encoding="utf-8"
    )
    if lock:
        add_lock_entry(repo, name, upstream=upstream)


def add_lock_entry(repo: Path, name: str, entry: dict | None = None, *, upstream: bool = False) -> None:
    """Registra uma skill em skills/skills.lock.json: própria, salvo upstream=True."""
    path = repo / "skills" / "skills.lock.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema_version": 1, "skills": {}}
    if entry is None:
        entry = upstream_entry(name) if upstream else {"origin": "own"}
    data["skills"][name] = entry
    path.write_text(json.dumps(data), encoding="utf-8")


def make_agent(
    repo: Path,
    name: str,
    *,
    frontmatter_name: str | None = None,
    description: bool = True,
    frontmatter: bool = True,
    lock: bool = True,
    upstream: bool = False,
) -> None:
    agents_dir = repo / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    head = f"---\nname: {frontmatter_name or name}\n"
    if description:
        head += f"description: Agent {name}.\n"
    head += "model: haiku\n---\n"
    (agents_dir / f"{name}.md").write_text(
        (head if frontmatter else "") + f"# {name}\n", encoding="utf-8"
    )
    if lock:
        add_agent_lock_entry(repo, name, upstream=upstream)


def add_agent_lock_entry(
    repo: Path, name: str, entry: dict | None = None, *, upstream: bool = False
) -> None:
    """Registra um agente em agents/agents.lock.json: próprio, salvo upstream=True."""
    path = repo / "agents" / "agents.lock.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema_version": 1, "agents": {}}
    if entry is None:
        entry = upstream_entry(name) if upstream else {"origin": "own"}
    data["agents"][name] = entry
    path.write_text(json.dumps(data), encoding="utf-8")


def make_command(repo: Path, consumer: str, name: str, *, source_dir: str = "commands") -> None:
    folder = repo / "config" / consumer / source_dir
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name}.md").write_text(f"# {name}\n", encoding="utf-8")


def make_integration(
    name: str,
    *,
    base: str = "entry_home",
    skills: list[str] | None = None,
    home_env: list[str] | None = None,
    target_subdir: str = "skills",
    schema_version: int = 1,
    agents: list[str] | None = None,
    agent_source_subdir: str | None = None,
    agent_source_suffix: str | None = None,
    agent_target_suffix: str | None = None,
    commands: list[str] | None = None,
    with_entry: bool = True,
) -> dict:
    """Integração de teste. Sem `with_entry`, o home vem do bloco `home` e não há arquivo de entrada."""
    home = {
        "home_env": home_env if home_env is not None else [f"{name.upper().replace('-', '_')}_HOME"],
        "home_default": f".{name}",
    }
    integration: dict = {"schema_version": schema_version, "name": name}
    if with_entry:
        integration["entry"] = {"source": "ENTRY.md", "target_name": "ENTRY.md", **home}
    else:
        integration["home"] = home
    integration["skills"] = {
        "base": base,
        "target_subdir": target_subdir,
        "names": ["router"] if skills is None else skills,
    }
    if commands is not None:
        integration["commands"] = {"source_dir": "commands", "target_subdir": "commands", "names": commands}
    if agents is not None:
        integration["agents"] = {"target_subdir": "agents", "names": agents}
        if agent_source_subdir is not None:
            integration["agents"]["source_subdir"] = agent_source_subdir
        if agent_source_suffix is not None:
            integration["agents"]["source_suffix"] = agent_source_suffix
        if agent_target_suffix is not None:
            integration["agents"]["target_suffix"] = agent_target_suffix
    return integration


def write_integration(repo: Path, integration: dict, *, with_entry: bool = True) -> None:
    folder = repo / "config" / integration["name"]
    folder.mkdir(parents=True, exist_ok=True)
    if with_entry and "entry" in integration:
        (folder / "ENTRY.md").write_text("# Entry\n", encoding="utf-8")
    (folder / "integration.json").write_text(json.dumps(integration), encoding="utf-8")


def read_integration(repo: Path, name: str) -> dict:
    return json.loads((repo / "config" / name / "integration.json").read_text(encoding="utf-8"))
