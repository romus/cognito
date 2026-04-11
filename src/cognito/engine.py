from __future__ import annotations

from pathlib import Path

from .fs import ensure_directory, inspect_text_file, iter_project_dirs, iter_project_files
from .models import Config, RenameRecord, ReplaceRecord, RunReport
from .text import replace_case_insensitive


class Console:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def info(self, message: str) -> None:
        print(message)
        self.lines.append(message)

    def warning(self, message: str) -> None:
        line = f"WARNING: {message}"
        print(line)
        self.lines.append(line)

    def error(self, message: str) -> None:
        line = f"ERROR: {message}"
        print(line)
        self.lines.append(line)


def run_encode(project_root: Path, config: Config, dry_run: bool, console: Console) -> RunReport:
    report = RunReport(command="encode", project_root=str(project_root), dry_run=dry_run)
    _apply_text_replacements(project_root, config, dry_run, report, console)
    _apply_renames(project_root, config, dry_run, report, console)
    return report


def run_decode(project_root: Path, config: Config, dry_run: bool, console: Console) -> RunReport:
    report = RunReport(command="decode", project_root=str(project_root), dry_run=dry_run)
    reverse_config = _reverse_config(config, report, console)
    if reverse_config is None:
        return report

    _apply_text_replacements(project_root, reverse_config, dry_run, report, console)
    _apply_renames(project_root, reverse_config, dry_run, report, console)
    return report


def _reverse_config(config: Config, report: RunReport, console: Console) -> Config | None:
    words = _reverse_mapping(config.words, "words", report, console)
    directory = _reverse_mapping(config.directory, "directory", report, console)
    if report.errors:
        return None
    return Config(words=words, directory=directory, ignore_dirs=config.ignore_dirs)


def _reverse_mapping(
    mapping: dict[str, str],
    field_name: str,
    report: RunReport,
    console: Console,
) -> dict[str, str]:
    reverse: dict[str, str] = {}
    for source, target in mapping.items():
        if not target:
            _record_error(
                report,
                console,
                f"Config field '{field_name}' cannot be decoded because '{source}' maps to an empty value.",
            )
            continue
        if field_name == "directory" and not _path_mapping_parts(target):
            _record_error(
                report,
                console,
                f"Config field '{field_name}' cannot be decoded because '{source}' maps to an empty path.",
            )
            continue
        existing = reverse.get(target)
        if existing is not None and existing != source:
            _record_error(
                report,
                console,
                f"Config field '{field_name}' has ambiguous reverse mapping for '{target}': '{existing}' and '{source}'.",
            )
            continue
        reverse[target] = source
    return reverse


def _apply_text_replacements(
    project_root: Path,
    config: Config,
    dry_run: bool,
    report: RunReport,
    console: Console,
) -> None:
    if not config.words:
        return
    for path in iter_project_files(project_root, config.ignore_dirs):
        text_info = inspect_text_file(path)
        if not text_info.is_text:
            continue
        rel_path = str(path.relative_to(project_root))
        if text_info.used_patch_fallback:
            message = f"Processing patch-like file with non-UTF-8 bytes via surrogateescape: {rel_path}"
            report.warnings.append(message)
            console.warning(message)
        original = _read_text_candidate(path, rel_path, text_info.used_patch_fallback, report, console)
        if original is None:
            continue
        updated, operations = replace_case_insensitive(original, config.words)
        if not operations:
            continue
        if dry_run:
            report.file_replacements.append(ReplaceRecord(path=rel_path, replacements=operations))
            console.info(f"Would update file: {rel_path}")
            continue
        if _write_text_candidate(path, rel_path, updated, text_info.used_patch_fallback, report, console):
            report.file_replacements.append(ReplaceRecord(path=rel_path, replacements=operations))
            console.info(f"Updated file: {rel_path}")


def _apply_renames(
    project_root: Path,
    config: Config,
    dry_run: bool,
    report: RunReport,
    console: Console,
) -> None:
    if not config.directory:
        return

    dir_operations = _plan_directory_renames(project_root, config)
    for before, after in dir_operations:
        _execute_rename(project_root, before, after, "directory", dry_run, report, console)

    file_operations = _plan_file_renames(project_root, config)
    for before, after in file_operations:
        _execute_rename(project_root, before, after, "file", dry_run, report, console)


