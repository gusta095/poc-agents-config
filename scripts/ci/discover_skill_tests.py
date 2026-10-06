#!/usr/bin/env python3
"""Descobre automaticamente as suítes executáveis das skills."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path


IGNORED_PARTS = {"__pycache__", ".git", ".venv", "tests"}


def has_python_code(skill_dir: Path) -> bool:
    """Retorna True quando a skill possui Python fora da suíte de testes."""
    return any(
        not IGNORED_PARTS.intersection(path.relative_to(skill_dir).parts)
        for path in skill_dir.rglob("*.py")
    )


def has_unit_tests(skill_dir: Path) -> bool:
    """Retorna True quando a skill possui ao menos um test_*.py."""
    tests_dir = skill_dir / "tests"
    return tests_dir.is_dir() and any(tests_dir.rglob("test_*.py"))


def requirements_file(skill_dir: Path) -> str:
    """Retorna o tests/requirements.txt da skill, ou vazio quando não existe."""
    path = skill_dir / "tests" / "requirements.txt"
    return path.as_posix() if path.is_file() else ""


def discover_suites(skills_dir: Path) -> list[dict[str, str]]:
    """Lista as suítes de toda skill declarada que contém Python.

    Cada suíte informa o `requirements_file` da skill (vazio quando ela não
    declara dependências).
    """
    suites: list[dict[str, str]] = []

    if not skills_dir.is_dir():
        raise FileNotFoundError(f"diretório de skills não encontrado: {skills_dir}")

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir() or not (skill_dir / "SKILL.md").is_file():
            continue
        if not has_python_code(skill_dir):
            continue

        relative_skill = skill_dir.as_posix()
        requirements = requirements_file(skill_dir)
        if has_unit_tests(skill_dir):
            test_path = (skill_dir / "tests").as_posix()
            suites.append(
                {
                    "name": skill_dir.name,
                    "mode": "unit",
                    "command": f"python3 -m unittest discover -s {test_path}",
                    "requirements_file": requirements,
                }
            )
        else:
            suites.append(
                {
                    "name": skill_dir.name,
                    "mode": "syntax",
                    "command": f"python3 -m compileall -q {relative_skill}",
                    "requirements_file": requirements,
                }
            )

    return suites


def run_suites(suites: list[dict[str, str]]) -> int:
    """Executa localmente as suítes descobertas."""
    failed = False
    for suite in suites:
        print(f"\n==> {suite['name']} ({suite['mode']})", flush=True)
        result = subprocess.run(shlex.split(suite["command"]), check=False)
        failed = failed or result.returncode != 0
    return 1 if failed else 0


def parse_args() -> argparse.Namespace:
    """Lê os argumentos da CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skills-dir",
        type=Path,
        default=Path("skills"),
        help="diretório que contém as skills (default: skills)",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="executa localmente as suítes descobertas",
    )
    return parser.parse_args()


def main() -> int:
    """Executa a descoberta e imprime a lista de suítes."""
    args = parse_args()
    suites = discover_suites(args.skills_dir)

    if args.run:
        return run_suites(suites)

    print(json.dumps({"include": suites}, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
