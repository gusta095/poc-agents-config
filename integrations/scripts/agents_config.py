#!/usr/bin/env python3
"""agents-config: CLI única para conectar e inspecionar as integrações do hub.

Esta ferramenta gerencia só a CONEXÃO entre um consumidor já instalado (por
exemplo, o Cursor) e este repositório, guiada pelo integration.json de cada
integração: symlinks para o arquivo de entrada (opcional), skills, commands e
agentes. Nunca instala, atualiza nem gerencia o consumidor em si; ver
config/README.md para o contrato e os limites ("Fora do escopo").

Comandos:
  plan <consumer>        mostra os links que o connect criaria, sem escrever
  connect <consumer>     cria os links que o integration.json declara
  sync <consumer>        refaz os links a partir do manifesto e remove órfãos
  status                 estado da conexão de cada integração
  doctor                 status mais checagens de ambiente (layout do hub, install home)
  disconnect <consumer>  remove os links criados por esta ferramenta e o recibo
  validate               valida o layout do hub (usa validate_hub_manifest.py)

Um recibo com exatamente os links criados por um `connect` fica em
<install_home>/.agents-config/receipts/<consumer>.json. É estado local de cada
máquina e nunca é versionado (ver "Fronteira de versionamento" em config/README.md).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hub_bootstrap  # noqa: E402
import validate_hub_manifest  # noqa: E402


SCHEMA_VERSION = 1
_OK_STATES = {"ok", "not connected"}


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_install_home() -> Path:
    raw = os.environ.get("AGENTS_CONFIG_INSTALL_HOME")
    return Path(raw).expanduser() if raw else Path.home()


def receipt_path(install_home: Path, consumer: str) -> Path:
    return install_home / ".agents-config" / "receipts" / f"{consumer}.json"


def load_receipt(install_home: Path, consumer: str) -> dict | None:
    path = receipt_path(install_home, consumer)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SystemExit(f"invalid receipt {path}: {error}")
    if not isinstance(data, dict) or not isinstance(data.get("links"), list):
        raise SystemExit(f"invalid receipt {path}: expected an object with a links list")
    return data


def _atomic_write(path: Path, content: bytes) -> None:
    """Substitui um arquivo de estado local de forma atômica, só com o conteúdo completo pronto."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        os.replace(temporary_name, path)
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def _write_receipt(install_home: Path, consumer: str, links: list[tuple[Path, Path]]) -> Path:
    path = receipt_path(install_home, consumer)
    data = {
        "schema_version": SCHEMA_VERSION,
        "consumer": consumer,
        "connected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "links": [{"source": str(source), "target": str(target)} for source, target in links],
    }
    _atomic_write(path, (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode())
    return path


def connect(repo_root: Path, consumer: str, install_home: Path) -> list[str]:
    links = hub_bootstrap.resolve_links(repo_root, consumer, install_home)
    link_plan = hub_bootstrap.plan_links(links)
    conflicts = [message for state, message in link_plan if state == "conflict"]
    if conflicts:
        raise SystemExit("\n".join(conflicts))

    created: list[tuple[Path, Path]] = []
    results: list[str] = []
    try:
        for (source, target), (state, _) in zip(links, link_plan, strict=True):
            results.append(hub_bootstrap.link_one(source, target))
            if state == "create":
                created.append((source, target))
        receipt = _write_receipt(install_home, consumer, links)
    except BaseException:
        for source, target in reversed(created):
            if target.is_symlink() and target.resolve() == source.resolve():
                target.unlink()
        raise
    results.append(f"receipt written: {receipt}")
    return results


def plan(repo_root: Path, consumer: str, install_home: Path) -> list[str]:
    """Descreve um connect sem alterar links nem recibos."""
    links = hub_bootstrap.resolve_links(repo_root, consumer, install_home)
    planned = hub_bootstrap.plan_links(links)
    results = [message for _, message in planned]
    if any(state == "conflict" for state, _ in planned):
        return results
    results.append("plan complete: no changes made")
    return results


def sync(repo_root: Path, consumer: str, install_home: Path) -> list[str]:
    """Refaz os links a partir do manifesto atual e remove os que o recibo anterior
    registrou e o manifesto não declara mais, só se ainda apontarem para onde o recibo diz."""
    previous = load_receipt(install_home, consumer)
    results = connect(repo_root, consumer, install_home)

    if previous is None:
        return results

    current_targets = {link["target"] for link in (load_receipt(install_home, consumer) or {}).get("links", [])}
    for link in previous["links"]:
        if link["target"] in current_targets:
            continue
        target = Path(link["target"])
        source = Path(link["source"])
        if target.is_symlink() and target.resolve() == source.resolve():
            target.unlink()
            results.append(f"removed orphaned {target} (no longer in manifest)")
        else:
            results.append(f"skip orphaned {target} (points elsewhere, not removing)")
    return results


def disconnect(install_home: Path, consumer: str) -> list[str]:
    receipt = load_receipt(install_home, consumer)
    if receipt is None:
        return [f"{consumer}: nothing to disconnect (no receipt)"]

    results: list[str] = []
    for link in receipt["links"]:
        target = Path(link["target"])
        source = Path(link["source"])
        if not target.is_symlink():
            results.append(f"skip {target} (not a symlink anymore)")
            continue
        if target.resolve() != source.resolve():
            results.append(f"skip {target} (points elsewhere now, not removing)")
            continue
        target.unlink()
        results.append(f"removed {target}")

    receipt_path(install_home, consumer).unlink()
    results.append(f"receipt removed for {consumer}")
    return results


def diagnose(repo_root: Path, install_home: Path) -> dict[str, list[str]]:
    """Devolve {consumidor: [problema, ...]} para cada integração em config/.

    Só confere o estado da conexão contra o manifesto, nunca a versão da
    ferramenta do consumidor (ver "Fora do escopo" em config/README.md).
    """
    manifest = hub_bootstrap.load_manifest(repo_root)
    report: dict[str, list[str]] = {}

    for integration in manifest["integrations"]:
        name = integration["name"]
        receipt = load_receipt(install_home, name)

        if receipt is None:
            report[name] = ["not connected"]
            continue

        problems: list[str] = []
        for link in receipt["links"]:
            target = Path(link["target"])
            source = Path(link["source"])
            if not source.exists():
                problems.append(f"source missing: {source} (target {target})")
            elif not target.is_symlink():
                problems.append(f"missing link: {target}")
            elif target.resolve() != source.resolve():
                problems.append(f"drifted: {target} -> {os.readlink(target)} (expected {source})")

        try:
            current_links = hub_bootstrap.resolve_links(repo_root, name, install_home)
            current_targets: set[str] | None = {str(target) for _, target in current_links}
        except SystemExit as error:
            problems.append(f"manifest error: {error}")
            current_targets = None

        if current_targets is not None and current_targets != {link["target"] for link in receipt["links"]}:
            problems.append("manifest changed since last connect — run 'sync'")

        report[name] = problems or ["ok"]

    return report


def status(repo_root: Path, install_home: Path) -> dict[str, list[str]]:
    return diagnose(repo_root, install_home)


def check_environment(repo_root: Path, install_home: Path) -> list[str]:
    """Devolve os problemas que impedem usar o que este hub conecta.

    Cobre só o que o hub gerencia: o layout do hub (as mesmas checagens do
    `validate`) e o install home. Nunca inspeciona a ferramenta do consumidor.
    """
    problems = [f"hub: {error}" for error in validate(repo_root)]

    if not install_home.is_dir():
        problems.append(f"install home does not exist: {install_home}")
    elif not os.access(install_home, os.W_OK):
        problems.append(f"install home is not writable: {install_home}")

    return problems


def doctor(repo_root: Path, install_home: Path) -> dict[str, list[str]]:
    report = diagnose(repo_root, install_home)
    report["environment"] = check_environment(repo_root, install_home) or ["ok"]
    return report


def validate(repo_root: Path) -> list[str]:
    return validate_hub_manifest.validate(repo_root)


def _print_report(report: dict[str, list[str]]) -> int:
    exit_code = 0
    for name, problems in report.items():
        print(f"{name}:")
        for problem in problems:
            print(f"  {problem}")
        if any(problem not in _OK_STATES for problem in problems):
            exit_code = 1
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=default_repo_root())
    parser.add_argument("--install-home", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_connect = subparsers.add_parser("connect", help="link an integration into this machine")
    p_connect.add_argument("consumer")

    p_plan = subparsers.add_parser("plan", help="show what connect would change")
    p_plan.add_argument("consumer")

    p_sync = subparsers.add_parser("sync", help="refresh links after a manifest change")
    p_sync.add_argument("consumer")

    subparsers.add_parser("status", help="show connection state for every integration")
    subparsers.add_parser("doctor", help="diagnose connection problems")

    p_disconnect = subparsers.add_parser("disconnect", help="remove links created by connect")
    p_disconnect.add_argument("consumer")

    subparsers.add_parser("validate", help="validate integration.json files, skills and agents")

    args = parser.parse_args()
    install_home = args.install_home.expanduser() if args.install_home else default_install_home()
    repo_root = args.repo_root.resolve()

    if args.command == "connect":
        for line in connect(repo_root, args.consumer, install_home):
            print(line)
        return 0

    if args.command == "plan":
        lines = plan(repo_root, args.consumer, install_home)
        for line in lines:
            print(line)
        return 1 if any(line.startswith("refusing") or line.startswith("source does not exist") for line in lines) else 0

    if args.command == "sync":
        for line in sync(repo_root, args.consumer, install_home):
            print(line)
        return 0

    if args.command == "status":
        return _print_report(status(repo_root, install_home))

    if args.command == "doctor":
        return _print_report(doctor(repo_root, install_home))

    if args.command == "disconnect":
        for line in disconnect(install_home, args.consumer):
            print(line)
        return 0

    if args.command == "validate":
        errors = validate(repo_root)
        if errors:
            for error in errors:
                print(f"error: {error}", file=sys.stderr)
            return 1
        print("hub validation passed")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
