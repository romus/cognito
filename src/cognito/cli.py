from __future__ import annotations

import argparse
from pathlib import Path
import sys

from cognito.config import ConfigError, create_default_config, load_config
from cognito.engine import Console, run_decode, run_encode
from cognito.fs import is_dangerous_project_path
from cognito import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cognito")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("encode", "decode"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--config", default=None, help="Path to JSON config file.")
        subparser.add_argument("--project", default=".", help="Project root path.")
        subparser.add_argument("--silent", action="store_true", help="Skip project safety confirmation.")
        subparser.add_argument("--dry-run", action="store_true", help="Print planned changes without mutating files.")
    init_parser = subparsers.add_parser("init-config")
    init_parser.add_argument("--config", default=None, help="Path to JSON config file.")
    init_parser.add_argument("--force", action="store_true", help="Overwrite an existing config file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    if args.command == "init-config":
        try:
            path = create_default_config(args.config, force=args.force)
        except ConfigError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        print(f"Created config template at {path}")
        return 0

    project_root = Path(args.project).expanduser().resolve()
    if not project_root.exists() or not project_root.is_dir():
        print(f"ERROR: Project directory does not exist: {project_root}", file=sys.stderr)
        return 2

    if is_dangerous_project_path(project_root) and not args.silent:
        confirmed = input(f"Project path {project_root} is dangerous. Continue? [y/N]: ").strip().lower()
        if confirmed not in {"y", "yes"}:
            print("Aborted.")
            return 1

    console = Console()
    if args.command == "encode":
        try:
            config = load_config(args.config)
        except ConfigError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        report = run_encode(project_root=project_root, config=config, dry_run=args.dry_run, console=console)
    else:
        report = run_decode(project_root=project_root, dry_run=args.dry_run, console=console)
    return report.exit_code
