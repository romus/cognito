from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Config:
    words: dict[str, str]
    directory: dict[str, str]
    ignore_dirs: tuple[str, ...]


@dataclass(slots=True)
class ReplaceRecord:
    path: str
    replacements: list[dict[str, str | int]]


@dataclass(slots=True)
class RenameRecord:
    kind: str
    before: str
    after: str


@dataclass(slots=True)
class RunReport:
    command: str
    project_root: str
    dry_run: bool
    file_replacements: list[ReplaceRecord] = field(default_factory=list)
    renames: list[RenameRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return 1 if self.errors else 0
