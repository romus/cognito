from __future__ import annotations

from pathlib import Path

from cognito.fs import (
    ensure_directory,
    inspect_text_file,
    is_dangerous_project_path,
    is_probably_text_by_extension,
    iter_project_dirs,
    iter_project_files,
)


def test_is_dangerous_project_path_home(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert is_dangerous_project_path(tmp_path) is True


def test_is_dangerous_project_path_root():
    assert is_dangerous_project_path(Path("/")) is True


def test_is_dangerous_project_path_safe(tmp_path):
    safe = tmp_path / "project"
    safe.mkdir()

    assert is_dangerous_project_path(safe) is False


def test_ensure_directory_creates(tmp_path):
    target = tmp_path / "a" / "b" / "c"

    ensure_directory(target, dry_run=False)

    assert target.is_dir()


def test_ensure_directory_dry_run(tmp_path):
    target = tmp_path / "nope"

    ensure_directory(target, dry_run=True)

    assert not target.exists()


def test_is_probably_text_by_extension():
    assert is_probably_text_by_extension(Path("file.patch")) is True
    assert is_probably_text_by_extension(Path("file.diff")) is True
    assert is_probably_text_by_extension(Path("file.PATCH")) is True
    assert is_probably_text_by_extension(Path("file.py")) is False


def test_inspect_text_file_utf8(tmp_path):
    f = tmp_path / "hello.txt"
    f.write_text("hello world", encoding="utf-8")

    info = inspect_text_file(f)

    assert info.is_text is True
    assert info.used_patch_fallback is False


def test_inspect_text_file_binary(tmp_path):
    f = tmp_path / "binary.bin"
    f.write_bytes(b"\x00\x01\x02")

    info = inspect_text_file(f)

    assert info.is_text is False


def test_inspect_text_file_non_utf8_non_patch(tmp_path):
    f = tmp_path / "bad.txt"
    f.write_bytes(b"\x80\x81\x82")

    info = inspect_text_file(f)

    assert info.is_text is False
    assert info.used_patch_fallback is False


def test_inspect_text_file_non_utf8_patch(tmp_path):
    f = tmp_path / "fix.patch"
    f.write_bytes(b"\x80\x81\x82")

    info = inspect_text_file(f)

    assert info.is_text is True
    assert info.used_patch_fallback is True


def test_inspect_text_file_missing(tmp_path):
    f = tmp_path / "missing.txt"

    info = inspect_text_file(f)

    assert info.is_text is False


def test_iter_project_files(tmp_path):
    (tmp_path / "a.txt").touch()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.txt").touch()
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "c.txt").touch()

    files = iter_project_files(tmp_path, ignore_dirs=(".git",))
    names = sorted(f.name for f in files)

    assert names == ["a.txt", "b.txt"]


def test_iter_project_dirs(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "pkg").mkdir()
    (tmp_path / ".git").mkdir()

    dirs = iter_project_dirs(tmp_path, ignore_dirs=(".git",))
    names = sorted(d.name for d in dirs)

    assert names == ["pkg", "src"]
