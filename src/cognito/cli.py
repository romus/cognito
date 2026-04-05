from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .config import ConfigError, create_default_config, load_config
from .engine import Console, run_decode, run_encode
from .fs import is_dangerous_project_path
from . import __version__


def build_parser() -> argparse.ArgumentParser:
    top_level_help = (
        "Commands:\n"
        "  encode       Apply configured text replacements and path renames, then save a manifest.\n"
        "    --config   Path to the JSON config file with replacement rules. Defaults to ~/.config/cognito/config.json.\n"
        "    --project  Path to the project root directory to scan and modify. Defaults to the current working directory.\n"
        "    --silent   Skip the confirmation prompt for dangerous project roots.\n"
        "    --dry-run  Show planned changes without modifying files or writing manifests.\n"
        "\n"
        "  decode       Restore the latest encoded state from the manifest in .cognito.\n"
        "    --config   Accepted for compatibility but not required during decode.\n"
        "    --project  Path to the project root directory to restore. Defaults to the current working directory.\n"
        "    --silent   Skip the confirmation prompt for dangerous project roots.\n"
        "    --dry-run  Show planned restore actions without modifying files.\n"
        "\n"
        "  init-config  Create a starter JSON config template.\n"
        "    --config   Output path for the generated config file. Defaults to ~/.config/cognito/config.json.\n"
        "    --force    Overwrite the target config file if it already exists."
    )
    parser = argparse.ArgumentParser(
        prog="cognito",
        description=(
            "Encode and decode project-specific text and path names so a codebase can be reused "
            "for another project with less manual cleanup."
        ),
        epilog=top_level_help,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("encode", "decode"):
        description = (
            "Apply configured text and path replacements across a project tree and save a manifest for decode."
            if command == "encode"
            else "Restore the latest encoded project state using the manifest stored in .cognito."
        )
        subparser = subparsers.add_parser(
            command,
            help=description,
            description=description,
        )
        subparser.add_argument(
            "--config",
            default=None,
            help=(
                "Path to the JSON config file used to load replacement rules. "
                "For encode, the file must exist and contain the configuration. "
                "For decode, the flag is accepted but not required because restore data is read from the latest "
                "manifest in .cognito. Defaults to ~/.config/cognito/config.json when omitted."
            ),
        )
        subparser.add_argument(
            "--project",
            default=".",
            help=(
                "Path to the project root directory that cognito will scan and modify. "
                "Defaults to the current working directory."
            ),
        )
        subparser.add_argument(
            "--silent",
            action="store_true",
            help=(
                "Skip the confirmation prompt for dangerous project roots such as the home directory or filesystem root."
            ),
        )
        subparser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Show which files and paths would change without modifying files, renaming paths, or writing manifests."
            ),
        )
    init_parser = subparsers.add_parser(
        "init-config",
        help="Create a starter JSON config template.",
        description="Create a starter JSON config template for cognito.",
    )
    init_parser.add_argument(
        "--config",
        default=None,
        help="Output path for the generated JSON config. Defaults to ~/.config/cognito/config.json.",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the target config file if it already exists.",
    )
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
