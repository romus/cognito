from __future__ import annotations

import os
from pathlib import Path
from typing import NamedTuple

FORCED_TEXT_EXTENSIONS = frozenset({".patch", ".diff"})


class TextFileInfo(NamedTuple):
    is_text: bool
    used_patch_fallback: bool


def is_dangerous_project_path(path: Path) -> bool:
    resolved = path.expanduser().resolve()
    root = resolved.anchor
    home = Path.home().resolve()
    return resolved == home or str(resolved) == root


def ensure_directory(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)


def is_probably_text_by_extension(path: Path) -> bool:
    return path.suffix.lower() in FORCED_TEXT_EXTENSIONS


def inspect_text_file(path: Path) -> TextFileInfo:
    try:
        with path.open("rb") as handle:
            sample = handle.read(8192)
    except OSError:
        return TextFileInfo(is_text=False, used_patch_fallback=False)

    if b"\x00" in sample:
        return TextFileInfo(is_text=False, used_patch_fallback=False)
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        forced_text = is_probably_text_by_extension(path)
        return TextFileInfo(is_text=forced_text, used_patch_fallback=forced_text)
    return TextFileInfo(is_text=True, used_patch_fallback=False)


def iter_project_files(project_root: Path, ignore_dirs: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    ignored = set(ignore_dirs)
    for current_root, dirs, filenames in os.walk(project_root):
        current_root = Path(current_root)
        dirs[:] = [name for name in dirs if name not in ignored]
        for filename in filenames:
            files.append(current_root / filename)
    return files


def iter_project_dirs(project_root: Path, ignore_dirs: tuple[str, ...]) -> list[Path]:
    dirs_out: list[Path] = []
    ignored = set(ignore_dirs)
    for current_root, dirs, _ in os.walk(project_root):
        current_root = Path(current_root)
        dirs[:] = [name for name in dirs if name not in ignored]
        for dirname in dirs:
            dirs_out.append(current_root / dirname)
    return dirs_out