def _plan_directory_renames(project_root: Path, config: Config) -> list[tuple[Path, Path]]:
    candidates: list[tuple[Path, Path]] = []
    for path in iter_project_dirs(project_root, config.ignore_dirs):
        rel_parts = path.relative_to(project_root).parts
        new_parts = _transform_parts(rel_parts, config.directory)
        if new_parts != rel_parts:
            candidates.append((path, project_root.joinpath(*new_parts)))

    candidates.sort(key=lambda item: len(item[0].relative_to(project_root).parts))
    selected: list[tuple[Path, Path]] = []
    selected_sources: list[Path] = []
    for before, after in candidates:
        if any(_is_relative_to(before, parent) for parent in selected_sources):
            continue
        selected.append((before, after))
        selected_sources.append(before)
    return selected


def _plan_file_renames(project_root: Path, config: Config) -> list[tuple[Path, Path]]:
    operations: list[tuple[Path, Path]] = []
    for path in iter_project_files(project_root, config.ignore_dirs):
        rel_parts = path.relative_to(project_root).parts
        new_parts = _transform_parts(rel_parts, config.directory)
        if new_parts != rel_parts:
            operations.append((path, project_root.joinpath(*new_parts)))
    operations.sort(key=lambda item: len(item[0].relative_to(project_root).parts))
    return operations


def _transform_parts(parts: tuple[str, ...], mapping: dict[str, str]) -> tuple[str, ...]:
    output = list(parts)
    for source, target in mapping.items():
        source_parts = _path_mapping_parts(source)
        target_parts = _path_mapping_parts(target)
        if not source_parts:
            continue
        output = _replace_parts(output, list(source_parts), list(target_parts))
    return tuple(output)


def _path_mapping_parts(value: str) -> tuple[str, ...]:
    return tuple(part for part in Path(value).parts if part not in ("/", "\\"))


def _replace_parts(parts: list[str], source_parts: list[str], target_parts: list[str]) -> list[str]:
    result: list[str] = []
    index = 0
    width = len(source_parts)
    while index < len(parts):
        if parts[index : index + width] == source_parts:
            result.extend(target_parts)
            index += width
            continue
        result.append(parts[index])
        index += 1
    return result


def _execute_rename(
    project_root: Path,
    before: Path,
    after: Path,
    kind: str,
    dry_run: bool,
    report: RunReport,
    console: Console,
) -> None:
    before_rel = str(before.relative_to(project_root))
    after_rel = str(after.relative_to(project_root))
    if dry_run:
        report.renames.append(RenameRecord(kind=kind, before=before_rel, after=after_rel))
        console.info(f"Would rename {kind}: {before_rel} -> {after_rel}")
        return
    try:
        ensure_directory(after.parent, dry_run=False)
        before.rename(after)
        _prune_empty_parents(before.parent, project_root)
        report.renames.append(RenameRecord(kind=kind, before=before_rel, after=after_rel))
        console.info(f"Renamed {kind}: {before_rel} -> {after_rel}")
    except OSError as exc:
        _record_error(report, console, f"Failed to rename {before_rel} -> {after_rel}: {exc}")


def _record_error(report: RunReport, console: Console, message: str) -> None:
    report.errors.append(message)
    console.error(message)


def _read_text_candidate(
    path: Path,
    rel_path: str,
    use_surrogateescape: bool,
    report: RunReport,
    console: Console,
) -> str | None:
    read_kwargs: dict[str, str] = {"encoding": "utf-8"}
    if use_surrogateescape:
        read_kwargs["errors"] = "surrogateescape"
    try:
        return path.read_text(**read_kwargs)
    except (OSError, UnicodeDecodeError) as exc:
        _record_error(report, console, f"Failed to read {rel_path}: {exc}")
        return None


def _write_text_candidate(
    path: Path,
    rel_path: str,
    content: str,
    use_surrogateescape: bool,
    report: RunReport,
    console: Console,
) -> bool:
    write_kwargs: dict[str, str] = {"encoding": "utf-8"}
    if use_surrogateescape:
        write_kwargs["errors"] = "surrogateescape"
    try:
        path.write_text(content, **write_kwargs)
        return True
    except (OSError, UnicodeEncodeError) as exc:
        _record_error(report, console, f"Failed to write {rel_path}: {exc}")
        return False


def _is_relative_to(path: Path, other: Path) -> bool:
    try:
        path.relative_to(other)
        return True
    except ValueError:
        return False


def _prune_empty_parents(start: Path, project_root: Path) -> None:
    current = start
    while current != project_root and _is_relative_to(current, project_root):
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent
