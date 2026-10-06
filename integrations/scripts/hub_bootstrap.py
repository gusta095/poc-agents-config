#!/usr/bin/env python3
"""Resolve as conexões globais de uma integração, a partir das declarações do hub.

Não existe manifesto central. Cada consumidor se declara em
config/<nome>/integration.json; as skills globais são os diretórios de skills/
que contêm um SKILL.md; os agentes globais (opcionais) são os arquivos
agents/<nome>.md. load_manifest() monta tudo numa estrutura em memória, e todo
link (entrada, skills, commands, agentes) vem só dela.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


INTEGRATION_FILE = "integration.json"


def discover_skills(repo_root: Path) -> list[dict]:
    """Skills globais: todo skills/<nome>/ que contém um SKILL.md."""
    skills_dir = repo_root / "skills"
    if not skills_dir.is_dir():
        return []
    return [
        {"name": path.name, "path": f"skills/{path.name}"}
        for path in sorted(skills_dir.iterdir())
        if (path / "SKILL.md").is_file()
    ]


def discover_agents(repo_root: Path) -> list[dict]:
    """Agentes globais: todo agents/<nome>.md (agents/README.md é documentação)."""
    agents_dir = repo_root / "agents"
    if not agents_dir.is_dir():
        return []
    return [
        {"name": path.stem, "path": f"agents/{path.name}"}
        for path in sorted(agents_dir.glob("*.md"))
        if path.name != "README.md" and not path.name.startswith((".", "_"))
    ]


def integration_files(repo_root: Path) -> list[Path]:
    """Todo config/<nome>/integration.json, ordenado pelo nome do consumidor."""
    config_dir = repo_root / "config"
    if not config_dir.is_dir():
        return []
    return sorted(config_dir.glob(f"*/{INTEGRATION_FILE}"))


def load_integration(config_path: Path) -> dict:
    """Lê um integration.json tornando entry.source e commands.source_dir relativos ao repositório.

    Ambos são escritos relativos ao diretório da própria integração, para que
    a pasta seja autocontida. Um caminho absoluto (após expandir ${VAR}) é
    mantido como está (ver resolve_repo_path).
    """
    integration = json.loads(config_path.read_text(encoding="utf-8"))
    folder = config_path.parent.name
    for section, key in (("entry", "source"), ("commands", "source_dir")):
        block = integration.get(section)
        value = block.get(key) if isinstance(block, dict) else None
        if isinstance(value, str) and value and not Path(os.path.expandvars(value)).is_absolute():
            block[key] = f"config/{folder}/{value}"
    return integration


def load_manifest(repo_root: Path) -> dict:
    return {
        "skills": discover_skills(repo_root),
        "agents": discover_agents(repo_root),
        "integrations": [load_integration(path) for path in integration_files(repo_root)],
    }


def resolve_repo_path(repo_root: Path, raw_path: str) -> Path:
    """Resolve um caminho do manifesto, expandindo $VAR/${VAR} antes.

    Caminho relativo ao repo_root após a expansão é um arquivo deste
    repositório. Caminho absoluto aponta para fora dele.
    """
    expanded = Path(os.path.expandvars(raw_path))
    return expanded if expanded.is_absolute() else repo_root / expanded


def resolve_home(env_names: list[str], default_subdir: str, install_home: Path) -> Path:
    for name in env_names:
        value = os.environ.get(name)
        if value:
            return Path(value).expanduser()
    return install_home / default_subdir


def integration_home(integration: dict, install_home: Path) -> Path:
    """Diretório home do consumidor.

    Vem do bloco `home` quando existe; senão de `entry` (home_env/home_default).
    O validador garante que ao menos um dos dois declara os campos.
    """
    block = integration.get("home") or integration["entry"]
    return resolve_home(block["home_env"], block["home_default"], install_home)


def link_one(source: Path, target: Path) -> str:
    state, message = plan_link(source, target)
    if state == "conflict":
        raise SystemExit(message)
    if state == "ok":
        return message

    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source)
    return f"created {target} -> {source}"


def plan_link(source: Path, target: Path) -> tuple[str, str]:
    """Classifica um link sem alterar o sistema de arquivos."""
    if not source.exists():
        return "conflict", f"source does not exist: {source}"
    if target.is_symlink():
        if target.resolve() == source.resolve():
            return "ok", f"ok {target} -> {source}"
        return "conflict", f"refusing to replace symlink {target} -> {os.readlink(target)}"
    if target.exists():
        return "conflict", f"refusing to replace existing path {target}"
    return "create", f"create {target} -> {source}"


def plan_links(pairs: list[tuple[Path, Path]]) -> list[tuple[str, str]]:
    """Planeja todos os links antes, para que um conflito não deixe instalação parcial."""
    return [plan_link(source, target) for source, target in pairs]


def get_integration(manifest: dict, consumer: str) -> dict:
    integration = next((item for item in manifest["integrations"] if item["name"] == consumer), None)
    if integration is None:
        known = ", ".join(item["name"] for item in manifest["integrations"])
        raise SystemExit(f"unknown integration '{consumer}' (known: {known})")
    return integration


def resolve_links(repo_root: Path, consumer: str, install_home: Path) -> list[tuple[Path, Path]]:
    """Devolve os pares (origem, destino) que o hub declara para um consumidor.

    Compartilhado por install() e por integrations/scripts/agents_config.py,
    para que instalação, status, doctor e sync leiam o manifesto do mesmo jeito.
    """
    manifest = load_manifest(repo_root)
    skills_by_name = {skill["name"]: skill for skill in manifest["skills"]}
    integration = get_integration(manifest, consumer)

    home = integration_home(integration, install_home)
    pairs: list[tuple[Path, Path]] = []

    entry = integration.get("entry")
    if entry:
        pairs.append((resolve_repo_path(repo_root, entry["source"]), home / entry["target_name"]))

    skills_cfg = integration["skills"]
    if skills_cfg["base"] == "install_home":
        skills_base = install_home
    elif skills_cfg["base"] == "entry_home":
        skills_base = home
    else:
        raise SystemExit(f"unknown skills.base '{skills_cfg['base']}' for '{consumer}'")
    skills_target_dir = skills_base / skills_cfg["target_subdir"]

    for name in skills_cfg["names"]:
        skill = skills_by_name.get(name)
        if skill is None:
            raise SystemExit(f"integration '{consumer}' references unknown skill '{name}'")
        pairs.append((resolve_repo_path(repo_root, skill["path"]), skills_target_dir / name))

    commands_cfg = integration.get("commands")
    if commands_cfg:
        suffix = commands_cfg.get("suffix", ".md")
        for name in commands_cfg["names"]:
            source = resolve_repo_path(repo_root, f"{commands_cfg['source_dir']}/{name}{suffix}")
            if "/" in name or ".." in name or not source.is_file():
                raise SystemExit(f"integration '{consumer}' references unknown command '{name}'")
            pairs.append((source, home / commands_cfg["target_subdir"] / f"{name}{suffix}"))

    agents_cfg = integration.get("agents")
    if agents_cfg:
        agents_by_name = {agent["name"]: agent for agent in manifest["agents"]}
        agents_target_dir = home / agents_cfg["target_subdir"]
        source_subdir = agents_cfg.get("source_subdir", "agents")
        source_suffix = agents_cfg.get("source_suffix", ".md")
        target_suffix = agents_cfg.get("target_suffix", source_suffix)
        for name in agents_cfg["names"]:
            if name not in agents_by_name:
                raise SystemExit(f"integration '{consumer}' references unknown agent '{name}'")
            source = resolve_repo_path(repo_root, f"{source_subdir}/{name}{source_suffix}")
            pairs.append((source, agents_target_dir / f"{name}{target_suffix}"))

    return pairs


def install(repo_root: Path, consumer: str, install_home: Path) -> list[str]:
    pairs = resolve_links(repo_root, consumer, install_home)
    planned = plan_links(pairs)
    conflicts = [message for state, message in planned if state == "conflict"]
    if conflicts:
        raise SystemExit("\n".join(conflicts))
    return [link_one(source, target) for source, target in pairs]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("consumer", help="nome da integração (um diretório em config/)")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
    )
    args = parser.parse_args()

    install_home_raw = os.environ.get("AGENTS_CONFIG_INSTALL_HOME")
    install_home = Path(install_home_raw).expanduser() if install_home_raw else Path.home()

    for line in install(args.repo_root.resolve(), args.consumer, install_home):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
